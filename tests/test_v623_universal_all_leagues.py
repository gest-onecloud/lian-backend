import datetime as dt
import unittest
from unittest.mock import patch
import backend.services.targeted_search as ts

class UniversalAllLeaguesV623(unittest.TestCase):
    def test_team_discovery_is_not_league_whitelisted(self):
        fixtures = [
            {'id':'mx','home':'Cruz Azul','away':'Santos Laguna','date':'2026-09-06','league':'Liga MX'},
            {'id':'es','home':'Valencia','away':'Barcelona','date':'2026-09-07','league':'LaLiga'},
            {'id':'de','home':'Bayern Munich','away':'Dortmund','date':'2026-09-08','league':'Bundesliga'},
            {'id':'it','home':'Inter','away':'Milan','date':'2026-09-09','league':'Serie A'},
            {'id':'fr','home':'PSG','away':'Lyon','date':'2026-09-10','league':'Ligue 1'},
            {'id':'br','home':'Flamengo','away':'Palmeiras','date':'2026-09-11','league':'Brasileirao'},
        ]
        def fake_events(source, team_id, timeout=6):
            names={'Cruz Azul':'Cruz Azul','Valencia':'Valencia','Bayern':'Bayern Munich','Inter':'Inter','PSG':'PSG','Flamengo':'Flamengo'}
            wanted=names.get(team_id,team_id)
            return [x for x in fixtures if ts.team_eq(x['home'],wanted) or ts.team_eq(x['away'],wanted)]
        mapping={
            'Cruz Azul':[('SOFA','Cruz Azul','Cruz Azul',{})],
            'Valencia':[('SOFA','Valencia','Valencia',{})],
            'Bayern':[('SOFA','Bayern','Bayern Munich',{})],
            'Inter':[('SOFA','Inter','Inter',{})],
            'PSG':[('SOFA','PSG','PSG',{})],
            'Flamengo':[('SOFA','Flamengo','Flamengo',{})],
        }
        with patch.object(ts,'_team_candidates',side_effect=lambda q,timeout=6:mapping[q]), patch.object(ts,'_events_for',side_effect=fake_events):
            for q,expected in [('Cruz Azul','Liga MX'),('Valencia','LaLiga'),('Bayern','Bundesliga'),('Inter','Serie A'),('PSG','Ligue 1'),('Flamengo','Brasileirao')]:
                x=ts.discover_team(q,today=dt.date(2026,9,3),days=20,timeout=1)
                self.assertTrue(x['found'],q)
                self.assertEqual(x['candidates'][0]['league'],expected)

    def test_sofascore_next_search_uses_multiple_pages(self):
        calls=[]
        def fake_get(url,timeout=6):
            calls.append(url)
            if '/events/next/4' in url:
                return {'events':[{'id':'late','homeTeam':{'name':'Cruz Azul'},'awayTeam':{'name':'Santos'},'startTimestamp':1788652800,'tournament':{'name':'Liga MX'},'status':{'type':'scheduled'}}]}
            return {'events':[]}
        with patch.object(ts,'_get',side_effect=fake_get), patch.object(ts,'_team_candidates',return_value=[('SOFA','123','Cruz Azul',{})]):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,3),days=20,timeout=1)
        self.assertTrue(x['found'])
        self.assertTrue(any('/events/next/4' in u for u in calls))

    def test_pair_is_still_strict_across_leagues(self):
        events=[
            {'id':'wrong','home':'Santos','away':'Cruz Azul','date':'2026-09-06','league':'Liga MX'},
            {'id':'right','home':'Cruz Azul','away':'Santos','date':'2026-09-06','league':'Liga MX'},
        ]
        with patch.object(ts,'_calendar_events_range',return_value=(events,[{'source':'TEST','ok':True}])), patch.object(ts,'_calendar_events',return_value=[]):
            x=ts.discover_calendar('Cruz Azul vs Santos',today=dt.date(2026,9,3),days=7,timeout=1)
        self.assertTrue(x['found'])
        self.assertEqual([e['id'] for e in x['candidates']],['right'])

if __name__=='__main__': unittest.main()
