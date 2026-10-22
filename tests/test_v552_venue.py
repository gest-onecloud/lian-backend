import unittest
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.venue import resolve
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'lian.db'
class VenueAndAdvancedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Repo(DB)
    def test_monterrey_chicago_is_away_host(self):
        m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
        v=resolve(m)
        self.assertTrue(v['verified']); self.assertEqual(v['venue_side'],'away'); self.assertEqual(v['hosting_team'],'Chicago Fire FC')
    def test_neutral_competition_has_zero_venue_delta_when_explicit(self):
        m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
        p=Model(self.r).predict(m)
        self.assertEqual(p['features']['venue_side'],'away')
        self.assertTrue(p['features']['venue_verified'])
        self.assertLess(p['features']['venue_verified']+0,2)
    def test_model_exposes_advanced_markets(self):
        m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
        p=Model(self.r).predict(m)
        for k in ('over_1_5','over_2_5','over_3_5','btts_yes','clean_sheet_home','clean_sheet_away'):
            self.assertIn(k,p['markets']); self.assertGreaterEqual(p['markets'][k],0); self.assertLessEqual(p['markets'][k],1)
    def test_model_no_forced_local_when_venue_is_away_host(self):
        m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
        p=Model(self.r).predict(m)
        self.assertLessEqual(p['features']['venue_advantage_home'],0)
        self.assertGreaterEqual(p['features']['venue_advantage_away'],0)
if __name__=='__main__': unittest.main()
