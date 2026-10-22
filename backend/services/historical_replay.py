"""Historical replay/catch-up for recent fixtures and verified outcomes.

This module deliberately separates *data acquisition* from prediction. It can populate
past dates from the same free public fixture sources used by the calendar, then run the
verified-result pipeline so Post-Match and Adaptive Learning receive real outcomes.
No retrospective prediction is promoted to a pre-match prediction.
"""
from __future__ import annotations
import datetime as dt
from .fixture_sync import FixtureSync
from .results_sync import ResultsSync
from ..learning.adaptive_engine import AdaptiveLearningEngine
from ..learning.adaptive_calibration import AdaptiveCalibration
from .calendar_clock import MX

class HistoricalReplay:
    VERSION='63.0.0'
    def __init__(self, repo): self.r=repo
    def run(self, start_date, end_date, force=False):
        start=dt.date.fromisoformat(start_date); end=dt.date.fromisoformat(end_date)
        if end<start: return {'status':'empty','days':0,'reports':[]}
        fx=FixtureSync(self.r)
        reports=[]; total_fixtures=total_results=0
        for i in range((end-start).days+1):
            d=(start+dt.timedelta(days=i)).isoformat()
            try:
                fr=fx.sync_day_cached(d,force=force)
            except Exception as ex:
                fr={'date':d,'error':str(ex),'match_count':0}
            try:
                rr=ResultsSync(self.r).sync(d)
            except Exception as ex:
                rr={'date':d,'applied':0,'error':str(ex)}
            total_fixtures += int(fr.get('match_count',0) or 0)
            total_results += int(rr.get('applied',0) or 0)
            reports.append({'date':d,'fixtures':fr,'results':rr})
        repair=None; calibration=None
        try: repair=AdaptiveLearningEngine(self.r).repair_reviews()
        except Exception as ex: repair={'error':str(ex)}
        try: calibration=AdaptiveCalibration(self.r).run()
        except Exception as ex: calibration={'error':str(ex)}
        return {'status':'complete','start':start.isoformat(),'end':end.isoformat(),'days':len(reports),
                'fixtures':total_fixtures,'results_applied':total_results,'repair':repair,'calibration':calibration,
                'reports':reports}
