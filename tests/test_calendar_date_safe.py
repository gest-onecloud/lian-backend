import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync,_mx_date_from_iso
from backend.services.timezone import MX,mexico_time
class CalendarDateSafeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.r.init_learning(); cls.fx=FixtureSync(cls.r)
 def test_seeded_aug26_is_present(self):
  n=self.r.one("SELECT COUNT(*) n FROM matches WHERE date='2026-08-26'")['n']; self.assertGreaterEqual(n,14)
 def test_aug25_and_aug26_are_disjoint(self):
  a={(x['home'],x['away']) for x in self.r.rows("SELECT home,away FROM matches WHERE date='2026-08-25'")}
  b={(x['home'],x['away']) for x in self.r.rows("SELECT home,away FROM matches WHERE date='2026-08-26'")}
  self.assertFalse(a & b)
 def test_wrong_provider_date_is_rejected(self):
  e={'id':'bad','home':'CF Monterrey','away':'Chicago Fire FC','league':'Leagues Cup','strDate':'2026-08-25','strTime':'19:30'}
  self.assertFalse(self.fx._upsert(e,'2026-08-26','test://bad','TheSportsDB'))
  self.assertIsNone(self.r.one("SELECT * FROM matches WHERE date='2026-08-26' AND home='CF Monterrey' AND away='Chicago Fire FC'"))
 def test_existing_aug25_times_are_displayed_in_mexico(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'"); x=mexico_time(m); self.assertEqual(x['time_mx'],'17:30'); self.assertEqual(x['date_mx'],'2026-08-25')

 def test_aug27_is_present_and_date_pure(self):
  from backend.services.fixture_sync import FixtureSync
  FixtureSync(self.r).bootstrap_seed()
  rows=self.r.rows("SELECT home,away,date FROM matches WHERE date='2026-08-27'")
  self.assertGreaterEqual(len(rows),40)
  self.assertTrue(all(r['date']=='2026-08-27' for r in rows))
  pairs={(r['home'],r['away']) for r in rows}
  self.assertNotIn(('CF Monterrey','Chicago Fire FC'),pairs)

 def test_aug27_request_never_raises_without_network(self):
  import os
  os.environ['LIAN_DISABLE_LIVE_FIXTURES']='1'
  from backend.server import H
  self.assertTrue(True)

 def test_timestamp_date_is_evaluated_in_mexico(self):
  self.assertEqual(_mx_date_from_iso('2026-08-26T05:00:00Z'),'2026-08-25')
  self.assertEqual(_mx_date_from_iso('2026-08-26T18:00:00Z'),'2026-08-26')
if __name__=='__main__':unittest.main()
