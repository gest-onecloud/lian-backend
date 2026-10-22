import unittest,datetime as dt,os,sys,subprocess,time,json,urllib.request
from pathlib import Path
from backend.data.repo import Repo
from backend.services.professional_audit import ProfessionalAudit
from backend.services.calendar import raw_matches

ROOT=Path(__file__).resolve().parents[1]

class ProfessionalHardeningTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.r.init_learning()
 def test_audit_is_read_only(self):
  before=self.r.one("SELECT COUNT(*) n FROM matches")['n']; x=ProfessionalAudit(self.r).report(); after=self.r.one("SELECT COUNT(*) n FROM matches")['n']; self.assertEqual(before,after); self.assertIn('probability_calibration_status',x['checks'])
 def test_historical_raw_calendar_does_not_predict(self):
  rows=raw_matches(self.r,'2026-08-25'); self.assertGreaterEqual(len(rows),20); self.assertTrue(all(x['date']=='2026-08-25' for x in rows))

 def test_http_historical_navigation_uses_selected_date(self):
  port='8097'; env=os.environ.copy(); env['LIAN_PORT']=port; env['LIAN_DISABLE_LIVE_FIXTURES']='1'; env['LIAN_DISABLE_LIVE_RESULTS']='1'
  p=subprocess.Popen([sys.executable,'-m','backend.server'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(30):
    try: urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1); break
    except Exception: time.sleep(.1)
   before=self.r.one("SELECT COUNT(*) n FROM predictions")['n']
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/calendar?date=2026-08-25&refresh=1',timeout=5) as r: x=json.loads(r.read())
   after=self.r.one("SELECT COUNT(*) n FROM predictions")['n']
   self.assertEqual(x['date'],'2026-08-25'); self.assertGreaterEqual(len(x['matches']),20); self.assertEqual(before,after); self.assertTrue(all(m['date']=='2026-08-25' for m in x['matches']))
  finally:
   if p.poll() is None:
    if os.name=='nt': subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else: p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
     p.kill(); p.wait(timeout=5)

 def test_version(self): self.assertIn((ROOT/'VERSION.txt').read_text().strip(),{'62.6.0','63.0.0','63.1.0','64.0.0','64.1.0','64.2.0','64.0.0','64.1.0','64.2.0','64.6.0'})
if __name__=='__main__': unittest.main()
