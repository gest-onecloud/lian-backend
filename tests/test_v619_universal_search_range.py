import datetime as dt
import unittest
from unittest.mock import patch
import backend.services.targeted_search as t

class UniversalSearchRangeV619(unittest.TestCase):
    def _event(self, home, away, date='2026-09-06'):
        return {
            'id':'401882888','date':date+'T21:15:00Z',
            'competitions':[{
                'league':{'name':'LaLiga'},
                'competitors':[
                    {'homeAway':'home','team':{'displayName':home}},
                    {'homeAway':'away','team':{'displayName':away}}
                ],
                'status':{'type':{'name':'STATUS_SCHEDULED'}}
            }]
        }
    def test_range_provider_finds_pair(self):
        def fake_get(url, timeout=8):
            self.assertIn('dates=20260902-20260922', url)
            return {'events':[self._event('Valencia CF','FC Barcelona')]}
        with patch.object(t,'_get',fake_get):
            x=t.discover_calendar('Valencia vs Barcelona',today=dt.date(2026,9,2),days=21)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['home'],'Valencia CF')
        self.assertEqual(x['candidates'][0]['away'],'FC Barcelona')

    def test_range_provider_finds_future_team(self):
        def fake_get(url, timeout=8):
            return {'events':[self._event('FC Barcelona','Feyenoord','2026-09-09')]}
        with patch.object(t,'_get',fake_get):
            x=t.discover_calendar('Barcelona',today=dt.date(2026,9,2),days=21)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['home'],'FC Barcelona')

    def test_range_diagnostics_expose_source_failure(self):
        def bad(url, timeout=8): raise OSError('DNS failure')
        with patch.object(t,'_get',bad):
            x=t.discover_calendar('Barcelona',today=dt.date(2026,9,2),days=2)
        self.assertTrue(x['sources']['diagnostics'])
        self.assertTrue(any(d.get('ok') is False for d in x['sources']['diagnostics']))

if __name__=='__main__': unittest.main()
