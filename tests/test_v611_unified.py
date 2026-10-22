import ast, sqlite3, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V611Unified(unittest.TestCase):
 def test_universal_syntax(self): ast.parse((ROOT/'backend/services/universal.py').read_text(encoding='utf8'))
 def test_server_unified_routes(self):
  s=(ROOT/'backend/server.py').read_text(encoding='utf8')
  for x in ('/api/universal-match','/api/data-health','/api/prediction-timeline'): self.assertIn(x,s)
 def test_database_intact(self):
  c=sqlite3.connect(ROOT/'data'/'lian.db'); self.assertGreater(c.execute('select count(*) from matches').fetchone()[0],0); c.close()
 def test_required_modules(self):
  for p in ['backend/core/model.py','backend/learning/adaptive_engine.py','backend/services/catchup.py','frontend/app.js']: self.assertTrue((ROOT/p).exists(),p)
if __name__=='__main__': unittest.main()
