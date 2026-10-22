import sys,tempfile,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from backend.data.repo import Repo
from backend.learning.live_context import LiveContextEngine
from backend.core.context import ContextEngine
class LiveContextTests(unittest.TestCase):
    def test_live_context_schema_and_neutral_missing(self):
        r=Repo(pathlib.Path(tempfile.mkdtemp())/'x.db'); r.init_learning(); r.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,date TEXT,competition_id TEXT,competition TEXT,home TEXT,away TEXT,status TEXT,home_score INTEGER,away_score INTEGER)')
        r.execute('INSERT INTO matches(id,date,competition_id,competition,home,away,status) VALUES(?,?,?,?,?,?,?)',('m','2026-09-01','L1','Liga Test','H','A','scheduled'))
        out=LiveContextEngine(r).refresh(r.one('SELECT * FROM matches WHERE id=?',('m',))); self.assertEqual(out['status'],'unavailable'); self.assertEqual(out['quality'],0)
        c=ContextEngine(r).evaluate(r.one('SELECT * FROM matches WHERE id=?',('m',))); self.assertEqual(c['live_context_quality'],0)
if __name__=='__main__': unittest.main()
