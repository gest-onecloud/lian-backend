import datetime as dt
import unittest
from unittest.mock import patch

from backend.services.targeted_search import discover_calendar


class UniversalSearchRootV618(unittest.TestCase):
    def test_broad_calendar_pair_finds_requested_fixture_without_team_lookup(self):
        import backend.services.targeted_search as t
        def fake_day(date, timeout=6):
            if date == '2026-09-06':
                return [
                    {'id':'wrong','home':'Elche CF','away':'FC Barcelona','date':date,'league':'LaLiga'},
                    {'id':'right','home':'Valencia CF','away':'FC Barcelona','date':date,'league':'LaLiga'},
                ]
            return []
        with patch.object(t, '_calendar_events', fake_day):
            x=discover_calendar('Valencia vs Barcelona',today=dt.date(2026,9,2),days=5)
        self.assertTrue(x['found'])
        self.assertEqual([m['id'] for m in x['candidates']], ['right'])

    def test_broad_calendar_single_team_returns_future_match(self):
        import backend.services.targeted_search as t
        def fake_day(date, timeout=6):
            if date == '2026-09-06':
                return [{'id':'right','home':'Valencia CF','away':'FC Barcelona','date':date,'league':'LaLiga'}]
            return []
        with patch.object(t, '_calendar_events', fake_day):
            x=discover_calendar('Barcelona',today=dt.date(2026,9,2),days=5)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['id'], 'right')

    def test_root_fix_window_covers_september_19(self):
        self.assertGreaterEqual(dt.date(2026,9,3)+dt.timedelta(days=21), dt.date(2026,9,19))


if __name__ == '__main__':
    unittest.main()
