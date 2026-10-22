import sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.services.data_fusion import DataFusion
from backend.services.catchup import CatchUpEngine
from backend.learning.ensemble import ProfessionalEnsemble
class V60Tests(unittest.TestCase):
 def test_fusion_deduplicates(self):
  with tempfile.TemporaryDirectory() as td:
   r=Repo(Path(td)/'t.db'); f=DataFusion(r); d='2099-01-01'; a={'date':d,'competition':'T','home':'A','away':'B','home_score':1,'away_score':0}; f.ingest('S1',[a],1); f.ingest('S2',[a],2); rows=f.matches_for_date(d); self.assertEqual(len(rows),1); self.assertGreaterEqual(rows[0]['_fusion']['source_count'],2)
 def test_catchup_state_tables(self):
  with tempfile.TemporaryDirectory() as td:
   r=Repo(Path(td)/'t.db'); CatchUpEngine(r); self.assertIsNotNone(r.one("SELECT name FROM sqlite_master WHERE type='table' AND name='catchup_runs'")); self.assertIsNotNone(r.one("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_state'"))
 def test_ensemble(self):
  with tempfile.TemporaryDirectory() as td:
   r=Repo(Path(td)/'t.db'); e=ProfessionalEnsemble(r); p,info=e.apply({'id':'x','date':'2026-08-25','home':'Valencia','away':'Real Betis'}, {'1':.4,'X':.3,'2':.3},1.2,1.0); self.assertAlmostEqual(sum(p.values()),1,6); self.assertIn('dixon_coles',info)
if __name__=='__main__': unittest.main()
