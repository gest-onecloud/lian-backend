import unittest
from pathlib import Path
import tempfile, shutil
from backend.data.repo import Repo
from backend.services.progol import generate_contest
from backend.core.model import Model

ROOT=Path(__file__).resolve().parents[1]
class V625ProgolSameCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td=Path(tempfile.mkdtemp(prefix='lian625_')); cls.db=cls.td/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',cls.db); shutil.copy2(ROOT/'data'/'public_priors.json',cls.td/'public_priors.json'); cls.r=Repo(cls.db); cls.r.init_learning()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.td,ignore_errors=True)
    def test_current_contest_uses_current_model(self):
        x=generate_contest(self.r,'2349')
        self.assertEqual(x['contest_id'],'2349')
        self.assertTrue(all(t['model_version']==Model.VERSION for g in x['groups'] for t in g['tickets']))
    def test_historical_contest_keeps_original_benchmark(self):
        x=generate_contest(self.r,'2348')
        self.assertEqual(x['contest_id'],'2348')
        self.assertTrue(all(len(t['selections'])==g['count'] for g in x['groups'] for t in g['tickets']))
    def test_prediction_payload_has_core_probabilities(self):
        x=generate_contest(self.r,'2349')
        self.assertEqual(len(x['groups'][0]['matches']),14)
        # Every Progol fixture is predicted by the same Model.predict path.
        # Reconstruct one fixture and require a normalized 1/X/2 distribution.
        from backend.services.progol import _contest_match, CONTESTS
        m=_contest_match(self.r,CONTESTS['2349']['matches'][0]); p=m['probabilities']
        self.assertEqual(set(p),{'1','X','2'}); self.assertAlmostEqual(sum(p.values()),1.0,places=6)

    def test_both_groups_exist(self):
        x=generate_contest(self.r,'2349'); self.assertEqual([g['count'] for g in x['groups']],[14,7])
if __name__=='__main__': unittest.main()
