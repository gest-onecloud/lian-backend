import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model

class V603CrossCompetitionSystematic(unittest.TestCase):
    def setUp(self):
        self.repo=Repo(ROOT/'data'/'lian.db'); self.model=Model(self.repo)
    def test_registry_resolves_known_2026_27_teams(self):
        for team in ['Birmingham City','Brentford','Sheffield Wednesday','Crewe Alexandra']:
            league,tier,source=self.model.team_competition(team,'2026-08-25')
            self.assertIsNotNone(tier,(team,league,source))
    def test_stronger_tier_gets_symmetric_bridge(self):
        pairs=[('Birmingham City','Brentford'),('Sheffield Wednesday','Wolverhampton Wanderers'),('Barnsley','Crewe Alexandra')]
        for home,away in pairs:
            hh,ht,_=self.model.team_competition(home,'2026-08-25'); ah,at,_=self.model.team_competition(away,'2026-08-25')
            self.assertNotEqual(ht,at,(home,away,hh,ah))
            _,hc=self.model.cross_competition_strength(home,1500,away,'2026-08-25')
            _,ac=self.model.cross_competition_strength(away,1500,home,'2026-08-25')
            self.assertEqual(hc,-ac,(home,away,hc,ac))
            self.assertGreater(hc,0 if ht>at else -1e9)
            self.assertLess(hc,0 if ht<at else 1e9)
    def test_birmingham_brentford_remains_away_without_manual_result_override(self):
        row=self.repo.rows("SELECT * FROM matches WHERE home='Birmingham City' AND away='Brentford' LIMIT 1")[0]
        out=self.model.predict(row)
        self.assertEqual(out['pick'],'2')
        self.assertLess(out['probabilities']['1'],out['probabilities']['2'])
        self.assertEqual(out['features']['home_competition'],'Championship')
        self.assertEqual(out['features']['away_competition'],'Premier League')

if __name__=='__main__': unittest.main()
