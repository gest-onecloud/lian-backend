import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.learning.error_intelligence import ErrorIntelligence
from backend.core.model import Model
class V555Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/"data"/"lian.db"); cls.r.init_learning()
 def test_version(self): self.assertIn(Model.VERSION,{"55.6","55.7","55.8","55.9","55.9.1","55.9.3","55.9.5","55.9.6","55.9.8","60.0.0","60.3.0","61.1.5","62.0.0","62.6.0","63.0.0","64.0.0"})
 def test_tables_and_report(self):
  x=ErrorIntelligence(self.r).report(); self.assertIn("global",x); self.assertIn("leagues",x); self.assertIn("worst_teams",x)
 def test_no_auto_weight_change_policy(self):
  x=ErrorIntelligence(self.r).report(); self.assertIn("cambia pesos automáticamente",x["policy"])
 def test_segment_metrics_table(self):
  tables={r['name'] for r in self.r.rows("SELECT name FROM sqlite_master WHERE type='table'")}
  self.assertIn("error_segment_metrics",tables); self.assertIn("error_intelligence_snapshots",tables)
if __name__=="__main__": unittest.main()
