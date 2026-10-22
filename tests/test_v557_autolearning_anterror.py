import pathlib, shutil, tempfile, unittest, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.learning.adaptive_engine import AdaptiveLearningEngine

class V557AutoLearningAntiError(unittest.TestCase):
    def make_repo(self):
        td=tempfile.mkdtemp(); db=pathlib.Path(td)/'x.db'; r=Repo(db)
        c=r.connect(); c.executescript('''CREATE TABLE matches(id TEXT PRIMARY KEY,date TEXT,home TEXT,away TEXT,home_score INTEGER,away_score INTEGER,status TEXT,competition_id TEXT,competition TEXT,region TEXT,country TEXT,time TEXT,source TEXT); CREATE TABLE predictions(match_id TEXT PRIMARY KEY,model_version TEXT,p_home REAL,p_draw REAL,p_away REAL,pick TEXT,confidence REAL,evidence REAL,expected_goals REAL,generated_at TEXT);'''); c.close(); r.init_learning(); return td,r
    def test_authoritative_outcome_and_repair(self):
        td,r=self.make_repo()
        try:
            r.execute("INSERT INTO matches(id,date,home,away,home_score,away_score,status,competition_id,competition) VALUES(?,?,?,?,?,?,?,?,?)",('m1','2026-08-20','Acassuso','San Telmo',1,2,'finished','ARG','Argentina'))
            r.execute("INSERT INTO predictions VALUES('m1','55.6',.40,.27,.33,'1',.40,.50,2.0,'now')")
            r.execute("INSERT INTO postmatch_reviews(match_id,model_version,predicted,actual,brier,log_loss,goal_error,calibration_gap,diagnosis) VALUES('m1','55.6','1','1',0,0,0,0,'[]')")
            x=AdaptiveLearningEngine(r).repair_reviews(); rev=r.one("SELECT predicted,actual FROM postmatch_reviews WHERE match_id='m1'")
            self.assertEqual(rev['predicted'],'1'); self.assertEqual(rev['actual'],'2'); self.assertEqual(x['repaired'],1)
        finally: shutil.rmtree(td)
    def test_no_future_leakage(self):
        td,r=self.make_repo()
        try:
            for i,d in enumerate(['2026-08-01','2026-08-10']):
                r.execute("INSERT INTO matches(id,date,home,away,home_score,away_score,status,competition_id,competition) VALUES(?,?,?,?,?,?,?,?,?)",(f'm{i}',d,'A','B',1,0,'finished','L','L'))
                r.execute("INSERT INTO predictions VALUES(?,?,?,?,?,?,?,?,?,?)",(f'm{i}','55.7',.7,.1,.2,'1',.7,.8,1.5,'2026-07-31' if i==0 else '2026-08-11'))
            e=AdaptiveLearningEngine(r); e.repair_reviews(); w=e.outcome_weights_as_of('2026-08-05'); self.assertEqual(w['samples'],1)
        finally: shutil.rmtree(td)

if __name__=='__main__': unittest.main()


from backend.learning.antierror import AntiError

def _antierror_regression():
    assert AntiError.verdict('1', AntiError.actual(1,2)) == 'FALLA'
