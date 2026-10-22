"""LiAn V62 Professional Engine.

A read-only quality gate over the existing prediction, learning, backtest and
error-intelligence components. It does not overwrite historical predictions or
change weights automatically.
"""
from __future__ import annotations
import math
from .backtest import BacktestEngine
from .benchmark import ProfessionalBenchmark
from .adaptive_calibration import AdaptiveCalibration
from .error_intelligence import ErrorIntelligence

class ProfessionalEngine:
    VERSION='63.0.0'
    MIN_CONFIDENCE_MARGIN=0.03
    def __init__(self,repo): self.r=repo

    @staticmethod
    def validate_probabilities(p):
        if not isinstance(p,dict) or any(k not in p for k in ('1','X','2')): return False
        vals=[float(p[k]) for k in ('1','X','2')]
        return all(math.isfinite(x) and 0<=x<=1 for x in vals) and abs(sum(vals)-1)<=1e-6

    def quality_gate(self):
        checks=[]
        tables={x['name'] for x in self.r.rows("SELECT name FROM sqlite_master WHERE type='table'")}
        required={'matches','predictions','postmatch_reviews','feature_snapshots'}
        checks.append({'name':'schema_core','pass':required.issubset(tables),'detail':f'{len(tables)} tablas'})
        rows=self.r.rows("SELECT * FROM matches WHERE status='finished' ORDER BY date ASC,id ASC LIMIT 50")
        valid=0
        if rows:
            from ..core.model import Model
            model=Model(self.r)
            for m in rows:
                try:
                    valid += int(self.validate_probabilities(model.predict(m)['probabilities']))
                except Exception: pass
        checks.append({'name':'probability_contract','pass':valid==len(rows),'detail':f'{valid}/{len(rows)}'})
        dup=self.r.one("SELECT COUNT(*) n FROM (SELECT home,away,date,COUNT(*) c FROM matches GROUP BY home,away,date HAVING c>1)")['n']
        checks.append({'name':'duplicate_fixture_groups','pass':int(dup)==0,'detail':str(dup)})
        stale=self.r.one("SELECT COUNT(*) n FROM matches WHERE date LIKE '2099-%'")['n']
        checks.append({'name':'future_fixture_sanity','pass':int(stale)==0,'detail':str(stale)})
        return {'version':self.VERSION,'pass':all(x['pass'] for x in checks),'checks':checks,
                'policy':'Quality gate read-only. No automatic model promotion and no destructive data repair.'}

    def report(self,limit=200,seed=20260902):
        gate=self.quality_gate()
        back=BacktestEngine(self.r).run(limit)
        bench=ProfessionalBenchmark(self.r).full_report(limit,seed)
        try: cal=AdaptiveCalibration(self.r).report()
        except Exception as e: cal={'error':str(e)}
        try: err=ErrorIntelligence(self.r).report()
        except Exception as e: err={'error':str(e)}
        return {'version':self.VERSION,'quality_gate':gate,'walk_forward':back,
                'model_comparison':bench,'calibration':cal,'error_intelligence':err,
                'promotion_policy':'Promote only after complete regression, leakage checks, and out-of-sample evidence. Five random matches are diagnostic, never proof.'}
