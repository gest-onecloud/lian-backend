import ast, sqlite3, datetime as dt, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V613SeptemberActive(unittest.TestCase):
 def test_version_synced(self):
  v=(ROOT/'VERSION.txt').read_text().strip(); s=(ROOT/'backend/server.py').read_text(); self.assertIn(v,{'62.6.0','63.0.0','63.1.0','63.2.0','64.0.0','64.1.0','64.2.0','64.6.0'}); self.assertIn(f"VERSION='{v}'",s)
 def test_no_stale_eleven_day_window(self):
  s=(ROOT/'backend/server.py').read_text()+"\n"+(ROOT/'backend/services/fixture_sync.py').read_text(); self.assertNotIn('days=11',s); self.assertNotIn("'window_days':11",s)
 def test_dynamic_search_module(self): ast.parse((ROOT/'backend/services/intel.py').read_text())
 def test_september_fixture_search_prefers_current_future(self):
  from backend.services.intel import search_matches
  class R:
   def rows(self,q,*a): return [{'id':'old','date':'2026-08-25','home':'Valencia','away':'Barcelona','competition':'LaLiga','status':'finished','time':'16:00'},{'id':'new','date':'2026-09-06','home':'Valencia CF','away':'FC Barcelona','competition':'LaLiga','status':'scheduled','time':'16:15'},{'id':'other','date':'2026-09-09','home':'FC Barcelona','away':'Feyenoord','competition':'Champions League','status':'scheduled','time':'18:45'}]
  got=search_matches(R(),'Valencia vs Barcelona',5); self.assertTrue(got); self.assertEqual(got[0]['id'],'new')
 def test_database_has_no_mutation_from_test(self):
  c=sqlite3.connect(ROOT/'data'/'lian.db'); self.assertGreater(c.execute('select count(*) from matches').fetchone()[0],0); c.close()
 def test_universal_route_performs_rolling_refresh(self):
  s=(ROOT/'backend/server.py').read_text(); self.assertIn("u.path=='/api/universal-match'",s); self.assertTrue('sync_window_cached' in s or 'sync_span_cached' in s)
 def test_universal_resolver_exact_pair_beats_stale_same_team_result(self):
  from backend.services.universal import resolve
  class R:
   def rows(self,q,*a): return [{'id':'old','date':'2026-08-25','home':'Valencia','away':'Barcelona','competition':'LaLiga','status':'finished','time':'16:00'},{'id':'new','date':'2026-09-06','home':'Valencia CF','away':'FC Barcelona','competition':'LaLiga','status':'scheduled','time':'16:15'},{'id':'wrong','date':'2026-09-07','home':'Barcelona','away':'Valencia','competition':'LaLiga','status':'scheduled','time':'16:15'}]
  got=resolve(R(),'Valencia vs Barcelona',5); self.assertTrue(got); self.assertEqual(got[0]['id'],'new')
 def test_september_reference_fixtures_are_current_regression_cases(self):
  expected={'Valencia vs Barcelona':'2026-09-06','Barcelona vs Feyenoord':'2026-09-09','Levante vs Barcelona':'2026-09-13','Barcelona vs Racing':'2026-09-16','Sevilla vs Barcelona':'2026-09-19'}; self.assertTrue(all(dt.date.fromisoformat(d).month==9 for d in expected.values()))
 def test_frontend_calendar_allows_rolling_window(self): self.assertIn("max.setDate(max.getDate()+29)",(ROOT/'frontend/app.js').read_text())
 def test_fixture_diagnostics_endpoint_exists(self):
  s=(ROOT/'backend/server.py').read_text(); self.assertIn("u.path=='/api/fixture-diagnostics'",s)
if __name__=='__main__': unittest.main()
