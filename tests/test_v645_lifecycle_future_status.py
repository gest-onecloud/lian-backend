import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from backend.services.match_lifecycle import lifecycle

MX = ZoneInfo("America/Mexico_City")

class LifecycleV645(unittest.TestCase):
    def test_future_finished_status_is_next(self):
        x = lifecycle({"date":"2026-09-10","status":"finished","home":"Bayern Munich","away":"Bodo/Glimt"},
                       dt.datetime(2026,9,4,20,0,tzinfo=MX))
        self.assertEqual(x["label"], "PRÓXIMO")
        self.assertEqual(x["code"], "scheduled")
        self.assertFalse(x["has_verified_score"])

    def test_future_final_with_stale_score_is_next(self):
        x = lifecycle({"date":"2026-09-13","status":"final","home_score":0,"away_score":0,
                       "home":"SV Elversberg","away":"Bayern Munich"},
                       dt.datetime(2026,9,4,20,0,tzinfo=MX))
        self.assertEqual(x["label"], "PRÓXIMO")
        self.assertEqual(x["code"], "scheduled")

    def test_today_verified_score_is_finished(self):
        x = lifecycle({"date":"2026-09-04","status":"scheduled","home_score":2,"away_score":1},
                       dt.datetime(2026,9,4,20,0,tzinfo=MX))
        self.assertEqual(x["label"], "FINALIZADO")
        self.assertEqual(x["code"], "finished")

    def test_past_finished_status_remains_finished(self):
        x = lifecycle({"date":"2026-09-03","status":"finished"},
                       dt.datetime(2026,9,4,20,0,tzinfo=MX))
        self.assertEqual(x["label"], "FINALIZADO")
        self.assertEqual(x["code"], "finished")

if __name__ == "__main__":
    unittest.main()
