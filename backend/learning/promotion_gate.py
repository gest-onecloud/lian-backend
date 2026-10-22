import math

class PromotionGate:
    """Hard release gate. Candidate never becomes stable if predictive quality regresses."""
    def __init__(self, repo): self.r=repo

    @staticmethod
    def _better_lower(candidate, baseline):
        return candidate <= baseline + 1e-12

    def evaluate(self, baseline_version, candidate_version, baseline, candidate, samples):
        ba,ca=baseline.get('accuracy'),candidate.get('accuracy')
        bb,cb=baseline.get('brier'),candidate.get('brier')
        bl,cl=baseline.get('log_loss'),candidate.get('log_loss')
        if not samples or any(x is None for x in (ba,ca,bb,cb,bl,cl)):
            status='REJECT'; reason='insufficient_comparable_metrics'
        elif ca + 1e-12 < ba or not self._better_lower(cb,bb) or not self._better_lower(cl,bl):
            status='REJECT'; reason='predictive_regression'
        elif ca > ba + 1e-12 or cb < bb - 1e-12 or cl < bl - 1e-12:
            status='PROMOTE'; reason='predictive_improvement_without_metric_regression'
        else:
            status='PROMOTE'; reason='predictive_parity_with_no_regression'
        self.r.execute('''INSERT INTO promotion_gates(baseline_version,candidate_version,samples,baseline_accuracy,candidate_accuracy,baseline_brier,candidate_brier,baseline_log_loss,candidate_log_loss,status,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
          (baseline_version,candidate_version,int(samples),ba,ca,bb,cb,bl,cl,status,reason))
        return {'status':status,'reason':reason,'baseline':baseline,'candidate':candidate,'samples':samples}
