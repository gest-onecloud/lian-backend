import datetime as dt
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from backend.services.match_lifecycle import lifecycle
import backend.services.targeted_search as ts

MX=ZoneInfo("America/Mexico_City")

class LifecycleV621(unittest.TestCase):
    def test_past_scheduled_never_next(self):
        x=lifecycle({"date":"2026-08-27","status":"scheduled","home":"Barcelona","away":"Athletic Club"}, dt.datetime(2026,9,3,tzinfo=MX))
        self.assertEqual(x["label"],"RESULTADO PENDIENTE")
        self.assertNotEqual(x["label"],"PRÓXIMO")
    def test_past_with_score_is_finished(self):
        x=lifecycle({"date":"2026-08-27","status":"scheduled","home_score":2,"away_score":1}, dt.datetime(2026,9,3,tzinfo=MX))
        self.assertEqual(x["label"],"FINALIZADO"); self.assertEqual(x["result"],"2–1")
    def test_future_is_next(self):
        x=lifecycle({"date":"2026-09-06","status":"scheduled"}, dt.datetime(2026,9,3,tzinfo=MX))
        self.assertEqual(x["label"],"PRÓXIMO")

class SearchIdentityV621(unittest.TestCase):
    def test_team_suffix_equivalence(self):
        self.assertTrue(ts.team_eq("Cruz Azul FC","Cruz Azul"))
        self.assertTrue(ts.team_eq("FC Barcelona","Barcelona"))
        self.assertFalse(ts.team_eq("Barcelona SC","Barcelona"))

    def test_pair_requires_both_sides(self):
        events=[{"home":"Elche","away":"Barcelona","date":"2026-09-04"},{"home":"Cruz Azul FC","away":"Santos Laguna","date":"2026-09-06"}]
        with patch.object(ts,'_calendar_events_range',return_value=(events,[{"source":"TEST","ok":True}])):
            with patch.object(ts,'_espn_league_range',return_value=([],{"source":"TEST","ok":True,"records":0,"url":""})):
                x=ts.discover_calendar("Cruz Azul vs Santos",today=dt.date(2026,9,3),days=7,timeout=1)
        self.assertTrue(x["found"]); self.assertEqual(x["candidates"][0]["home"],"Cruz Azul FC")

if __name__=="__main__":unittest.main()

class SearchTeamV621(unittest.TestCase):
    def test_discover_team_accepts_safe_team_descriptor(self):
        events=[{'id':'x','home':'Cruz Azul FC','away':'Santos Laguna','date':'2026-09-06','league':'Liga MX'}]
        with patch.object(ts,'_team_candidates',return_value=[('TEST','1','Cruz Azul',{})]), \
             patch.object(ts,'_events_for',return_value=events):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,3),days=10,timeout=1)
        self.assertTrue(x['found']); self.assertEqual(x['candidates'][0]['away'],'Santos Laguna')
