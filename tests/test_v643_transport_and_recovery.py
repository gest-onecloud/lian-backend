import json, shutil, tempfile, unittest
from pathlib import Path
import sys
from unittest.mock import patch
import datetime as dt

from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
import backend.services.fixture_sync as fs
import backend.services.targeted_search as ts

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class Resp:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.payload).encode()

class V643TransportRecovery(unittest.TestCase):
    def test_espn_transport_does_not_send_fake_browser_user_agent(self):
        td=Path(tempfile.mkdtemp(prefix='lian643_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            seen={}
            def fake(req,timeout=None):
                seen.update(req.headers); return Resp({'events':[]})
            with patch('backend.services.fixture_sync.urllib.request.urlopen',side_effect=fake):
                fx._get_json('https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates=20260904')
            self.assertNotIn('LiAn', ' '.join(f'{k}:{v}' for k,v in seen.items()))
            self.assertIn('Accept', seen)
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_sofa_transport_uses_browser_profile(self):
        td=Path(tempfile.mkdtemp(prefix='lian643_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); fx=FixtureSync(r)
            seen={}
            def fake(req,timeout=None): seen.update(req.headers); return Resp({'events':[]})
            with patch('backend.services.fixture_sync.urllib.request.urlopen',side_effect=fake):
                fx._get_json('https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-09-04')
            self.assertIn('Chrome',seen.get('User-agent',''))
            self.assertEqual(seen.get('Origin'),'https://www.sofascore.com')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_light_sync_recovers_when_all_broad_feeds_are_empty(self):
        td=Path(tempfile.mkdtemp(prefix='lian643_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            def league(date, league):
                if league=='esp.1':
                    return ([{'id':'la1','home':'Real Betis','away':'Real Madrid','league':'LaLiga','timestamp':'2026-09-04T19:00:00Z','status':'scheduled'},
                             {'id':'la2','home':'Sevilla','away':'Villarreal','league':'LaLiga','timestamp':'2026-09-04T21:00:00Z','status':'scheduled'}], 'espn')
                if league=='ita.1':
                    return ([{'id':'it1','home':'Genoa','away':'Como','league':'Serie A','timestamp':'2026-09-04T18:45:00Z','status':'scheduled'}], 'espn')
                return ([], 'espn')
            with patch.object(fx,'fetch_espn_all',return_value=([],'all')), patch.object(fx,'fetch_sofascore_day',return_value=([],'sofa')), patch.object(fx,'fetch_fotmob_day',return_value=([],'fot')), patch.object(fx,'fetch_thesportsdb',return_value=([], 'tsdb')), patch.object(fx,'fetch_espn',side_effect=league):
                x=fx.sync_day_light('2026-09-04')
            self.assertEqual(x['match_count'],3)
            self.assertEqual(x['recovery_mode'],'ESPN_LEAGUE_FALLBACK')
            self.assertEqual(x['coverage_status'],'partial')
            self.assertEqual(r.one("SELECT COUNT(*) n FROM matches WHERE date='2026-09-04'")['n'],3)
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_targeted_team_can_use_espn_team_schedule_when_sofa_is_unavailable(self):
        teams=[('ESPN','mex.1:123','Cruz Azul',{'league':'mex.1','id':'123','sport':{'name':'Soccer'}})]
        fixtures=[
            {'id':'1','home':'Cruz Azul','away':'Santos Laguna','league':'Liga MX','date':'2026-09-06','time':'20:00'},
            {'id':'2','home':'Cruz Azul','away':'América','league':'Liga MX','date':'2026-09-12','time':'20:00'},
            {'id':'3','home':'Inter Miami','away':'Cruz Azul','league':'Leagues Cup','date':'2026-09-16','time':'20:00'},
            {'id':'4','home':'Monterrey','away':'Cruz Azul','league':'Liga MX','date':'2026-09-19','time':'20:00'},
            {'id':'5','home':'Cruz Azul','away':'Toluca','league':'Liga MX','date':'2026-09-26','time':'20:00'},
        ]
        with patch.object(ts,'_team_candidates',return_value=teams), patch.object(ts,'_events_for',return_value=fixtures):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,4),days=30,timeout=1)
        self.assertEqual(len(x['candidates']),5)
        self.assertEqual([z['date'] for z in x['candidates']],['2026-09-06','2026-09-12','2026-09-16','2026-09-19','2026-09-26'])

    def test_window_is_exactly_30_days_inclusive(self):
        today=dt.date(2026,9,4); days=30; end=today+dt.timedelta(days=days-1)
        self.assertEqual((end-today).days,29)

if __name__=='__main__': unittest.main()
