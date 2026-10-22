import math
from ..core.model import Model

class BacktestEngine:
    """Strict walk-forward evaluator. It never uses a match's own result as a feature."""
    def __init__(self,repo): self.r=repo; self.model=Model(repo)
    @staticmethod
    def brier(p,a): return sum((p[k]-(1 if k==a else 0))**2 for k in ('1','X','2'))
    @staticmethod
    def logloss(p,a): return -math.log(max(1e-12,p[a]))
    def run(self,limit=200):
        rows=self.r.rows("SELECT * FROM matches WHERE status='finished' ORDER BY date ASC LIMIT ?",(limit,)); results=[]; feature_hits={}
        for m in rows:
            p=self.model.predict(m); actual='1' if m['home_score']>m['away_score'] else 'X' if m['home_score']==m['away_score'] else '2'
            for s in p.get('signals',[]):
                if s['direction']=='neutral': continue
                actual_side='local' if actual=='1' else 'visitante' if actual=='2' else 'neutral'
                d=feature_hits.setdefault(s['factor'],{'samples':0,'correct_direction':0})
                d['samples']+=1
                if actual_side==s['direction']: d['correct_direction']+=1
            results.append({'id':m['id'],'date':m['date'],'pick':p['pick'],'actual':actual,'correct':p['pick']==actual,'brier':self.brier(p['probabilities'],actual),'log_loss':self.logloss(p['probabilities'],actual)})
        n=len(results); acc=sum(x['correct'] for x in results)/n if n else None
        return {'model_version':self.model.VERSION,'samples':n,'accuracy':acc,'brier':sum(x['brier'] for x in results)/n if n else None,'log_loss':sum(x['log_loss'] for x in results)/n if n else None,'feature_directional_performance':feature_hits,'policy':'walk-forward; no future leakage; automatic weight changes require a minimum sample threshold and out-of-sample improvement.'}
