import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.services.results_sync import ResultsSync
from backend.learning.adaptive_calibration import AdaptiveCalibration
from backend.core.model import Model

class V554Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.r.init_learning()
 def test_version(self): self.assertIn(Model.VERSION,{'55.6','55.7','55.8','55.9','55.9.1','55.9.3','55.9.5','55.9.6','55.9.8','60.0.0','60.3.0','61.1.5','62.6.0','63.0.0','64.0.0','64.1.0','64.2.0','64.6.0'})
 def test_results_are_verified_and_non_destructive(self):
  x=ResultsSync(self.r).sync('2026-08-25'); self.assertGreaterEqual(x['applied'],18)
  row=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-es-laliga-valencia-real-betis'")
  self.assertEqual((row['status'],row['home_score'],row['away_score']),('finished',0,1)); self.assertEqual(row['result_source_type'],'official')
  row2=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-en-carabao-birmingham-city-brentford'")
  self.assertEqual((row2['home_score'],row2['away_score']),(1,6)); self.assertEqual(row2['result_source_type'],'secondary')
 def test_postmatch_autopsy_runs_from_stored_prediction(self):
  AdaptiveCalibration(self.r).run(); n=self.r.one('SELECT COUNT(*) n FROM postmatch_reviews')['n']; self.assertGreaterEqual(n,18)
  v=self.r.one("SELECT * FROM postmatch_reviews WHERE match_id='cal-2026-08-25-es-laliga-valencia-real-betis'")
  self.assertIsNotNone(v); self.assertEqual(v['actual'],'2'); self.assertEqual(v['predicted'],'1')
 def test_no_automatic_weight_change_with_small_sample(self):
  x=AdaptiveCalibration(self.r).run(); self.assertIn('policy',x); self.assertTrue(all(not r['eligible'] for r in x['recommendations']))
 def test_finished_cards_keep_prematch_probabilities(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-es-laliga-valencia-real-betis'")
  p=self.r.one("SELECT * FROM predictions WHERE match_id=?",(m['id'],)); self.assertAlmostEqual(p['p_home']+p['p_draw']+p['p_away'],1,places=6); self.assertEqual(p['model_version'],'55.3')
if __name__=='__main__': unittest.main()
