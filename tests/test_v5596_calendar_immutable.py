import datetime as dt, unittest, tempfile, shutil
from pathlib import Path
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync, _mx_date_from_iso

ROOT=Path(__file__).resolve().parents[1]

class FakeBroadSync(FixtureSync):
    def fetch_espn_all(self,date):
        return ([{'id':'e1','home':'Alpha FC','away':'Beta FC','league':'League A','timestamp':date+'T23:00:00Z'},
                 {'id':'e2','home':'Gamma FC','away':'Delta FC','league':'League A','timestamp':date+'T23:30:00Z'}], 'test://espn-all')
    def fetch_sofascore_day(self,date):
        return ([{'id':'s1','home':'Alpha F.C.','away':'Beta FC','league':'League A','timestamp':date+'T23:00:00Z'},
                 {'id':'s2','home':'Epsilon FC','away':'Zeta FC','league':'League B','timestamp':date+'T20:00:00Z'}], 'test://sofascore')
    def fetch_espn(self,date,league): return ([], 'test://espn/'+league)
    def fetch_thesportsdb(self,date): return ([{'id':'t1','home':'Eta FC','away':'Theta FC','league':'League C','strDate':date,'strTime':'20:00'}], 'test://sportsdb')

class CalendarImmutableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._td=tempfile.mkdtemp(prefix='lian_calendar_immutable_')
        cls._db=Path(cls._td)/'lian.db'
        shutil.copy2(ROOT/'data'/'lian.db',cls._db)
        cls.r=Repo(cls._db); cls.r.init_learning()
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._td,ignore_errors=True)
    def test_multi_source_union_and_dedupe(self):
        fx=FakeBroadSync(self.r); d='2099-01-05'; r=fx.sync_day(d)
        self.assertEqual(r['coverage_status'],'complete')
        self.assertEqual(r['source_counts']['ESPN_ALL'],2)
        self.assertEqual(r['source_counts']['SOFASCORE'],2)
        self.assertEqual(r['match_count'],4)
        self.assertEqual(len(self.r.rows('SELECT * FROM matches WHERE date=?',(d,))),4)
    def test_material_disagreement_is_partial(self):
        fx=FakeBroadSync(self.r); d='2099-01-06'
        fx.fetch_espn_all=lambda date: ([{'id':str(i),'home':f'A{i}','away':f'B{i}','league':'L','timestamp':date+'T12:00:00Z'} for i in range(2)],'test://e')
        fx.fetch_sofascore_day=lambda date: ([{'id':str(i),'home':f'C{i}','away':f'D{i}','league':'L','timestamp':date+'T12:00:00Z'} for i in range(20)],'test://s')
        fx.fetch_espn=lambda date,league:([], 'test://x'); fx.fetch_thesportsdb=lambda date:([], 'test://t')
        r=fx.sync_day(d)
        self.assertEqual(r['coverage_status'],'partial')
    def test_mexico_date_gate(self):
        self.assertEqual(_mx_date_from_iso('2026-08-26T05:00:00Z'),'2026-08-25')
        self.assertEqual(_mx_date_from_iso('2026-08-26T18:00:00Z'),'2026-08-26')

if __name__=='__main__': unittest.main()
