import ast, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class V5594Regression(unittest.TestCase):
    def test_all_python_files_parse(self):
        for p in ROOT.rglob('*.py'):
            if '__pycache__' in p.parts: continue
            ast.parse(p.read_text(encoding='utf8'))
    def test_runtime_versions_are_synchronized(self):
        v=(ROOT/'VERSION.txt').read_text(encoding='utf8').strip()
        self.assertIn(v,{'62.6.0','63.0.0','63.1.0','63.2.0','64.0.0','64.1.0','64.2.0','64.6.0'})
        checks={
          'backend/server.py':f"VERSION='{v}'",
          'backend/core/model.py':"VERSION='63.0.0'",
          'backend/learning/live_context.py':"VERSION='63.0.0'",
          'frontend/app.js':f"LIAN_VERSION='{v}'",
          'frontend/index.html':f'V{v}',
        }
        for rel,token in checks.items(): self.assertIn(token,(ROOT/rel).read_text(encoding='utf8'))
    def test_no_stale_runtime_version(self):
        runtime=['backend','frontend','*.bat','VERSION.txt']
        for rel in ['backend/server.py','backend/core/model.py','backend/learning/live_context.py','backend/services/progol.py','backend/services/results_sync.py','backend/services/fixture_sync.py','frontend/app.js','frontend/index.html','VALIDAR_TODO.bat','VERIFICAR_PAQUETE.bat','LAUNCHER_LIAN.bat']:
            self.assertNotIn('55.9.3',(ROOT/rel).read_text(encoding='utf8'),rel)
if __name__=='__main__': unittest.main()
