from __future__ import annotations
import math, random
from collections import Counter
from .backtest import BacktestEngine
from ..core.model import Model

OUTCOMES=('1','X','2')

class ProfessionalBenchmark:
    """Leakage-safe benchmark for model-vs-model and random historical checks.

    Old predictions are read from the immutable predictions table. New scores are
    generated with the current model using only information available before the
    match date. Benchmarking never writes predictions, learning rows, or reviews.
    """
    VERSION='63.0.0'
    def __init__(self, repo):
        self.r=repo; self.model=Model(repo)

    @staticmethod
    def actual(m):
        hs,as_=m.get('home_score'),m.get('away_score')
        if hs is None or as_ is None:return None
        return '1' if int(hs)>int(as_) else 'X' if int(hs)==int(as_) else '2'

    @staticmethod
    def metrics(rows):
        n=len(rows)
        if not n:return {'samples':0,'accuracy':None,'top2':None,'brier':None,'log_loss':None,'predicted_distribution':{k:0 for k in OUTCOMES},'actual_distribution':{k:0 for k in OUTCOMES}}
        acc=sum(x['correct'] for x in rows)/n
        top2=sum(x['top2'] for x in rows)/n
        brier=sum(x['brier'] for x in rows)/n
        ll=sum(x['log_loss'] for x in rows)/n
        pd=Counter(x['pick'] for x in rows); ad=Counter(x['actual'] for x in rows)
        return {'samples':n,'accuracy':acc,'top2':top2,'brier':brier,'log_loss':ll,'predicted_distribution':{k:pd.get(k,0) for k in OUTCOMES},'actual_distribution':{k:ad.get(k,0) for k in OUTCOMES}}

    @staticmethod
    def _old(row):
        p={'1':float(row['p_home'] or 0),'X':float(row['p_draw'] or 0),'2':float(row['p_away'] or 0)}
        pick=str(row['old_pick'] or '')
        if pick not in OUTCOMES:pick=max(p,key=p.get)
        return pick,p

    @staticmethod
    def _score(p,actual,pick):
        return {
            'pick':pick,'actual':actual,'correct':pick==actual,
            'top2':actual in sorted(OUTCOMES,key=p.get,reverse=True)[:2],
            'brier':sum((p[k]-(1 if k==actual else 0))**2 for k in OUTCOMES),
            'log_loss':-math.log(max(1e-12,p[actual]))
        }

    def compare(self,limit=200):
        matches=self.r.rows('''SELECT m.*,p.model_version old_version,p.pick old_pick,p.p_home,p.p_draw,p.p_away,p.confidence old_conf
            FROM matches m JOIN predictions p ON p.match_id=m.id
            WHERE m.status='finished' AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            ORDER BY m.date ASC,m.id ASC LIMIT ?''',(int(limit),))
        old_rows=[]; new_rows=[]; paired=[]
        for m in matches:
            actual=self.actual(m)
            if actual is None:continue
            op,oprobs=self._old(m)
            np=self.model.predict(m)
            nr=self._score(np['probabilities'],actual,np['pick']); orow=self._score(oprobs,actual,op)
            old_rows.append(orow); new_rows.append(nr)
            paired.append({'id':m['id'],'date':m['date'],'home':m['home'],'away':m['away'],'result':f"{m['home_score']}-{m['away_score']}",
                           'actual':actual,'old_version':m['old_version'],'old_pick':op,'new_pick':np['pick'],
                           'old_correct':orow['correct'],'new_correct':nr['correct'],'old_top2':orow['top2'],'new_top2':nr['top2'],
                           'old_probabilities':oprobs,'new_probabilities':np['probabilities']})
        om=self.metrics(old_rows); nm=self.metrics(new_rows)
        return {'version':self.VERSION,'samples':len(paired),'old':om,'new':nm,
                'delta':{'accuracy':None if om['accuracy'] is None else nm['accuracy']-om['accuracy'],
                         'top2':None if om['top2'] is None else nm['top2']-om['top2'],
                         'brier':None if om['brier'] is None else nm['brier']-om['brier'],
                         'log_loss':None if om['log_loss'] is None else nm['log_loss']-om['log_loss']},
                'paired':paired,'policy':'Comparación fuera de muestra respecto al registro preexistente; no escribe aprendizaje ni modifica predicciones históricas.'}

    def random_five(self,seed=20260902,include_match_id=''):
        rows=self.r.rows('''SELECT m.*,p.model_version old_version,p.pick old_pick,p.p_home,p.p_draw,p.p_away
            FROM matches m JOIN predictions p ON p.match_id=m.id
            WHERE m.status='finished' AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            ORDER BY m.date ASC,m.id ASC''')
        if len(rows)<5:return {'error':'No hay al menos 5 partidos terminados con predicción histórica comparable.','samples':len(rows)}
        rng=random.Random(seed)
        chosen=[]
        if include_match_id:
            forced=[r for r in rows if r['id']==include_match_id]
            if forced: chosen.append(forced[0])
        remaining=[r for r in rows if r['id'] not in {x['id'] for x in chosen}]
        chosen.extend(rng.sample(remaining, max(0,5-len(chosen))))
        out=[]
        for m in chosen:
            actual=self.actual(m); op,oprobs=self._old(m); np=self.model.predict(m); nr=self._score(np['probabilities'],actual,np['pick']); orow=self._score(oprobs,actual,op)
            out.append({'id':m['id'],'date':m['date'],'home':m['home'],'away':m['away'],'result':f"{m['home_score']}-{m['away_score']}",
                        'actual':actual,'old_version':m['old_version'],'old_pick':op,'new_pick':np['pick'],
                        'old_correct':orow['correct'],'new_correct':nr['correct'],'old_top2':orow['top2'],'new_top2':nr['top2'],
                        'old_probabilities':oprobs,'new_probabilities':np['probabilities']})
        return {'version':self.VERSION,'seed':seed,'samples':len(out),'matches':out,'old_accuracy':sum(x['old_correct'] for x in out)/len(out),'new_accuracy':sum(x['new_correct'] for x in out)/len(out),
                'old_top2':sum(x['old_top2'] for x in out)/len(out),'new_top2':sum(x['new_top2'] for x in out)/len(out),
                'policy':'Muestra aleatoria reproducible. No se fuerza el resultado a local; 1/X/2 son igualmente posibles y se conserva la salida real del modelo.'}

    def full_report(self,limit=200,seed=20260902):
        comparison=self.compare(limit)
        five=self.random_five(seed,include_match_id='cal-2026-08-25-en-carabao-birmingham-city-brentford')
        walk=BacktestEngine(self.r).run(limit)
        return {'version':self.VERSION,'comparison':comparison,'random_five':five,'walk_forward_current':walk,
                'acceptance_policy':'No se promociona un cambio de modelo por una muestra de 5. Requiere mejora fuera de muestra y revisión de Brier/LogLoss, además de ausencia de regresiones.'}
