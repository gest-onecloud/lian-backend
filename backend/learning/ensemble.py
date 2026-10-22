from __future__ import annotations
import math, re
from collections import defaultdict

class ProfessionalEnsemble:
    VERSION='63.0.0'
    def __init__(self,repo): self.r=repo
    @staticmethod
    def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
    @staticmethod
    def normalize(p):
        s=sum(p.values()) or 1; return {k:max(0,v/s) for k,v in p.items()}
    @staticmethod
    def dc_tau(x,y,lh,la,rho=-0.08):
        # Dixon-Coles low-score correction for 0/0, 0/1, 1/0 and 1/1.
        if x==0 and y==0:return 1-lh*la*rho
        if x==0 and y==1:return 1+lh*rho
        if x==1 and y==0:return 1+la*rho
        if x==1 and y==1:return 1-rho
        return 1.0
    def dc_probs(self,lh,la):
        out={'1':0.,'X':0.,'2':0.}
        for h in range(0,10):
            ph=math.exp(-lh)*lh**h/math.factorial(h)
            for a in range(0,10):
                pa=math.exp(-la)*la**a/math.factorial(a)
                q=ph*pa*self.dc_tau(h,a,lh,la)
                out['1' if h>a else 'X' if h==a else '2']+=q
        return self.normalize(out)
    def _features(self,m):
        date=m['date']; rows=self.r.rows("SELECT home,away,home_score,away_score FROM matches WHERE status='finished' AND date<? ORDER BY date ASC,id ASC",(date,))
        stats=defaultdict(lambda:[0,0,0,0,1500.])
        for x in rows:
            h=self.norm(x['home']); a=self.norm(x['away']); hs=int(x['home_score']); aws=int(x['away_score'])
            rh=stats[h][4]; ra=stats[a][4]; exp=1/(1+10**((ra-rh)/400)); act=1 if hs>aws else .5 if hs==aws else 0
            k=20
            stats[h][4]=rh+k*(act-exp); stats[a][4]=ra+k*((1-act)-(1-exp))
            stats[h][0]+=1; stats[h][1]+=hs; stats[h][2]+=aws; stats[h][3]+=1
            stats[a][0]+=1; stats[a][1]+=aws; stats[a][2]+=hs; stats[a][3]+=1
        h=stats[self.norm(m['home'])]; a=stats[self.norm(m['away'])]
        return [h[4]-a[4], (h[1]/h[0] if h[0] else 1.35)-(a[1]/a[0] if a[0] else 1.35), (h[2]/h[0] if h[0] else 1.35)-(a[2]/a[0] if a[0] else 1.35), min(h[0],30), min(a[0],30)]
    def xgb(self,m):
        try:
            from xgboost import XGBClassifier
        except Exception:return None
        try: rows=self.r.rows("SELECT * FROM matches WHERE status='finished' AND date<? ORDER BY date ASC,id ASC",(m['date'],))
        except Exception: return None
        if len(rows)<60:return None
        # Walk-forward feature generation; no future rows are used for a training example.
        stats=defaultdict(lambda:[0,0,0,0,1500.])
        X=[]; y=[]
        for r in rows:
            h=self.norm(r['home']); a=self.norm(r['away']); sh=stats[h]; sa=stats[a]
            feat=[sh[4]-sa[4],(sh[1]/sh[0] if sh[0] else 1.35)-(sa[1]/sa[0] if sa[0] else 1.35),(sh[2]/sh[0] if sh[0] else 1.35)-(sa[2]/sa[0] if sa[0] else 1.35),min(sh[0],30),min(sa[0],30)]
            X.append(feat); y.append(0 if r['home_score']>r['away_score'] else 1 if r['home_score']==r['away_score'] else 2)
            rh=sh[4]; ra=sa[4]; exp=1/(1+10**((ra-rh)/400)); act=1 if r['home_score']>r['away_score'] else .5 if r['home_score']==r['away_score'] else 0
            sh[4]=rh+20*(act-exp); sa[4]=ra+20*((1-act)-(1-exp))
            sh[0]+=1; sh[1]+=r['home_score']; sh[2]+=r['away_score']; sh[3]+=1
            sa[0]+=1; sa[1]+=r['away_score']; sa[2]+=r['home_score']; sa[3]+=1
        try:
            model=XGBClassifier(n_estimators=120,max_depth=3,learning_rate=.05,subsample=.85,colsample_bytree=.9,objective='multi:softprob',num_class=3,eval_metric='mlogloss',random_state=60,n_jobs=1)
            model.fit(X,y,verbose=False); return dict(zip(['1','X','2'],model.predict_proba([self._features(m)])[0]))
        except Exception:return None
    def apply(self,m,base,lh,la):
        dc=self.dc_probs(max(.2,lh),max(.18,la)); xgb=self.xgb(m)
        if xgb:
            p=self.normalize({k:.70*base[k]+.15*dc[k]+.15*xgb[k] for k in ('1','X','2')}); source='base+dc+xgboost'
        else:
            p=self.normalize({k:.84*base[k]+.16*dc[k] for k in ('1','X','2')}); source='base+dixon-coles'
        return p, {'dixon_coles':dc,'xgboost':xgb,'weights':{'base':.70 if xgb else .84,'dixon_coles':.15 if xgb else .16,'xgboost':.15 if xgb else 0},'source':source}
