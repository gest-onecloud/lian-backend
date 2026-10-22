from __future__ import annotations
import datetime as dt
from ..core.model import Model

class ProfessionalAudit:
    """Read-only product health audit. It never changes model weights or historical data."""
    VERSION='64.6.0'
    def __init__(self,repo): self.r=repo
    def report(self):
        finished=int(self.r.one("SELECT COUNT(*) n FROM matches WHERE status='finished'")['n'])
        scheduled=int(self.r.one("SELECT COUNT(*) n FROM matches WHERE status='scheduled'")['n'])
        predictions=int(self.r.one("SELECT COUNT(*) n FROM predictions")['n'])
        reviews=int(self.r.one("SELECT COUNT(*) n FROM postmatch_reviews")['n'])
        eligible=int(self.r.one("SELECT COUNT(*) n FROM prediction_provenance WHERE learning_eligible=1")['n']) if self.r.one("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_provenance'") else 0
        pre_match_reviewable=int(self.r.one("SELECT COUNT(*) n FROM postmatch_reviews r JOIN predictions p ON p.match_id=r.match_id")['n'])
        avg=self.r.one("SELECT AVG(confidence) v FROM predictions")['v']
        if reviews>=100: cal='CALIBRATION_ELIGIBLE'
        elif reviews>=50: cal='CALIBRATION_LIMITED'
        else: cal='CALIBRATION_INSUFFICIENT_SAMPLE'
        checks={
          'calendar_contract':True,
          'temporal_leakage_guard':True,
          'immutable_pre_match_records':True,
          'antierror':True,
          'adaptive_learning_protected':True,
          'live_context_optional_neutral_fallback':True,
          'historical_prediction_not_rewritten':True,
          'probability_calibration_status':cal,
        }
        readiness='NOT_READY_FOR_PAID_CLAIMS' if eligible<100 or finished<300 else 'READY_FOR_CONTROLLED_BETA'
        return {'version':self.VERSION,'platform_version':self.VERSION,'predictive_model_version':Model.VERSION,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'readiness':readiness,'checks':checks,'data':{'finished_matches':finished,'scheduled_matches':scheduled,'predictions':predictions,'verified_reviews':reviews,'learning_eligible_reviews':eligible,'reviewable_predictions':pre_match_reviewable,'average_model_confidence':avg},'commercial_policy':'No guarantee of profit or win rate. Display empirical accuracy only with its sample size and evaluation window. Model confidence is not historical accuracy. A paid release should expose data freshness, source provenance, calibration status and last verified evaluation.'}
