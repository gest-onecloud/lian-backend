import os,sys,time,json,urllib.request,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HttpSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port='8099'; env=os.environ.copy(); env['LIAN_PORT']=cls.port; env['LIAN_DISABLE_LIVE_FIXTURES']='1'; env['LIAN_DISABLE_LIVE_RESULTS']='1'
        cls.p=subprocess.Popen([sys.executable,'-m','backend.server'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(30):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{cls.port}/api/health',timeout=1); break
            except Exception: time.sleep(.1)
        else: raise RuntimeError('API did not start')
    @classmethod
    def tearDownClass(cls):
        if cls.p.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill','/PID',str(cls.p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                cls.p.terminate()
            try: cls.p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.p.kill(); cls.p.wait(timeout=5)
    def get(self,path):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/{path}',timeout=10) as r:
            return r.status,r.headers.get('Content-Type',''),r.read()
    def test_health(self):
        s,ct,b=self.get('api/health'); self.assertEqual(s,200); self.assertIn('json',ct)
    def test_calendar(self):
        s,ct,b=self.get('api/calendar?date=2026-08-25'); x=json.loads(b); self.assertEqual(s,200); self.assertEqual(len(x['matches']),23)
    def test_calendar_27(self):
        s,_,b=self.get('api/calendar?date=2026-08-27'); x=json.loads(b); self.assertEqual(s,200); self.assertEqual(x['date'],'2026-08-27'); self.assertGreaterEqual(len(x['matches']),40); self.assertTrue(all(m['date']=='2026-08-27' for m in x['matches']))

    def test_modules(self):
        for path in ['api/top-picks?date=2026-08-25','api/combinations?date=2026-08-25','api/progol?date=2026-08-25','api/learning']:
            s,_,b=self.get(path); self.assertEqual(s,200); self.assertTrue(json.loads(b))
    def test_progol_contest_sections(self):
        for cid, expected in [('2348',[(14,20),(7,20)]),('810',[(9,20)])]:
            s,_,b=self.get(f'api/progol?contest={cid}'); x=json.loads(b); self.assertEqual(s,200); self.assertEqual([(g['count'],len(g['tickets'])) for g in x['groups']],expected)

    def test_new_v541_endpoints(self):
        for path in ['api/data-status','api/feature-snapshot?match_id=cal-2026-08-25-es-laliga-valencia-real-betis','api/explain?match_id=cal-2026-08-25-es-laliga-valencia-real-betis']:
            s,_,b=self.get(path); self.assertEqual(s,200); self.assertTrue(json.loads(b))
    def test_intelligence(self):
        s,_,b=self.get('api/intelligence?q=Valencia%20vs%20Real%20Betis'); x=json.loads(b); self.assertEqual(s,200); self.assertTrue(x['found']); self.assertIn('probabilities',x['match'])
    def test_static(self):
        for path in ['','style.css','app.js']:
            s,ct,b=self.get(path); self.assertEqual(s,200); self.assertGreater(len(b),100)
if __name__=='__main__': unittest.main()
