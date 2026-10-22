from __future__ import annotations
import datetime as dt, json
from .source_manager import SourceManager
from .results_sync import ResultsSync
from ..learning.adaptive_calibration import AdaptiveCalibration
from ..services.fixture_sync import FixtureSync
from ..services.timezone import MX

class CatchUpEngine:
    VERSION='63.0.0'
    def __init__(self,repo): self.r=repo; self._schema()
    def _schema(self):
        self.r.execute('''CREATE TABLE IF NOT EXISTS engine_state(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS catchup_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started_at TEXT,ended_at TEXT,last_sync TEXT,gap_minutes INTEGER,days INTEGER,status TEXT,report TEXT)''')
    def get(self,key,default=''):
        x=self.r.one('SELECT value FROM engine_state WHERE key=?',(key,)); return x['value'] if x else default
    def set(self,key,value): self.r.execute('INSERT OR REPLACE INTO engine_state(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)',(key,str(value)))
    def run(self,now=None,max_days=90):
        now=now or dt.datetime.now(MX)
        last=self.get('last_successful_sync','')
        if last:
            try: last_dt=dt.datetime.fromisoformat(last).astimezone(MX)
            except Exception: last_dt=now-dt.timedelta(days=1)
        else: last_dt=now-dt.timedelta(days=1)
        gap=max(0,int((now-last_dt).total_seconds()/60))
        start=last_dt.date()+dt.timedelta(days=1); end=now.date()
        days=max(0,(end-start).days+1)
        days=min(days,max_days)
        if days==0:
            self.set('last_successful_sync',now.isoformat()); return {'status':'up_to_date','gap_minutes':gap,'days':0}
        run_id=None; started=dt.datetime.now(dt.timezone.utc).isoformat(); reports=[]
        try:
            fx=FixtureSync(self.r)
            for i in range(days):
                d=(start+dt.timedelta(days=i)).isoformat()
                try: fx.bootstrap_seed()
                except Exception: pass
                try:
                    fr=fx.sync_day_cached(d,force=False)
                    local=self.r.rows('SELECT * FROM matches WHERE date=?',(d,))
                    fusion=SourceManager(self.r).collect(d,local_records=local)
                    rs=ResultsSync(self.r).sync(d)
                    reports.append({'date':d,'fixtures':fr,'source_fusion':fusion,'results':rs})
                except Exception as ex: reports.append({'date':d,'catchup_error':str(ex)})
            try: AdaptiveCalibration(self.r).run()
            except Exception as ex: reports.append({'learning_error':str(ex)})
            self.set('last_successful_sync',now.isoformat())
            status='complete'
        except Exception as ex:
            status='partial'; reports.append({'fatal':str(ex)})
        ended=dt.datetime.now(dt.timezone.utc).isoformat()
        self.r.execute('INSERT INTO catchup_runs(started_at,ended_at,last_sync,gap_minutes,days,status,report) VALUES(?,?,?,?,?,?,?)',(started,ended,last,gap,days,status,json.dumps(reports,ensure_ascii=False)))
        return {'status':status,'gap_minutes':gap,'days':days,'from':start.isoformat(),'to':end.isoformat(),'reports':reports}
