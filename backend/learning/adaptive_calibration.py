"""Post-match calibration intelligence.
It measures errors immediately, but does not change model weights from a small sample.
Automatic parameter changes require a minimum sample and out-of-sample improvement.
"""
from __future__ import annotations
import math, json
from collections import defaultdict
from .error_learning import ErrorLearning
from .adaptive_engine import AdaptiveLearningEngine
from ..core.model import Model

class AdaptiveCalibration:
    MIN_AUTO_SAMPLES=100
    MIN_SCOPE_SAMPLES=50
    def __init__(self,repo):
        self.r=repo; self.r.init_learning()
        self.r.execute("""CREATE TABLE IF NOT EXISTS calibration_recommendations(
            id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, scope TEXT, metric TEXT,
            samples INTEGER, current_value REAL, target_value REAL, recommendation TEXT,
            eligible INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    def review_finished(self, limit=500):
        rows=self.r.rows("SELECT * FROM matches WHERE status='finished' ORDER BY date ASC LIMIT ?",(limit,))
        engine=AdaptiveLearningEngine(self.r)
        repair=engine.repair_reviews()
        feature_rows=engine.rebuild_feature_history()
        el=ErrorLearning(self.r); created=repair['created']
        for m in rows:
            existing=self.r.one('SELECT id FROM postmatch_reviews WHERE match_id=?',(m['id'],))
            if existing: continue
            pred=self.r.one('SELECT * FROM predictions WHERE match_id=? ORDER BY generated_at ASC LIMIT 1',(m['id'],))
            if pred:
                p={'model_version':pred['model_version'],'probabilities':{'1':pred['p_home'],'X':pred['p_draw'],'2':pred['p_away']},'pick':pred['pick'],'confidence':pred['confidence'],'evidence':pred['evidence'],'expected_goals':Model(self.r).predict(m)['expected_goals'], 'features':{'home_history':0,'away_history':0}}
                el.autopsy(m,p); created+=1
        return created
    def _summary(self):
        r=self.r.one("SELECT COUNT(*) n,AVG(brier) b,AVG(log_loss) l,AVG(goal_error) g,AVG(calibration_gap) c FROM postmatch_reviews") or {}
        n=int(r.get('n') or 0)
        wrong=int((self.r.one("SELECT COUNT(*) n FROM postmatch_reviews WHERE predicted<>actual") or {'n':0})['n'])
        return {'samples':n,'accuracy':(n-wrong)/n if n else None,'brier':r.get('b'),'log_loss':r.get('l'),'goal_error':r.get('g'),'calibration_gap':r.get('c')}
    def _recommendations(self):
        rec=[]; rows=self.r.rows('SELECT * FROM postmatch_reviews')
        n=len(rows)
        if n:
            wrong=sum(x['predicted']!=x['actual'] for x in rows)
            acc=1-wrong/n
            eligible=int(n>=self.MIN_AUTO_SAMPLES)
            rec.append(('global','accuracy',n,acc,None,'Conservar pesos; recalibrar solo con muestra ≥100 y mejora walk-forward fuera de muestra.',eligible))
        # Outcome bias: predicted pick vs actual. This is diagnostic, not an automatic weight change.
        for outcome,label in [('1','local'),('X','empate'),('2','visitante')]:
            rs=[x for x in rows if x['predicted']==outcome]
            if len(rs)>=10:
                hit=sum(x['actual']==outcome for x in rs)/len(rs)
                rec.append(('resultado',label,len(rs),hit,None,'Monitorear sesgo de selección; no cambiar pesos con <50 observaciones por segmento.',int(len(rs)>=self.MIN_SCOPE_SAMPLES)))
        return rec
    def run(self):
        created=self.review_finished()
        repair=self.r.one("SELECT COUNT(*) n FROM learning_audit WHERE event_type='review_repaired'") or {'n':0}
        feature_rows=self.r.one("SELECT COUNT(*) n FROM adaptive_feature_history") or {'n':0}
        s=self._summary(); rec=self._recommendations()
        for scope,metric,n,current,target,text,eligible in rec:
            self.r.execute('INSERT INTO calibration_recommendations(model_version,scope,metric,samples,current_value,target_value,recommendation,eligible) VALUES(?,?,?,?,?,?,?,?)',
                           (Model.VERSION,scope,metric,n,current,target,text,eligible))
        try: learning_snapshot=AdaptiveLearningEngine(self.r).snapshot(self.r.one("SELECT COALESCE(MAX(date),'0000-00-00') d FROM matches WHERE status='finished'")['d'])
        except Exception: learning_snapshot={'samples':0}
        return {'reviews_created':created,'repair':{'repaired':int(repair.get('n',0))},'feature_history_rows':int(feature_rows.get('n',0)),'learning_snapshot':learning_snapshot,'summary':s,'recommendations':[{'scope':a,'metric':b,'samples':c,'current_value':d,'target_value':e,'recommendation':f,'eligible':bool(g)} for a,b,c,d,e,f,g in rec],
                'policy':f'No automatic weight change until >= {self.MIN_AUTO_SAMPLES} global observations, >= {self.MIN_SCOPE_SAMPLES} per scope, and a walk-forward improvement is verified.'}
    def report(self):
        s=self._summary(); latest=self.r.rows('SELECT scope,metric,samples,current_value,target_value,recommendation,eligible,created_at FROM calibration_recommendations ORDER BY id DESC LIMIT 20')
        return {'summary':s,'latest':latest,'policy':f'No automatic weight change until >= {self.MIN_AUTO_SAMPLES} global observations, >= {self.MIN_SCOPE_SAMPLES} per scope, and out-of-sample improvement.'}
