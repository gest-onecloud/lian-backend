from __future__ import annotations
import os,time,threading,datetime as dt, traceback,json
from ..data.repo import Repo
from .catchup import CatchUpEngine
from .source_manager import SourceManager
from .fixture_sync import FixtureSync
from .calendar_clock import mexico_today_iso
from .results_sync import ResultsSync

class BackgroundEngine:
    VERSION='63.0.0'
    def __init__(self,repo,interval=60): self.r=repo; self.interval=max(15,int(interval)); self.stop_event=threading.Event(); self.thread=None; self._schema()
    def _schema(self):
        self.r.init_learning(); self.r.execute('CREATE TABLE IF NOT EXISTS background_heartbeat(id INTEGER PRIMARY KEY CHECK(id=1),last_tick TEXT,status TEXT,message TEXT)')
    def once(self):
        now=dt.datetime.now(dt.timezone.utc).isoformat(); self.r.execute("INSERT OR REPLACE INTO background_heartbeat(id,last_tick,status,message) VALUES(1,?,?,?)",(now,'running','tick'))
        CatchUpEngine(self.r).run()
        today=mexico_today_iso()
        try:
            fx=FixtureSync(self.r)
            fx.bootstrap_seed()
            # Once per 24h, attempt a structured historical backfill. It is cached
            # so the background loop does not hammer public archives every minute.
            self.r.execute('CREATE TABLE IF NOT EXISTS historical_sync_state(id INTEGER PRIMARY KEY CHECK(id=1),last_run REAL,status TEXT,message TEXT)')
            hs=self.r.one('SELECT * FROM historical_sync_state WHERE id=1')
            if not hs or (time.time()-float(hs.get('last_run') or 0))>=86400:
                try:
                    report=__import__('backend.data.historical',fromlist=['HistoricalSync']).HistoricalSync(self.r).run()
                    self.r.execute('INSERT OR REPLACE INTO historical_sync_state(id,last_run,status,message) VALUES(1,?,?,?)',(time.time(),'ok',json.dumps({'inserted':report.get('inserted',0),'failures':len(report.get('failures',[]))})))
                except Exception as hex:
                    self.r.execute('INSERT OR REPLACE INTO historical_sync_state(id,last_run,status,message) VALUES(1,?,?,?)',(time.time(),'degraded',str(hex)))
            now_mx=dt.date.fromisoformat(today)
            # Keep a real rolling calendar, not only 'today': yesterday is needed for
            # post-match learning and the next two weeks are needed for search/picks.
            span=fx.sync_span_cached((now_mx-dt.timedelta(days=1)).isoformat(),(now_mx+dt.timedelta(days=29)).isoformat(),force=False,light=True)
            # Pre-match prediction persistence is part of the continuous data loop. Without
            # this, a match never opened in the UI could finish without a true pre-match
            # benchmark, making Adaptive Learning blind to that result.
            from ..server import predictions_for
            for j in range(0,30):
                d=(now_mx+dt.timedelta(days=j)).isoformat()
                try: predictions_for(self.r,d,allow_persist=True)
                except Exception as pex: self.r.execute("UPDATE background_heartbeat SET message=? WHERE id=1",(f'prediction-sync {d}: {pex}',))
            local=self.r.rows('SELECT * FROM matches WHERE date=?',(today,))
            SourceManager(self.r).collect(today,local_records=local)
            # Every past date is first populated as fixtures and then verified as results.
            # This fixes the old deadlock where a result could not be learned because the
            # match itself had never been inserted while the PC was off.
            for i in range(1,32):
                d=(now_mx-dt.timedelta(days=i)).isoformat()
                try:
                    rs=ResultsSync(self.r).sync(d)
                    if rs.get('applied'):
                        from ..learning.adaptive_calibration import AdaptiveCalibration
                        AdaptiveCalibration(self.r).run()
                except Exception as rex:
                    self.r.execute("UPDATE background_heartbeat SET message=? WHERE id=1",(f'result-sync {d}: {rex}',))
            self.r.execute("UPDATE background_heartbeat SET message=? WHERE id=1",(f'rolling fixtures {span.get('start')}..{span.get('end')}; recent results 31d',))
        except Exception as ex: self.r.execute("UPDATE background_heartbeat SET status='degraded',message=? WHERE id=1",(str(ex),))
        self.r.execute("UPDATE background_heartbeat SET status='idle',message=? WHERE id=1",('cycle complete',))
    def loop(self):
        while not self.stop_event.is_set():
            try:self.once()
            except Exception as ex:
                try:self.r.execute("UPDATE background_heartbeat SET status='error',message=? WHERE id=1",(str(ex),))
                except Exception: pass
            self.stop_event.wait(self.interval)
    def start(self):
        if self.thread and self.thread.is_alive(): return False
        self.stop_event.clear(); self.thread=threading.Thread(target=self.loop,name='LiAnBackground',daemon=True); self.thread.start(); return True
    def stop(self): self.stop_event.set();

def run_forever():
    root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); repo=Repo(os.path.join(root,'data','lian.db')); interval=int(os.getenv('LIAN_BACKGROUND_INTERVAL','60')); BackgroundEngine(repo,interval).loop()
