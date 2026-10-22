import ast, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V612DynamicDate(unittest.TestCase):
 def test_dynamic_date_modules_parse(self):
  for p in ['backend/services/calendar_clock.py','backend/services/intel.py','backend/services/fixture_sync.py','backend/services/background.py','backend/server.py']: ast.parse((ROOT/p).read_text(encoding='utf8'))
 def test_no_hardcoded_august_in_search_logic(self):
  s=(ROOT/'backend/services/intel.py').read_text(encoding='utf8'); self.assertNotIn('2026-08',s); self.assertNotIn('08-',s)
 def test_search_has_mx_today_priority_and_refresh(self):
  s=(ROOT/'backend/server.py').read_text(encoding='utf8'); self.assertIn('today_mx',s); self.assertIn('sync_window_cached',s)
 def test_background_uses_mexico_date(self): self.assertIn('mexico_today_iso',(ROOT/'backend/services/background.py').read_text(encoding='utf8'))
if __name__=='__main__': unittest.main()
