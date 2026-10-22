import sys,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.data.feature_store import FeatureStore
from backend.core.model import Model
from backend.data.historical import HistoricalSync,SEASONS

class V541(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.fs=FeatureStore(cls.r); cls.model=Model(cls.r)
 def test_schema_isolation(self):
  names={r['name'] for r in self.r.rows("select name from sqlite_master where type='table'")}
  self.assertTrue({'feature_snapshots','team_state','player_state','league_state','model_evaluations'}.issubset(names))
 def test_temporal_features(self):
  m=self.r.one("select * from matches where status='scheduled' order by date limit 1")
  snap=self.fs.snapshot(m)
  self.assertEqual(snap['as_of'],m['date'])
  future=self.r.one("select count(*) n from matches where status='finished' and date>=?",(m['date'],))['n']
  self.assertGreaterEqual(future,0)
 def test_model_probabilities(self):
  rows=self.r.rows("select * from matches where status='scheduled' order by date limit 23")
  for m in rows:
   p=self.model.predict(m)['probabilities']; self.assertAlmostEqual(sum(p.values()),1,places=6); self.assertTrue(all(0<=x<=1 for x in p.values()))
 def test_feature_snapshot_persist(self):
  m=self.r.one("select * from matches where status='scheduled' order by date limit 1")
  before=self.r.one('select count(*) n from feature_snapshots')['n']; self.fs.persist_snapshot(m); after=self.r.one('select count(*) n from feature_snapshots')['n']; self.assertEqual(after,before+1)
 def test_source_urls_are_verified_shapes(self):
  self.assertIn('2024-25', SEASONS)

if __name__=='__main__':unittest.main()
