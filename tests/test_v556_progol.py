import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.services.progol import generate
from backend.services.timezone import mexico_time
from backend.learning.error_fingerprint import ErrorFingerprint
from backend.core.model import Model
class V556Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.r.init_learning()
 def test_version(self): self.assertIn(Model.VERSION,{'55.6','55.7','55.9','55.9.1','55.9.3','55.9.5','55.9.6','55.9.8','60.0.0','60.3.0','61.1.5','62.0.0','62.6.0','63.0.0','64.0.0','64.1.0','64.2.0','64.6.0'})
 def test_progol_persists_20_tickets(self):
  x=generate(self.r,'2026-08-25'); self.assertEqual(len(x['tickets']),20); self.assertEqual(len(x['matches']),len(x['tickets'][0]['cells']))
  n=self.r.one("SELECT COUNT(*) n FROM progol_tickets WHERE match_date='2026-08-25'")['n']; self.assertEqual(n,20)
 def test_progol_has_match_headers_and_results(self):
  x=generate(self.r,'2026-08-25'); self.assertTrue(all('q' in m and 'home' in m and 'away' in m and 'time_mx' in m for m in x['matches']))
  self.assertTrue(any(c['state']=='correct' for t in x['tickets'] for c in t['cells']))
  self.assertTrue(any(c['state']=='wrong' for t in x['tickets'] for c in t['cells']))
 def test_progol_is_stable_between_calls(self):
  a=generate(self.r,'2026-08-25'); b=generate(self.r,'2026-08-25'); self.assertEqual([t['selections'] for t in a['tickets']],[t['selections'] for t in b['tickets']])
 def test_mexico_time_official_overrides(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'"); self.assertEqual(mexico_time(m)['time_mx'],'17:30'); self.assertEqual(mexico_time(m)['status'],'VERIFICADA')
  m2=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-club-león-real-salt-lake'"); self.assertEqual(mexico_time(m2)['time_mx'],'20:30')
 def test_fingerprint_is_diagnostic(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'"); p=Model(self.r).predict(m); x=ErrorFingerprint(self.r).assess(m,p); self.assertIn(x['level'],{'SIN MUESTRA','RIESGO NORMAL','RIESGO MODERADO','RIESGO ELEVADO'}); self.assertIn('fingerprint',x)
if __name__=='__main__': unittest.main()
