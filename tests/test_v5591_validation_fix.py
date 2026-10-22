import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ValidationFixTests(unittest.TestCase):
    def test_runtime_version_matches_manifest(self):
        v=(ROOT/'VERSION.txt').read_text(encoding='utf8').strip(); server=(ROOT/'backend/server.py').read_text(encoding='utf8'); model=(ROOT/'backend/core/model.py').read_text(encoding='utf8'); frontend=(ROOT/'frontend/app.js').read_text(encoding='utf8')
        self.assertIn(f"VERSION='{v}'",server); self.assertIn("VERSION='63.0.0'",model); self.assertIn(f"LIAN_VERSION='{v}'",frontend)
    def test_no_stale_runtime_557_tokens(self):
        for fn in ['frontend/app.js','frontend/index.html','VERIFICAR_PAQUETE.bat','LAUNCHER_LIAN.bat','VALIDAR_TODO.bat']:
            self.assertNotIn('55.7',(ROOT/fn).read_text(encoding='utf8'))
if __name__=='__main__': unittest.main()
