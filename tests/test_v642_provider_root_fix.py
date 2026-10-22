import datetime as dt
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
import backend.services.fixture_sync as fs
import backend.services.targeted_search as ts

ROOT=Path(__file__).resolve().parents[1]

class V642ProviderRootFix(unittest.TestCase):
    def test_sofascore_uses_api_host(self):
        self.assertEqual(fs.SOFASCORE_DAY,'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}')
        self.assertEqual(ts.SOFA_SEARCH,'https://api.sofascore.com/api/v1/search/all')
        self.assertEqual(ts.SOFA_NEXT,'https://api.sofascore.com/api/v1/team/{team_id}/events/next/{page}')

    def test_espn_all_has_web_host_fallback(self):
        self.assertEqual(fs.ESPN_ALL_ALT,'https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard')
        td=Path(tempfile.mkdtemp(prefix='lian642_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            payload={'events':[{'id':'E1','date':'2026-09-04T19:00:00Z','season':{'slug':'2026'},'competitions':[{'league':{'name':'LaLiga'},'competitors':[{'homeAway':'home','team':{'displayName':'Real Betis'}},{'homeAway':'away','team':{'displayName':'Real Madrid'}}],'status':{'type':{'name':'STATUS_SCHEDULED'}}}]}]}
            calls=[]
            def fake(url):
                calls.append(url)
                if url.startswith(fs.ESPN_ALL_BASE): raise OSError('blocked primary host')
                return payload
            with patch.object(fx,'_get_json',side_effect=fake):
                rows,url=fx.fetch_espn_all('2026-09-04')
            self.assertEqual(len(rows),1); self.assertIn('site.web.api.espn.com',url); self.assertEqual(len(calls),2)
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_day_union_survives_primary_provider_failure(self):
        td=Path(tempfile.mkdtemp(prefix='lian642union_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            espn=[{'id':'e1','home':'Ipswich Town','away':'Liverpool','league':'Premier League','timestamp':'2026-09-04T19:00:00Z','status':'scheduled'}]
            sofa=[
              {'id':'s1','home':'Real Betis','away':'Real Madrid','league':'LaLiga','timestamp':'2026-09-04T19:00:00Z','status':'scheduled'},
              {'id':'s2','home':'Genoa','away':'Como','league':'Serie A','timestamp':'2026-09-04T18:45:00Z','status':'scheduled'},
              {'id':'s3','home':'Stuttgart','away':'FC Cologne','league':'Bundesliga','timestamp':'2026-09-04T18:30:00Z','status':'scheduled'},
              {'id':'s4','home':'Lyon','away':'Auxerre','league':'Ligue 1','timestamp':'2026-09-04T17:00:00Z','status':'scheduled'},
              {'id':'s5','home':'PSG','away':'Monaco','league':'Ligue 1','timestamp':'2026-09-04T19:05:00Z','status':'scheduled'},
            ]
            with patch.object(fx,'fetch_espn_all',return_value=(espn,'espn')), patch.object(fx,'fetch_sofascore_day',return_value=(sofa,'sofa')), patch.object(fx,'fetch_fotmob_day',return_value=([],'fot')), patch.object(fx,'fetch_thesportsdb',return_value=([],'tsdb')), patch.object(fx,'fetch_espn',return_value=([],'')):
                x=fx.sync_day_light('2026-09-04')
            self.assertEqual(x['match_count'],6)
            self.assertEqual(r.one("SELECT COUNT(*) n FROM matches WHERE date='2026-09-04'")['n'],6)
            self.assertEqual(x['source_counts']['SOFASCORE'],5)
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_targeted_team_uses_sofascore_schedule_and_returns_all_future_matches(self):
        fixtures=[]
        for i,(d,h,a) in enumerate([
            ('2026-09-06','Cruz Azul','Santos Laguna'),
            ('2026-09-12','Cruz Azul','América'),
            ('2026-09-16','Inter Miami','Cruz Azul'),
            ('2026-09-19','Monterrey','Cruz Azul'),
            ('2026-09-26','Cruz Azul','Toluca')]):
            fixtures.append({'id':str(i+1),'home':h,'away':a,'league':'Liga MX','date':d})
        with patch.object(ts,'_team_candidates',return_value=[('SOFA','123','Cruz Azul',{'sport':{'name':'Football'}})]), patch.object(ts,'_events_for',return_value=fixtures):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,4),days=30,timeout=1)
        self.assertEqual(len(x['candidates']),5)
        self.assertEqual([z['date'] for z in x['candidates']],['2026-09-06','2026-09-12','2026-09-16','2026-09-19','2026-09-26'])

if __name__=='__main__': unittest.main()
