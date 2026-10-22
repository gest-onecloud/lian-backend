"""Leakage-safe adaptive learning engine for LiAn.

The engine learns from VERIFIED finished matches only.  It keeps the original
prediction immutable, derives the real outcome exclusively from the final
score, and produces small, auditable calibration factors.  Every factor used
for a future match is computed from matches strictly before that match date.
"""
from __future__ import annotations
import json, math
from collections import defaultdict

OUTCOMES=('1','X','2')
LABELS={'1':'local','X':'empate','2':'visitante'}
FEATURES=('Fuerza/ELO','Forma','Ataque ajustado','Defensa ajustada','xG diferencial',
          'Producción ajustada','Tendencia','Sede real','Descanso','Viaje','Jugadores',
          'H2H','Contexto competitivo reciente','Fatiga/contexto adaptativo','Plantilla/fitness','Clima','Árbitro','Perfil de liga')

class AdaptiveLearningEngine:
    """Online meta-calibration with temporal isolation and bounded updates."""
    VERSION='63.0.0'
    def __init__(self, repo):
        self.r=repo
        self.r.init_learning()
        self._schema()

    def _schema(self):
        self.r.execute('''CREATE TABLE IF NOT EXISTS learning_audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT NOT NULL,
            event_type TEXT NOT NULL, old_value TEXT, new_value TEXT,
            reason TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS adaptive_feature_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT NOT NULL,
            match_date TEXT NOT NULL, feature TEXT NOT NULL, direction TEXT NOT NULL,
            actual TEXT NOT NULL, correct INTEGER NOT NULL,
            signal REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(match_id,feature))''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS adaptive_outcome_history(
            match_id TEXT PRIMARY KEY, match_date TEXT NOT NULL,
            predicted TEXT NOT NULL, actual TEXT NOT NULL,
            p_home REAL NOT NULL, p_draw REAL NOT NULL, p_away REAL NOT NULL)''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS learning_snapshots(
            id INTEGER PRIMARY KEY AUTOINCREMENT, as_of TEXT NOT NULL,
            samples INTEGER NOT NULL, global_accuracy REAL, brier REAL, log_loss REAL,
            outcome_weights TEXT NOT NULL, feature_weights TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        try: self.r.execute('ALTER TABLE adaptive_outcome_history ADD COLUMN learning_eligible INTEGER DEFAULT 1')
        except Exception: pass
        # Migrate legacy learning rows: records generated on/after the match
        # date are retrospective evidence and must never train the model.
        self.r.execute('''UPDATE adaptive_outcome_history SET learning_eligible=CASE
            WHEN EXISTS (SELECT 1 FROM predictions p WHERE p.match_id=adaptive_outcome_history.match_id
                         AND substr(COALESCE(p.generated_at,''),1,10) < adaptive_outcome_history.match_date)
            THEN 1 ELSE 0 END''')

    @staticmethod
    def actual(match):
        hs, aw = match.get('home_score'), match.get('away_score')
        if hs is None or aw is None: return None
        hs,aw=int(hs),int(aw)
        return '1' if hs>aw else 'X' if hs==aw else '2'

    def repair_reviews(self):
        """Repair stale/corrupt reviews using immutable stored predictions + final score."""
        rows=self.r.rows("""SELECT m.*, p.model_version, p.p_home,p.p_draw,p.p_away,p.pick,
            p.confidence,p.evidence,p.expected_goals,p.generated_at
            FROM matches m JOIN predictions p ON p.match_id=m.id
            WHERE m.status='finished' AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            ORDER BY m.date ASC, m.id ASC""")
        repaired=0; created=0
        for m in rows:
            actual=self.actual(m)
            if actual is None: continue
            p={'1':float(m['p_home'] or 0),'X':float(m['p_draw'] or 0),'2':float(m['p_away'] or 0)}
            stored_pick=str(m.get('pick') or '').strip()
            expected=stored_pick if stored_pick in OUTCOMES else max(p,key=p.get)
            b=sum((p[k]-(1 if k==actual else 0))**2 for k in OUTCOMES)
            ll=-math.log(max(1e-12,p[actual]))
            existing=self.r.one('SELECT predicted,actual,brier,log_loss FROM postmatch_reviews WHERE match_id=?',(m['id'],))
            changed=not existing or existing.get('predicted')!=expected or existing.get('actual')!=actual
            diagnosis=[]
            if expected!=actual: diagnosis.append('pick_error')
            if expected!=actual and float(m['confidence'] or 0)>.70: diagnosis.append('overconfidence')
            if abs(p['1']-p['2'])<.03: diagnosis.append('local_away_close')
            if float(m['evidence'] or 0)<.55: diagnosis.append('low_evidence')
            if changed and existing: diagnosis.append('review_repaired')
            ge=0.0
            try:
                # predictions.expected_goals is total only in the current schema; keep prior goal_error if present.
                old=self.r.one('SELECT goal_error FROM postmatch_reviews WHERE match_id=?',(m['id'],))
                ge=float(old['goal_error'] or 0) if old else 0.0
            except Exception: pass
            self.r.execute('''INSERT OR REPLACE INTO postmatch_reviews
                (match_id,model_version,predicted,actual,brier,log_loss,goal_error,calibration_gap,diagnosis)
                VALUES(?,?,?,?,?,?,?,?,?)''',
                (m['id'],m['model_version'] or self.VERSION,expected,actual,b,ll,ge,
                 abs(max(p.values())-(1 if expected==actual else 0)),json.dumps(diagnosis,ensure_ascii=False)))
            generated=str(m.get('generated_at') or '')[:10]
            # A stored prediction is eligible for learning only if it existed
            # before the match date. Same-day timestamps are conservatively
            # excluded because kickoff time may be unavailable. The review is
            # still retained for audit/comparison.
            learning_eligible=int(bool(generated and generated < str(m['date'])))
            self.r.execute('''INSERT OR REPLACE INTO adaptive_outcome_history
                (match_id,match_date,predicted,actual,p_home,p_draw,p_away,learning_eligible) VALUES(?,?,?,?,?,?,?,?)''',
                (m['id'],m['date'],expected,actual,p['1'],p['X'],p['2'],learning_eligible))
            if changed:
                typ='review_created' if not existing else 'review_repaired'
                self.r.execute('INSERT INTO learning_audit(match_id,event_type,old_value,new_value,reason) VALUES(?,?,?,?,?)',
                    (m['id'],typ,json.dumps(dict(existing or {}),ensure_ascii=False),json.dumps({'predicted':expected,'actual':actual},ensure_ascii=False),'Resultado derivado exclusivamente del marcador final verificado.'))
                repaired += 1 if existing else 0; created += 1 if not existing else 0
        return {'created':created,'repaired':repaired,'checked':len(rows)}

    def rebuild_feature_history(self):
        """Create one temporal feature outcome row per verified pre-match snapshot."""
        rows=self.r.rows('''SELECT m.id,m.date,m.home_score,m.away_score,e.payload
            FROM matches m JOIN evidence_snapshots e ON e.match_id=m.id JOIN predictions p ON p.match_id=m.id
            WHERE m.status='finished' AND substr(COALESCE(p.generated_at,''),1,10)<m.date AND substr(COALESCE(e.collected_at,''),1,10)<m.date AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            ORDER BY m.date ASC,m.id ASC''')
        added=0
        for r in rows:
            try: payload=json.loads(r['payload']); pred=payload.get('prediction',{}); fv=pred.get('feature_vector',{})
            except Exception: continue
            actual=self.actual(r)
            for feature,signal in fv.items():
                try: signal=float(signal or 0)
                except Exception: continue
                if abs(signal)<1e-9: continue
                direction='1' if signal>0 else '2'
                correct=int(direction==actual)
                before=self.r.one('SELECT id FROM adaptive_feature_history WHERE match_id=? AND feature=?',(r['id'],feature))
                self.r.execute('''INSERT OR IGNORE INTO adaptive_feature_history
                    (match_id,match_date,feature,direction,actual,correct,signal) VALUES(?,?,?,?,?,?,?)''',
                    (r['id'],r['date'],feature,direction,actual,correct,signal))
                if not before: added+=1
        return added

    def outcome_weights_as_of(self,date):
        """Bayesian/shrunk calibration, using only matches strictly before date."""
        rows=self.r.rows('''SELECT predicted,actual,p_home,p_draw,p_away FROM adaptive_outcome_history
            WHERE match_date<? AND learning_eligible=1 ORDER BY match_date ASC,match_id ASC''',(date,))
        n=len(rows)
        if not n: return {'1':1.0,'X':1.0,'2':1.0,'samples':0}
        # Dirichlet prior 20 observations distributed uniformly. This prevents small-sample swings.
        counts={k:20.0 for k in OUTCOMES}
        picked={k:0.0 for k in OUTCOMES}; hit={k:0.0 for k in OUTCOMES}
        for r in rows:
            a=r['actual']; counts[a]+=1
            pr=r['predicted']; picked[pr]+=1; hit[pr]+=int(pr==a)
        total=sum(counts.values()); actual_rate={k:counts[k]/total for k in OUTCOMES}
        # Expected prior-neutral share of predicted outcomes is used as a stable reference.
        weights={}
        for k in OUTCOMES:
            empirical=(hit[k]+8.0)/(picked[k]+16.0) if picked[k] else .5
            target=.50 + .50*(actual_rate[k]-.3333333333)
            raw=empirical/max(.05,target)
            weights[k]=max(.92,min(1.08,raw))
        weights['samples']=n
        return weights

    def feature_weights_as_of(self,date):
        rows=self.r.rows('''SELECT feature,correct FROM adaptive_feature_history WHERE match_date<? ORDER BY match_date ASC,id ASC''',(date,))
        by=defaultdict(list)
        for r in rows: by[r['feature']].append(int(r['correct']))
        out={}
        for f in FEATURES:
            vals=by.get(f,[]); n=len(vals)
            if not n: out[f]=1.0; continue
            # Strong shrinkage toward neutral; bounded to prevent feedback explosions.
            acc=(sum(vals)+10)/(n+20)
            out[f]=max(.90,min(1.10, .90 + .20*acc))
        return out

    def calibration_for_match(self,match):
        date=match['date']; ow=self.outcome_weights_as_of(date); fw=self.feature_weights_as_of(date)
        # Team-specific and competition-specific corrections are intentionally very small.
        comp=match.get('competition_id') or ''
        rows=self.r.rows('''SELECT r.predicted,r.actual FROM postmatch_reviews r JOIN matches m ON m.id=r.match_id
            WHERE m.date<? AND m.status='finished' AND m.competition_id=?''',(date,comp))
        comp_adj={k:1.0 for k in OUTCOMES}
        if len(rows)>=8:
            for k in OUTCOMES:
                pk=[x for x in rows if x['predicted']==k]
                if len(pk)>=4:
                    hit=sum(x['actual']==k for x in pk)/len(pk)
                    comp_adj[k]=max(.95,min(1.05,.96+.08*hit))
        return {'outcome':ow,'feature':fw,'competition':comp_adj}

    def feature_delta(self, feature_vector, calibration):
        total=0.0
        fw=calibration.get('feature',{})
        for feature,signal in (feature_vector or {}).items():
            try: total += float(signal or 0.0) * (float(fw.get(feature,1.0))-1.0)
            except Exception: pass
        return max(-0.04,min(0.04,total*0.12))

    def apply(self, probabilities, calibration, feature_delta=0.0):
        p=dict(probabilities)
        p['1']=max(0.0,p['1']+feature_delta); p['2']=max(0.0,p['2']-feature_delta)
        ow=calibration['outcome']; ca=calibration['competition']
        q={k:p[k]*float(ow.get(k,1))*float(ca.get(k,1)) for k in OUTCOMES}
        s=sum(q.values()) or 1
        return {k:q[k]/s for k in OUTCOMES}

    def snapshot(self,date):
        ow=self.outcome_weights_as_of(date); fw=self.feature_weights_as_of(date)
        rows=self.r.rows('SELECT * FROM adaptive_outcome_history WHERE match_date<? AND learning_eligible=1',(date,))
        n=len(rows)
        self.r.execute('''INSERT INTO learning_snapshots(as_of,samples,global_accuracy,brier,log_loss,outcome_weights,feature_weights)
            VALUES(?,?,?,?,?,?,?)''',(date,n,None,None,None,json.dumps(ow),json.dumps(fw,ensure_ascii=False)))
        self.r.execute('''INSERT INTO model_weights(scope,weights_json,version,updated_at) VALUES(?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(scope) DO UPDATE SET weights_json=excluded.weights_json,version=model_weights.version+1,updated_at=CURRENT_TIMESTAMP''',
            ('global',json.dumps({'outcome':ow,'feature':fw},ensure_ascii=False)))
        for f,w in fw.items():
            vals=self.r.one('SELECT COUNT(*) n,SUM(correct) c FROM adaptive_feature_history WHERE feature=? AND match_date<?',(f,date)) or {'n':0,'c':0}
            n2=int(vals.get('n') or 0); c2=float(vals.get('c') or 0)
            self.r.execute('''INSERT INTO feature_performance(feature,samples,correct,error,weight,updated_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(feature) DO UPDATE SET samples=excluded.samples,correct=excluded.correct,error=excluded.error,weight=excluded.weight,updated_at=CURRENT_TIMESTAMP''',
                (f,n2,c2,max(0,n2-c2),w))
        return {'as_of':date,'samples':n,'outcome_weights':ow,'feature_weights':fw}
