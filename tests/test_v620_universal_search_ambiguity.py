import datetime as dt
import os
import unittest
from unittest.mock import patch

import backend.server as server

class _Repo:
    def __init__(self):
        self.rows_data=[
            {"id":"old1","date":"2026-08-23","home":"Elche","away":"Barcelona","competition":"LaLiga","status":"finished"},
            {"id":"old2","date":"2026-08-27","home":"Barcelona","away":"Athletic Club","competition":"LaLiga","status":"finished"},
        ]
    def rows(self,sql,args=()):
        if "FROM matches" in sql:return list(self.rows_data)
        return []
    def one(self,sql,args=()):
        if "FROM matches WHERE id=" in sql:return next((x for x in self.rows_data if x["id"]==args[0]),None)
        return None
    def execute(self,*a,**k):return None

class UniversalSearchAmbiguityV620(unittest.TestCase):
    def test_ambiguous_historical_team_still_runs_live_discovery(self):
        calls=[]; repo=_Repo()
        def fake_calendar(q,*args,**kw):
            calls.append(("calendar",q)); return {"found":True,"candidates":[{"id":"new","date":"2026-09-06","home":"Valencia CF","away":"FC Barcelona","competition":"LaLiga","status":"scheduled","source":"TEST"}],"sources":{}}
        with patch.dict(os.environ,{"LIAN_DISABLE_LIVE_FIXTURES":"0"}), \
             patch.object(server,"FixtureSync",lambda repo:type("S",(),{"sync_window_cached":lambda self,*a,**k:{},"_upsert":lambda self,*a,**k:None})()), \
             patch.object(server,"canonical",side_effect=[{"found":True,"ambiguous":True,"candidates":repo.rows_data},{"found":True,"ambiguous":False,"match":{"id":"new","date":"2026-09-06","home":"Valencia CF","away":"FC Barcelona"},"candidates":[]}]), \
             patch("backend.services.targeted_search.discover_calendar",fake_calendar), \
             patch("backend.services.targeted_search.discover_team",fake_calendar):
            x=server.universal_search(repo,"Barcelona")
        self.assertTrue(calls)
        self.assertTrue(x["found"])
        self.assertEqual(x["match"]["id"],"new")

    def test_pair_with_stale_local_rows_runs_discovery(self):
        repo=_Repo(); calls=[]
        with patch.dict(os.environ,{"LIAN_DISABLE_LIVE_FIXTURES":"0"}), \
             patch.object(server,"FixtureSync",lambda repo:type("S",(),{"sync_window_cached":lambda self,*a,**k:{},"_upsert":lambda self,*a,**k:None})()), \
             patch.object(server,"canonical",side_effect=[{"found":False,"ambiguous":False,"candidates":repo.rows_data},{"found":True,"ambiguous":False,"match":{"id":"vb","date":"2026-09-06","home":"Valencia CF","away":"FC Barcelona"},"candidates":[]}]), \
             patch("backend.services.targeted_search.discover_calendar",lambda q,*args,**kw:(calls.append(q) or {"found":True,"candidates":[{"id":"vb","date":"2026-09-06","home":"Valencia CF","away":"FC Barcelona","competition":"LaLiga","status":"scheduled","source":"TEST"}],"sources":{}})), \
             patch("backend.services.targeted_search.discover_pair",lambda q,*args,**kw:{"found":True,"candidates":[{"id":"vb","date":"2026-09-06","home":"Valencia CF","away":"FC Barcelona","competition":"LaLiga","status":"scheduled","source":"TEST"}],"sources":{}}):
            x=server.universal_search(repo,"Valencia vs Barcelona")
        self.assertEqual(calls,["Valencia vs Barcelona"])
        self.assertTrue(x["found"])

    def test_pair_never_becomes_ambiguous_from_unrelated_local_rows(self):
        from backend.services.universal import resolve
        class R:
            def rows(self,q):return [
                {"id":"a","date":"2026-08-23","home":"Elche","away":"Barcelona","competition":"LaLiga","status":"finished"},
                {"id":"b","date":"2026-08-27","home":"Barcelona","away":"Athletic Club","competition":"LaLiga","status":"finished"},
            ]
        self.assertEqual(resolve(R(),"Valencia vs Barcelona"),[])

    def test_needs_discovery_for_ambiguous_stale_team(self):
        self.assertTrue(server.needs_targeted_discovery("Barcelona",{"found":False,"ambiguous":True,"candidates":[{"date":"2026-08-27"}]},dt.date(2026,9,2)))

if __name__=="__main__":unittest.main()
