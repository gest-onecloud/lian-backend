import unittest

from backend.services.universal import resolve
from backend.server import needs_targeted_discovery

class SearchContractV616(unittest.TestCase):
    def test_pair_never_returns_unrelated_future_fixture(self):
        class R:
            def rows(self, q):
                return [
                    {'id':'wrong','home':'Corpus Christi FC','away':'South Georgia Tormenta','competition':'USL','date':'2026-09-02','status':'scheduled'},
                    {'id':'right','home':'Valencia CF','away':'FC Barcelona','competition':'LaLiga','date':'2026-09-06','status':'scheduled'},
                ]
        self.assertEqual([x['id'] for x in resolve(R(),'Valencia vs Barcelona')], ['right'])

    def test_single_team_never_returns_unrelated_future_fixture(self):
        class R:
            def rows(self, q):
                return [
                    {'id':'wrong','home':'Corpus Christi FC','away':'South Georgia Tormenta','competition':'USL','date':'2026-09-02','status':'scheduled'},
                    {'id':'right','home':'FC Barcelona','away':'Feyenoord','competition':'Champions League','date':'2026-09-09','status':'scheduled'},
                ]
        self.assertEqual([x['id'] for x in resolve(R(),'Barcelona')], ['right'])

    def test_targeted_discovery_is_required_for_stale_single_team_results(self):
        import datetime as dt
        result={'found':False,'candidates':[{'date':'2026-08-31','home':'Elche','away':'FC Barcelona'}]}
        self.assertTrue(needs_targeted_discovery('Barcelona',result,dt.date(2026,9,2)))

    def test_targeted_discovery_is_required_for_stale_explicit_pair(self):
        import datetime as dt
        result={'found':True,'match':{'date':'2026-08-31','home':'Elche','away':'FC Barcelona'}}
        self.assertFalse(needs_targeted_discovery('Valencia vs Barcelona',result,dt.date(2026,9,2)))
        self.assertTrue(needs_targeted_discovery('Valencia vs Barcelona',{'found':False},dt.date(2026,9,2)))

    def test_targeted_discovery_not_needed_when_single_team_has_future_match(self):
        import datetime as dt
        result={'found':True,'candidates':[{'date':'2026-09-06','home':'Valencia CF','away':'FC Barcelona'}]}
        self.assertFalse(needs_targeted_discovery('Barcelona',result,dt.date(2026,9,2)))

    def test_single_team_can_return_recent_historical_fixture_but_future_ranks_first(self):
        class R:
            def rows(self, q):
                return [
                    {'id':'old','home':'Elche','away':'FC Barcelona','competition':'LaLiga','date':'2026-08-31','status':'finished'},
                    {'id':'new','home':'FC Barcelona','away':'Feyenoord','competition':'Champions League','date':'2026-09-09','status':'scheduled'},
                ]
        result=resolve(R(),'Barcelona')
        self.assertEqual(result[0]['id'], 'new')
        self.assertEqual(result[1]['id'], 'old')

if __name__ == '__main__':
    unittest.main()

class TargetedSearchContractV616(unittest.TestCase):
    def test_targeted_pair_discovers_requested_fixture_without_local_index(self):
        from unittest.mock import patch
        import datetime as dt
        import backend.services.targeted_search as t
        def teams(name, timeout=6): return [('FAKE','1',name,{})]
        def events(source, tid, timeout=6):
            return [{'id':'wrong','home':'Elche','away':'FC Barcelona','date':'2026-09-06','league':'LaLiga'},
                    {'id':'right','home':'Valencia CF','away':'FC Barcelona','date':'2026-09-06','league':'LaLiga'}]
        with patch.object(t,'_team_candidates',teams), patch.object(t,'_events_for',events):
            x=t.discover_pair('Valencia vs Barcelona',today=dt.date(2026,9,2),days=45)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['id'],'right')

    def test_targeted_team_discovers_future_fixture_before_old_results(self):
        from unittest.mock import patch
        import datetime as dt
        import backend.services.targeted_search as t
        def teams(name, timeout=6): return [('FAKE','1','FC Barcelona',{})]
        def events(source, tid, timeout=6):
            return [{'id':'old','home':'Elche','away':'FC Barcelona','date':'2026-08-31','league':'LaLiga'},
                    {'id':'new','home':'FC Barcelona','away':'Feyenoord','date':'2026-09-09','league':'Champions League'}]
        with patch.object(t,'_team_candidates',teams), patch.object(t,'_events_for',events):
            x=t.discover_team('Barcelona',today=dt.date(2026,9,2),days=45)
        self.assertTrue(x['found'])
        self.assertEqual(x['candidates'][0]['id'],'new')


class FallbackContractV616(unittest.TestCase):
    def test_server_source_contains_no_stale_fallback_policy(self):
        from pathlib import Path
        text=Path(__file__).resolve().parents[1].joinpath('backend','server.py').read_text(encoding='utf8')
        self.assertIn('No se encontró un partido actual/futuro relacionado', text)
        self.assertIn('histórico', text)

