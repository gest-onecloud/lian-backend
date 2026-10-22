"""Pre-match error fingerprinting. Diagnostic only; never changes weights automatically."""
from ..services.venue import resolve
class ErrorFingerprint:
    MIN_SIMILAR=5
    def __init__(self,repo): self.r=repo; self.r.init_learning()
    @staticmethod
    def _band(x):
        x=float(x or 0); return 'low' if x<.40 else 'mid' if x<.65 else 'high'
    @staticmethod
    def _sep(p):
        vals=sorted([float(v) for v in (p or {}).values()],reverse=True); return vals[0]-vals[1] if len(vals)>1 else 0
    def fingerprint(self,m,p):
        e=p.get('explainability') or {}; v=resolve(m)
        return {'competition':m.get('competition_id'),'pick':p.get('pick'),'venue_status':v.get('status'),'venue_side':v.get('advantage_side'),'quality':p.get('quality'),'evidence_band':self._band(p.get('evidence')),'confidence_band':self._band(p.get('confidence')),'separation_band':'tight' if self._sep(p.get('probabilities'))<.05 else 'balanced' if self._sep(p.get('probabilities'))<.10 else 'separated'}
    def _past(self):
        rows=self.r.rows('''SELECT r.match_id,r.predicted,r.actual,p.p_home,p.p_draw,p.p_away,p.confidence,p.evidence,m.competition_id,m.competition,m.home,m.away FROM postmatch_reviews r JOIN matches m ON m.id=r.match_id LEFT JOIN predictions p ON p.match_id=r.match_id WHERE m.status='finished' AND r.actual IN ('1','X','2')''')
        out=[]
        for r in rows:
            m={'id':r['match_id'],'competition_id':r['competition_id'],'competition':r['competition'],'home':r['home'],'away':r['away']}; pred={'pick':r['predicted'],'probabilities':{'1':r.get('p_home',0),'X':r.get('p_draw',0),'2':r.get('p_away',0)},'confidence':r.get('confidence',0),'evidence':r.get('evidence',0)}
            try: out.append((self.fingerprint(m,pred),r))
            except Exception: pass
        return out
    @staticmethod
    def _sim(a,b):
        keys=['competition','pick','venue_status','venue_side','quality','evidence_band','confidence_band','separation_band']; return sum(a.get(k)==b.get(k) for k in keys)/len(keys)
    def assess(self,m,p):
        cur=self.fingerprint(m,p); past=self._past(); sims=[r for fp,r in past if self._sim(cur,fp)>=.75]; n=len(sims); wrong=sum(r['predicted']!=r['actual'] for r in sims) if n else 0; rate=wrong/n if n else None; gn=len(past); gw=sum(r['predicted']!=r['actual'] for _,r in past) if gn else 0; gr=gw/gn if gn else None
        if n<5: level='SIN MUESTRA'; message='No hay suficientes casos históricos comparables para estimar un patrón de error.'
        elif rate>=gr+.10: level='RIESGO ELEVADO'; message='Los casos comparables tienen una tasa de error claramente superior a la media.'
        elif rate>=gr+.05: level='RIESGO MODERADO'; message='Existe un patrón histórico de error algo superior a la media.'
        else: level='RIESGO NORMAL'; message='Los casos comparables no muestran un exceso de error relevante.'
        return {'level':level,'message':message,'fingerprint':cur,'similar_cases':n,'similar_wrong':wrong,'similar_error_rate':rate,'global_cases':gn,'global_error_rate':gr,'policy':'Solo advertencia prepartido; no modifica probabilidades ni pesos automáticamente.'}
    def report(self):
        p=self._past(); n=len(p); w=sum(r['predicted']!=r['actual'] for _,r in p) if n else 0; return {'samples':n,'global_error_rate':w/n if n else None,'policy':'Fingerprint diagnóstico; requiere al menos 5 casos comparables y no altera el modelo automáticamente.'}
