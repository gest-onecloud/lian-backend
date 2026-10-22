import os
import unittest
from unittest.mock import patch

import backend.server as server


class _FakeSync:
    def __init__(self, repo):
        self.repo = repo
        self.upserts = []

    def sync_window_cached(self, start, days=30, force=True):
        return {'start': start, 'end': start, 'reports': [], 'match_count': 0}

    def _upsert(self, event, date, url, source):
        self.upserts.append((event, date, url, source))
        return True


class UniversalSearchRuntimeV617(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'LIAN_DISABLE_LIVE_FIXTURES': '0'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_pair_query_executes_pair_discovery(self):
        initial = {'found': False, 'query': 'Valencia vs Barcelona', 'candidates': []}
        discovered = {
            'found': True,
            'candidates': [{
                'id': 'v-b', 'home': 'Valencia CF', 'away': 'FC Barcelona',
                'date': '2026-09-06', 'league': 'LaLiga', 'source': 'SOFA'
            }],
            'sources': {'Valencia': {'teams': ['Valencia CF']}, 'Barcelona': {'teams': ['FC Barcelona']}}
        }
        canonical_after = {'found': True, 'match': discovered['candidates'][0], 'candidates': discovered['candidates']}
        calls = []

        def fake_canonical(repo, term, mid=None):
            calls.append((term, mid))
            return initial if len(calls) == 1 else canonical_after

        def fake_pair(*args, **kwargs):
            calls.append(('pair', args[0]))
            return discovered

        def fake_team(*args, **kwargs):
            raise AssertionError('single-team discovery was incorrectly selected')

        with patch.object(server, 'FixtureSync', _FakeSync), \
             patch.object(server, 'canonical', fake_canonical), \
             patch('backend.services.targeted_search.discover_calendar', return_value={'found':False,'candidates':[],'sources':{}}), \
             patch('backend.services.targeted_search.discover_pair', fake_pair), \
             patch('backend.services.targeted_search.discover_team', fake_team):
            result = server.universal_search(object(), 'Valencia vs Barcelona')

        self.assertTrue(result['found'])
        self.assertEqual(result['match']['id'], 'v-b')
        self.assertTrue(any(c == ('pair', 'Valencia vs Barcelona') for c in calls))

    def test_single_team_executes_team_discovery(self):
        initial = {
            'found': True,
            'match': {'id': 'old', 'home': 'Elche', 'away': 'FC Barcelona', 'date': '2026-08-23', 'status': 'finished'},
            'candidates': [{'id': 'old', 'home': 'Elche', 'away': 'FC Barcelona', 'date': '2026-08-23', 'status': 'finished'}]
        }
        discovered = {
            'found': True,
            'candidates': [{
                'id': 'new', 'home': 'FC Barcelona', 'away': 'Feyenoord',
                'date': '2026-09-09', 'league': 'Champions League', 'source': 'SOFA'
            }],
            'sources': {'Barcelona': {'teams': ['FC Barcelona']}}
        }
        canonical_after = {'found': True, 'match': discovered['candidates'][0], 'candidates': discovered['candidates']}
        calls = []

        def fake_canonical(repo, term, mid=None):
            calls.append((term, mid))
            return initial if len(calls) == 1 else canonical_after

        def fake_pair(*args, **kwargs):
            raise AssertionError('pair discovery was incorrectly selected')

        def fake_team(*args, **kwargs):
            calls.append(('team', args[0]))
            return discovered

        with patch.object(server, 'FixtureSync', _FakeSync), \
             patch.object(server, 'canonical', fake_canonical), \
             patch('backend.services.targeted_search.discover_calendar', return_value={'found':False,'candidates':[],'sources':{}}), \
             patch('backend.services.targeted_search.discover_pair', fake_pair), \
             patch('backend.services.targeted_search.discover_team', fake_team):
            result = server.universal_search(object(), 'Barcelona')

        self.assertTrue(result['found'])
        self.assertEqual(result['match']['id'], 'new')
        self.assertTrue(any(c == ('team', 'Barcelona') for c in calls))

    def test_failed_discovery_does_not_promote_historical_fixture(self):
        initial = {
            'found': True,
            'match': {'id': 'old', 'home': 'Elche', 'away': 'FC Barcelona', 'date': '2026-08-23', 'status': 'finished'},
            'candidates': [{'id': 'old', 'home': 'Elche', 'away': 'FC Barcelona', 'date': '2026-08-23', 'status': 'finished'}]
        }
        with patch.object(server, 'FixtureSync', _FakeSync), \
             patch.object(server, 'canonical', return_value=initial), \
             patch('backend.services.targeted_search.discover_calendar', return_value={'found':False,'candidates':[],'sources':{}}), \
             patch('backend.services.targeted_search.discover_team', return_value={'found': False, 'candidates': [], 'sources': {}}):
            result = server.universal_search(object(), 'Barcelona')

        self.assertFalse(result['found'])
        self.assertIn('históricos', result['reason'])
        self.assertEqual(result['historical_candidates'][0]['id'], 'old')


if __name__ == '__main__':
    unittest.main()
