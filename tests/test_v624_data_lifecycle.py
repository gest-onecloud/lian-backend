import datetime as dt
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
from backend.services.historical_replay import HistoricalReplay
from backend.services.progol import generate_contest

ROOT=Path(__file__).resolve().parents[1]

class V624DataLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td=tempfile.mkdtemp(prefix='lian624_')
        cls.db=Path(cls.td)/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',cls.db); shutil.copy2(ROOT/'data'/'public_priors.json',Path(cls.td)/'public_priors.json')
        cls.r=Repo(cls.db); cls.r.init_learning()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.td,ignore_errors=True)

    def test_bootstrap_contains_current_and_previous_day_snapshots(self):
        FixtureSync(self.r).bootstrap_seed()
        for d in ('2026-09-02','2026-09-03','2026-09-06'):
            n=self.r.one('SELECT COUNT(*) n FROM matches WHERE date=?',(d,))['n']
            self.assertGreater(n,0,d)

    def test_past_snapshot_is_not_next(self):
        FixtureSync(self.r).bootstrap_seed()
        m=self.r.one("SELECT * FROM matches WHERE date='2026-09-02' LIMIT 1")
        self.assertEqual(m['status'],'finished')
        self.assertIsNotNone(m['home_score']); self.assertIsNotNone(m['away_score'])

    def test_progol_2349_is_current_and_not_2348(self):
        x=generate_contest(self.r,'2349')
        self.assertEqual(x['contest_id'],'2349')
        self.assertEqual([g['count'] for g in x['groups']],[14,7])
        self.assertTrue(all(t['model_version'] in {'62.6.0','63.0.0','64.0.0'} for g in x['groups'] for t in g['tickets']))
        self.assertEqual(x['groups'][0]['matches'][0]['home'],'FC Juárez')

if __name__=='__main__': unittest.main()
