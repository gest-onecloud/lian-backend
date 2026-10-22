import json, unittest, tempfile, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync, _mx_date_from_iso

class FakeCalendarSync(FixtureSync):
    def fetch_espn_all(self,date):
        return ([
            {'id':'1','home':'A','away':'B','league':'Test League','timestamp':date+'T23:00:00Z','status':'STATUS_SCHEDULED'},
            {'id':'2','home':'C','away':'D','league':'Test League','timestamp':date+'T23:30:00Z','status':'STATUS_SCHEDULED'},
        ], 'test://espn-all')
    def fetch_fotmob_day(self,date): return ([{'id':'f1','home':'A','away':'B','league':'Test League','timestamp':date+'T23:00:00Z'},{'id':'f2','home':'C','away':'D','league':'Test League','timestamp':date+'T23:30:00Z'}], 'test://fotmob')
    def fetch_espn(self,date,league): return ([], 'test://espn/'+league)
    def fetch_thesportsdb(self,date):
        # Simulate the free-tier three-event response; it must not define completeness.
        return ([{'id':'3','home':'E','away':'F','league':'Test League','strDate':date,'strTime':'20:00'}], 'test://sportsdb')

class CalendarFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._td=tempfile.mkdtemp(prefix='lian_calendar_final_')
        cls._db=Path(cls._td)/'lian.db'
        shutil.copy2(ROOT/'data'/'lian.db',cls._db)
        cls.r=Repo(cls._db); cls.r.init_learning()
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._td,ignore_errors=True)
    def test_broad_source_is_authority(self):
        fx=FakeCalendarSync(self.r)
        d='2099-01-02'
        r=fx.sync_day(d)
        self.assertEqual(r['coverage_status'],'complete')
        self.assertEqual(r['match_count'],3)
        self.assertEqual(r['source_counts']['ESPN_ALL'],2)
    def test_cache_never_freezes_partial(self):
        fx=FakeCalendarSync(self.r); d='2099-01-03'
        fx.sync_day(d); self.assertEqual(fx.sync_day_cached(d)['coverage_status'],'complete')
    def test_mexico_date_gate(self):
        self.assertEqual(_mx_date_from_iso('2026-08-26T05:00:00Z'),'2026-08-25')
        self.assertEqual(_mx_date_from_iso('2026-08-26T18:00:00Z'),'2026-08-26')
if __name__=='__main__': unittest.main()
