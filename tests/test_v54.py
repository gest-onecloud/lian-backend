import sys,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.services.calendar import matches
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db')
 def test_db(self):
  c=sqlite3.connect(ROOT/'data'/'lian.db')
  try:
   self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok'); self.assertGreaterEqual(c.execute('select count(*) from matches').fetchone()[0],91)
  finally: c.close()
 def test_today(self): self.assertEqual(len(matches(self.r,'2026-08-25')),23)
 def test_probabilities(self):
  for m in matches(self.r,'2026-08-25'):
   p=m['probabilities']; self.assertAlmostEqual(sum(p.values()),1,places=5); self.assertTrue(all(0<=x<=1 for x in p.values()))
 def test_no_all_same_vector(self):
  ms=matches(self.r,'2026-08-25'); vec={(round(m['probabilities']['1'],3),round(m['probabilities']['X'],3),round(m['probabilities']['2'],3)) for m in ms}; self.assertGreaterEqual(len(vec),5)
if __name__=='__main__':unittest.main()
