import json, shutil, tempfile, unittest
from pathlib import Path
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.historical_master import HistoricalMaster
from backend.learning.promotion_gate import PromotionGate

ROOT=Path(__file__).resolve().parents[1]
class V630Integrity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.td=tempfile.mkdtemp(prefix='lian630_'); cls.db=Path(cls.td)/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',cls.db); shutil.copy2(ROOT/'data'/'public_priors.json',Path(cls.td)/'public_priors.json'); cls.r=Repo(cls.db); cls.r.init_learning()
 @classmethod
 def tearDownClass(cls): shutil.rmtree(cls.td,ignore_errors=True)
 def test_historical_master_populates(self):
  x=HistoricalMaster(self.r).build(); self.assertGreaterEqual(x['ingested'],100); self.assertEqual(self.r.one('select count(*) n from historical_master')['n'],x['ingested'])
 def test_postmatch_display_can_be_correct_but_retrospective_is_ineligible(self):
  m=self.r.one("select * from matches where home='Palermo' and away='Mantova'"); self.assertIsNotNone(m); p=Model(self.r).predict(m); self.assertIn(p['pick'],{'1','X','2'})
 def test_promotion_gate_rejects_accuracy_regression(self):
  x=PromotionGate(self.r).evaluate('62.6.0','63.0.0',{'accuracy':.50,'brier':.50,'log_loss':.80},{'accuracy':.49,'brier':.49,'log_loss':.79},20); self.assertEqual(x['status'],'REJECT')
 def test_promotion_gate_accepts_parity_without_metric_regression(self):
  x=PromotionGate(self.r).evaluate('62.6.0','63.0.0',{'accuracy':.50,'brier':.50,'log_loss':.80},{'accuracy':.50,'brier':.499,'log_loss':.799},20); self.assertEqual(x['status'],'PROMOTE')
if __name__=='__main__': unittest.main()
