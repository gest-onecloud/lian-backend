"""Public AntiError facade for LiAn V55.7.
The established AdaptiveLearningEngine remains the implementation; this facade
exposes deterministic result derivation and repair for tests/services.
"""
from .adaptive_engine import AdaptiveLearningEngine

class AntiError:
    def __init__(self, repo): self.engine=AdaptiveLearningEngine(repo)
    @staticmethod
    def actual(home_score, away_score): return AdaptiveLearningEngine.actual({'home_score':home_score,'away_score':away_score})
    @staticmethod
    def verdict(pick, actual):
        if pick not in ('1','X','2') or actual not in ('1','X','2'): return 'PENDIENTE'
        return 'ACERTO' if pick==actual else 'FALLA'
    def repair_all(self): return self.engine.repair_reviews()
