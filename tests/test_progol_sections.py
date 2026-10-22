import unittest
from backend.data.repo import Repo
from backend.services.progol import generate_contest

ROOT='data/lian.db'
class ProgolSectionsTests(unittest.TestCase):
    def setUp(self): self.repo=Repo(ROOT)
    def test_weekend_has_14_plus_7_and_20_each(self):
        x=generate_contest(self.repo,'2348')
        self.assertEqual(x['kind'],'fin_semana')
        self.assertEqual([(g['count'],len(g['tickets'])) for g in x['groups']],[(14,20),(7,20)])
        self.assertEqual(len(x['groups'][0]['matches']),14); self.assertEqual(len(x['groups'][1]['matches']),7)
        self.assertTrue(all(m['date_mx'] and m['time_mx'] for g in x['groups'] for m in g['matches']))
    def test_midweek_has_9_and_20(self):
        x=generate_contest(self.repo,'810')
        self.assertEqual(x['kind'],'media_semana')
        self.assertEqual([(g['count'],len(g['tickets'])) for g in x['groups']],[(9,20)])
        self.assertEqual(len(x['groups'][0]['matches']),9)
        self.assertTrue(all(m['date_mx'] and m['time_mx'] for m in x['groups'][0]['matches']))
    def test_persistence(self):
        a=generate_contest(self.repo,'810')['groups'][0]['tickets']
        b=generate_contest(self.repo,'810')['groups'][0]['tickets']
        self.assertEqual(a,b)
if __name__=='__main__': unittest.main()
