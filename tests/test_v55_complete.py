import sys,unittest,urllib.request,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.combo import build
from backend.data.historical import HistoricalSync
class V55(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.r.init_learning()
 def test_model_vector(self):
  rows=self.r.rows("select * from matches where status='scheduled' order by date limit 23")
  self.assertTrue(rows)
  for m in rows:
   p=Model(self.r).predict(m); self.assertAlmostEqual(sum(p['probabilities'].values()),1,places=6); self.assertEqual(set(p['probabilities']),{'1','X','2'})
 def test_combinations_5x2(self):
  x=build(self.r,'2026-08-25'); self.assertEqual(len(x['levels']),5); self.assertTrue(all(len(l['combinations'])==2 for l in x['levels']))
  self.assertTrue(all(c['size']>=0 for l in x['levels'] for c in l['combinations']))
 def test_parser_contract(self):
  raw=b'{"matches":[{"date":"2025-01-01","team1":"A","team2":"B","score":{"ft":[1,0]}}]}'
  rows=HistoricalSync(self.r).parse_openfootball(raw,'Premier League','2024-25'); self.assertEqual(rows[0]['away_score'],0)
 def test_db_integrity(self): self.assertEqual(self.r.one('PRAGMA integrity_check')['integrity_check'],'ok')
if __name__=='__main__':unittest.main()
