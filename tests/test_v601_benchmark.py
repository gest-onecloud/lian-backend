import sys,unittest,tempfile,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.learning.benchmark import ProfessionalBenchmark
from backend.learning.historical_intelligence import HistoricalIntelligence
class V601Benchmark(unittest.TestCase):
 def test_metrics_empty(self):
  x=ProfessionalBenchmark.metrics([]); self.assertEqual(x['samples'],0)
 def test_score_outcomes(self):
  self.assertTrue(ProfessionalBenchmark._score({'1':.2,'X':.3,'2':.5},'2','2')['correct'])
  self.assertTrue(ProfessionalBenchmark._score({'1':.2,'X':.3,'2':.5},'X','2')['top2'])
 def test_base_rate_is_non_forcing(self):
  p=ProfessionalBenchmark.__new__(ProfessionalBenchmark); self.assertEqual(set(ProfessionalBenchmark._score({'1':.2,'X':.5,'2':.3},'X','X')),{'pick','actual','correct','top2','brier','log_loss'})
 def test_h2h_recency_bounded(self):
  x=HistoricalIntelligence.__new__(HistoricalIntelligence)
  rows=[{'date':'2026-08-20','home':'A','away':'B','home_score':0,'away_score':2},{'date':'2020-01-01','home':'A','away':'B','home_score':3,'away_score':0}]
  z=x.evaluate('A','B','2026-08-25',rows); self.assertLessEqual(abs(z['home_edge']),.09); self.assertEqual(z['samples'],2)
 def test_no_forced_home(self):
  x=ProfessionalBenchmark._score({'1':.2,'X':.5,'2':.3},'X','X'); self.assertEqual(set(x),{'pick','actual','correct','top2','brier','log_loss'})
if __name__=='__main__':unittest.main()
