import datetime as dt
import shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
import backend.services.fixture_sync as fs
import backend.services.targeted_search as ts
from backend.server import dedup_fixtures
ROOT=Path(__file__).resolve().parents[1]

class V641CalendarSources(unittest.TestCase):
    def test_fotmob_payload_is_normalized_without_loss(self):
        payload={'leagues':[
            {'name':'LaLiga','matches':[{'id':1,'home':{'name':'Real Betis'},'away':{'name':'Real Madrid'},'status':{'utcTime':'2026-09-04T19:00:00Z','finished':False}}]},
            {'name':'Ligue 1','matches':[{'id':2,'home':{'name':'Lyon'},'away':{'name':'Auxerre'},'status':{'utcTime':'2026-09-04T17:00:00Z','finished':False}}, {'id':3,'home':{'name':'PSG'},'away':{'name':'Monaco'},'status':{'utcTime':'2026-09-04T19:05:00Z','finished':False}}]},
        ]}
        td=Path(tempfile.mkdtemp(prefix='lian641_'))
        try:
            r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            with patch.object(fx,'_get_json',return_value=payload):
                rows,url=fx.fetch_fotmob_day('2026-09-04')
            self.assertEqual(len(rows),3)
            self.assertEqual({x['league'] for x in rows},{'LaLiga','Ligue 1'})
            self.assertEqual(rows[0]['home'],'Real Betis')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_live_empty_is_never_marked_complete_empty(self):
        td=Path(tempfile.mkdtemp(prefix='lian641_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            with patch.object(fx,'fetch_espn_all',return_value=([],'e')), patch.object(fx,'fetch_sofascore_day',return_value=([],'s')), patch.object(fx,'fetch_fotmob_day',return_value=([],'f')), patch.object(fx,'fetch_thesportsdb',return_value=([],'t')), patch.object(fx,'fetch_espn',return_value=([],'league')):
                x=fx.sync_day_light('2026-09-04')
            self.assertNotEqual(x['coverage_status'],'complete-empty')
            self.assertEqual(x['coverage_status'],'incomplete')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_stale_complete_empty_cache_is_not_reused(self):
        td=Path(tempfile.mkdtemp(prefix='lian641cache_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            fx.ensure_cache_schema(); fx._cache_set('2026-09-04','complete-empty',0)
            with patch.object(fx,'sync_day_light',return_value={'date':'2026-09-04','match_count':7,'coverage_status':'partial','source_counts':{}}) as run:
                x=fx.sync_day_light_cached('2026-09-04',force=False)
            self.assertTrue(run.called)
            self.assertEqual(x['coverage_status'],'partial')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_calendar_dedup_ignores_provider_time_representation(self):
        rows=[
            {'id':'a','date':'2026-09-06','time':'20:00','home':'Cruz Azul','away':'Santos Laguna','competition':'Liga MX'},
            {'id':'b','date':'2026-09-07','time':'02:00','home':'Cruz Azul FC','away':'Santos','competition':''},
        ]
        self.assertEqual(len(dedup_fixtures(rows)),1)

    def test_team_search_keeps_all_upcoming_fixtures_and_does_not_cap_at_twenty(self):
        fixtures=[{'id':str(i),'home':'Cruz Azul','away':f'Rival {i}','date':f'2026-09-{6+i:02d}','league':'Liga MX'} for i in range(1,22)]
        with patch.object(ts,'_team_candidates',return_value=[('TEST','1','Cruz Azul',{})]), patch.object(ts,'_events_for',return_value=fixtures):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,4),days=30,timeout=1)
        self.assertEqual(len(x['candidates']),21)

    def test_broad_discovery_can_find_multiple_leagues(self):
        def fake_fotmob(date,timeout):
            return ([{'id':date+'a','home':'Real Betis','away':'Real Madrid','league':'LaLiga','date':date,'time':'13:00','timestamp':'2026-09-04T19:00:00Z'},
                     {'id':date+'b','home':'Lyon','away':'Auxerre','league':'Ligue 1','date':date,'time':'11:00','timestamp':'2026-09-04T17:00:00Z'}], 'fotmob')
        with patch.object(ts,'_fotmob_events',side_effect=fake_fotmob), patch.object(ts,'_get',return_value={'events':[]}):
            x=ts.discover_calendar('Real Madrid',today=dt.date(2026,9,4),days=1,timeout=1)
        self.assertTrue(x['found'])
        self.assertEqual(len(x['candidates']),1)
        self.assertEqual(x['candidates'][0]['home'],'Real Betis')

    def test_model_core_hash_unchanged(self):
        import hashlib
        h=hashlib.sha256((ROOT/'backend/core/model.py').read_bytes()).hexdigest()
        self.assertEqual(h,'ab9af7a7a98240bbbd86a8e4a6d34d5f3767e0c3efd98f77a7d0458d4e8294f9')

if __name__=='__main__': unittest.main()
