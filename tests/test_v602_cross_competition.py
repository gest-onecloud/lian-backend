import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model

class V602CrossCompetition(unittest.TestCase):
    def test_birmingham_brentford_cross_competition_is_not_forced_local(self):
        repo=Repo(ROOT/"data"/"lian.db")
        row=repo.rows("SELECT * FROM matches WHERE home='Birmingham City' AND away='Brentford' LIMIT 1")[0]
        model=Model(repo)
        out=model.predict(row)
        self.assertEqual(out["pick"],"2")
        self.assertLess(out["probabilities"]["1"],out["probabilities"]["2"])
        self.assertLess(out["features"]["cross_competition_home_adjustment"],0)
        self.assertGreater(out["features"]["cross_competition_away_adjustment"],0)
        self.assertLess(out["features"]["cross_competition_goal_delta"],0)

if __name__=="__main__": unittest.main()
