import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.learning.professional_engine import ProfessionalEngine
class ProfessionalEngineV621(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.e=ProfessionalEngine(cls.r)
    def test_version(self): self.assertIn(self.e.VERSION,{'62.6.0','63.0.0','64.0.0'})
    def test_probability_contract(self): self.assertTrue(self.e.validate_probabilities({'1':.4,'X':.3,'2':.3}))
    def test_probability_rejects_bad_sum(self): self.assertFalse(self.e.validate_probabilities({'1':.7,'X':.7,'2':.0}))
    def test_quality_gate(self): self.assertTrue(self.e.quality_gate()['pass'])
if __name__=='__main__': unittest.main()
