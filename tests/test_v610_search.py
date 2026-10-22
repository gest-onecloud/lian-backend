import ast, sqlite3, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V610Search(unittest.TestCase):
 def test_search_module_syntax(self): ast.parse((ROOT/'backend/services/intel.py').read_text(encoding='utf8'))
 def test_search_index_contains_matches(self):
  c=sqlite3.connect(ROOT/'data'/'lian.db'); n=c.execute('select count(*) from matches').fetchone()[0]; c.close(); self.assertGreater(n,0)
 def test_search_api_tokens(self):
  s=(ROOT/'backend/server.py').read_text(encoding='utf8'); self.assertIn('/api/search',s); self.assertIn('search_matches',s)
if __name__=='__main__': unittest.main()
