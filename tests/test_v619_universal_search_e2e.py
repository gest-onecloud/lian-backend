import os
import unittest
from unittest.mock import patch

import backend.server as server

class _Repo:
    def __init__(self):
        self.rows_data=[
            {'id':'old','home':'Elche CF','away':'FC Barcelona','competition':'LaLiga','date':'2026-08-23','status':'finished','home_score':1,'away_score':0}
        ]
    def rows(self,sql,args=()):
        if 'FROM matches' in sql:return list(self.rows_data)
        return []
    def one(self,sql,args=()):
        if 'FROM matches WHERE id=' in sql:
            return next((x for x in self.rows_data if x['id']==args[0]),None)
        return None
    def execute(self,*a,**k): return None

class UniversalSearchE2EV619(unittest.TestCase):
    def setUp(self): self.env=patch.dict(os.environ,{'LIAN_DISABLE_LIVE_FIXTURES':'0'}); self.env.start()
    def tearDown(self): self.env.stop()

    def test_single_team_never_returns_august_when_live_discovery_raises(self):
        repo=_Repo()
        with patch.object(server,'FixtureSync',lambda repo: type('S',(),{'sync_window_cached':lambda self,*a,**k:{}})()), \
             patch.object(server,'canonical',return_value={'found':True,'match':repo.rows_data[0],'candidates':repo.rows_data}), \
             patch('backend.services.targeted_search.discover_calendar',side_effect=RuntimeError('provider failure')), \
             patch('backend.services.targeted_search.discover_team',side_effect=RuntimeError('provider failure')):
            x=server.universal_search(repo,'Barcelona')
        self.assertFalse(x['found'])
        self.assertEqual(x['historical_candidates'][0]['date'],'2026-08-23')

    def test_pair_does_not_fall_back_to_unrelated_or_historical_match(self):
        repo=_Repo()
        with patch.object(server,'FixtureSync',lambda repo: type('S',(),{'sync_window_cached':lambda self,*a,**k:{}})()), \
             patch.object(server,'canonical',return_value={'found':False,'query':'Valencia vs Barcelona','candidates':[]}), \
             patch('backend.services.targeted_search.discover_calendar',return_value={'found':False,'candidates':[],'sources':{}}), \
             patch('backend.services.targeted_search.discover_pair',return_value={'found':False,'candidates':[],'sources':{}}):
            x=server.universal_search(repo,'Valencia vs Barcelona')
        self.assertFalse(x['found'])

if __name__=='__main__': unittest.main()
