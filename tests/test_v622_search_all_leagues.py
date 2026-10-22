import datetime as dt
import unittest
from unittest.mock import patch

import backend.services.targeted_search as t

class SearchAllLeaguesV622(unittest.TestCase):
    def test_broad_discovery_does_not_stop_when_espn_has_records(self):
        def fake_range(start, end, timeout=8):
            return ([{'id':'pl','home':'Arsenal','away':'Chelsea','date':'2026-09-06','league':'Premier League'}],
                    [{'source':'ESPN_ALL_RANGE','ok':True,'records':1}])
        def fake_day(date, timeout=6):
            if date == '2026-09-06':
                return [{'id':'mx','home':'Santos Laguna','away':'Cruz Azul','date':date,'league':'Liga MX','source':'SOFA_CALENDAR'}]
            return []
        with patch.object(t,'_calendar_events_range',fake_range), patch.object(t,'_calendar_events',fake_day):
            x=t.discover_calendar('Cruz Azul',today=dt.date(2026,9,3),days=5)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['id'],'mx')

    def test_universal_single_team_returns_all_current_future_competitions(self):
        import backend.server as server
        class Sync:
            def __init__(self, repo): pass
            def sync_window_cached(self, start, days=30, force=True): return {'start':start,'match_count':0}
            def _upsert(self, *args, **kwargs): return True
        local={'found':False,'candidates':[]}
        discovered={'found':True,'candidates':[
            {'id':'a','home':'Cruz Azul','away':'Santos Laguna','date':'2026-09-06','league':'Liga MX','source':'SOFA'},
            {'id':'b','home':'Cruz Azul','away':'Inter Miami','date':'2026-09-10','league':'CONCACAF Champions Cup','source':'SOFA'}], 'sources':{}}
        def canonical(repo, term, mid=None):
            return {'found':True,'candidates':discovered['candidates']} if term=='Cruz Azul' and getattr(server,'_test_discovered',False) else local
        with patch.object(server,'FixtureSync',Sync), patch.object(server,'canonical',canonical), \
             patch.object(server,'mexico_today_iso',return_value='2026-09-03'), \
             patch('backend.services.targeted_search.discover_team',return_value={'found':False,'candidates':[],'sources':{}}), \
             patch('backend.services.targeted_search.discover_calendar',return_value=discovered):
            server._test_discovered=True
            try:
                x=server.universal_search(object(),'Cruz Azul')
            finally:
                server._test_discovered=False
        self.assertTrue(x['found']); self.assertTrue(x['ambiguous'])
        self.assertEqual([m['id'] for m in x['candidates']],['a','b'])

    def test_pair_is_strict_after_multi_source_merge(self):
        def fake_day(date, timeout=6):
            if date=='2026-09-06':
                return [
                    {'id':'wrong','home':'Santos Laguna','away':'Cruz Azul','date':date,'league':'Liga MX'},
                    {'id':'right','home':'Cruz Azul','away':'Santos Laguna','date':date,'league':'Liga MX'}]
            return []
        with patch.object(t,'_calendar_events_range',return_value=([],[])), patch.object(t,'_calendar_events',fake_day):
            x=t.discover_calendar('Cruz Azul vs Santos',today=dt.date(2026,9,3),days=5)
        self.assertTrue(x['found'])
        self.assertEqual([m['id'] for m in x['candidates']],['right'])

if __name__=='__main__': unittest.main()
