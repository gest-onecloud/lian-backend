import os, subprocess, sys, time, urllib.request, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V641APIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env=os.environ.copy(); env['LIAN_DISABLE_LIVE_FIXTURES']='1'; env['LIAN_DISABLE_LIVE_RESULTS']='1'; env['LIAN_PORT']='8121'
        cls.p=subprocess.Popen([sys.executable,'-m','backend.server'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                urllib.request.urlopen('http://127.0.0.1:8121/api/health',timeout=0.3); break
            except Exception: time.sleep(.1)
    @classmethod
    def tearDownClass(cls):
        cls.p.terminate(); cls.p.wait(timeout=5)
    def get(self,path):
        with urllib.request.urlopen('http://127.0.0.1:8121'+path,timeout=3) as r:return json.loads(r.read())
    def test_health_platform_model_versions(self):
        x=self.get('/api/health'); self.assertEqual(x['version'],'64.6.0'); self.assertEqual(x['model_version'],'64.0.0')
    def test_calendar_window_is_exactly_thirty_dates(self):
        x=self.get('/api/calendar-window'); self.assertEqual(len(x['days']),30); self.assertEqual(x['window_days'],30); self.assertEqual(x['days'][0]['date'],x['start']); self.assertEqual(x['days'][-1]['date'],x['end'])
    def test_canonical_duplicate_is_not_returned_twice_in_local_window(self):
        x=self.get('/api/universal-match?q=Cruz%20Azul'); cs=x.get('candidates') or []
        keys={(c.get('date'),c.get('home'),c.get('away')) for c in cs}
        self.assertEqual(len(keys),len(cs))
if __name__=='__main__': unittest.main()
