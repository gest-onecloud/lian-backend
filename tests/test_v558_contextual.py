import sys,tempfile,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from backend.data.repo import Repo
from backend.learning.contextual_intelligence import ContextualIntelligence
class ContextualTests(unittest.TestCase):
    def test_profile_temporal(self):
        r=Repo(pathlib.Path(tempfile.mkdtemp())/'x.db'); r.init_learning(); r.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,date TEXT,competition_id TEXT,competition TEXT,home TEXT,away TEXT,status TEXT,home_score INTEGER,away_score INTEGER)')
        for i,(a,b) in enumerate([(2,0),(1,1),(0,1),(3,1)]):
            r.execute('INSERT INTO matches(id,date,competition_id,competition,home,away,status,home_score,away_score) VALUES(?,?,?,?,?,?,?,?,?)',(str(i),f'2026-01-{i+1:02d}','L1','Liga Test','H','A','finished',a,b))
        p=ContextualIntelligence(r).league_profile('L1','2026-02-01'); self.assertEqual(p['samples'],4); self.assertEqual(p['home_goals'],1.5)
    def test_missing_context_neutral(self):
        r=Repo(pathlib.Path(tempfile.mkdtemp())/'x.db'); r.init_learning(); r.execute('CREATE TABLE matches(id TEXT PRIMARY KEY,date TEXT,competition_id TEXT,competition TEXT,home TEXT,away TEXT,status TEXT,home_score INTEGER,away_score INTEGER)')
        x=ContextualIntelligence(r).evaluate({'date':'2026-02-01','home':'H','away':'A','competition_id':'L1'},{'rest_days_home':7,'rest_days_away':7,'travel_km_home':0,'travel_km_away':0})
        self.assertEqual(x['lineup_delta'],0); self.assertEqual(x['weather_delta'],0); self.assertEqual(x['referee_delta'],0)
if __name__=='__main__': unittest.main()
