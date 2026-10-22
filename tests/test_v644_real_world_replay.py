import datetime as dt, unittest
from unittest.mock import patch
import backend.services.targeted_search as ts

class V644RealWorldReplay(unittest.TestCase):
    def test_cruz_azul_30_day_schedule_replay_contains_five_distinct_fixtures(self):
        fixtures=[
            {'id':'ca1','home':'Cruz Azul','away':'Santos Laguna','league':'Liga MX','date':'2026-09-06'},
            {'id':'ca2','home':'Cruz Azul','away':'América','league':'Liga MX','date':'2026-09-12'},
            {'id':'ca3','home':'Inter Miami CF','away':'Cruz Azul','league':'Campeones Cup','date':'2026-09-16'},
            {'id':'ca4','home':'Monterrey','away':'Cruz Azul','league':'Liga MX','date':'2026-09-19'},
            {'id':'ca5','home':'Cruz Azul','away':'Toluca','league':'Liga MX','date':'2026-09-26'},
        ]
        with patch.object(ts,'_team_candidates',return_value=[('SOFA','6578','Cruz Azul',{'sport':{'name':'Football'}})]), patch.object(ts,'_events_for',return_value=fixtures):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,4),days=30,timeout=1)
        self.assertEqual(len(x['candidates']),5)
        self.assertEqual([m['date'] for m in x['candidates']],['2026-09-06','2026-09-12','2026-09-16','2026-09-19','2026-09-26'])

    def test_daily_multi_league_replay_does_not_collapse_to_three(self):
        fixtures=[
            {'id':'1','home':'Ipswich','away':'Liverpool','league':'Premier League','date':'2026-09-04','time':'19:00','timestamp':'2026-09-04T19:00:00Z'},
            {'id':'2','home':'Real Betis','away':'Real Madrid','league':'LaLiga','date':'2026-09-04','time':'19:00','timestamp':'2026-09-04T19:00:00Z'},
            {'id':'3','home':'Genoa','away':'Como','league':'Serie A','date':'2026-09-04','time':'18:45','timestamp':'2026-09-04T18:45:00Z'},
            {'id':'4','home':'VfB Stuttgart','away':'Köln','league':'Bundesliga','date':'2026-09-04','time':'18:30','timestamp':'2026-09-04T18:30:00Z'},
            {'id':'5','home':'Lyon','away':'Auxerre','league':'Ligue 1','date':'2026-09-04','time':'17:00','timestamp':'2026-09-04T17:00:00Z'},
            {'id':'6','home':'PSG','away':'Monaco','league':'Ligue 1','date':'2026-09-04','time':'19:05','timestamp':'2026-09-04T19:05:00Z'},
            {'id':'7','home':'NYCFC','away':'Nashville SC','league':'MLS','date':'2026-09-04','time':'23:30','timestamp':'2026-09-04T23:30:00Z'},
            {'id':'8','home':'Loudoun United FC','away':'Colorado Springs Switchbacks FC','league':'USL Championship','date':'2026-09-04','time':'23:00','timestamp':'2026-09-04T23:00:00Z'},
        ]
        def fake_calendar(date,timeout): return fixtures,'replay'
        with patch.object(ts,'_calendar_events_range',return_value=(fixtures,[])), patch.object(ts,'_calendar_events',return_value=[]):
            x=ts.discover_calendar('Real Betis',today=dt.date(2026,9,4),days=1,timeout=1)
        self.assertTrue(x['found']); self.assertEqual(len(x['candidates']),1)
        self.assertEqual(x['candidates'][0]['home'],'Real Betis')

if __name__=='__main__': unittest.main()
