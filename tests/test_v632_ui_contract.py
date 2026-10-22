import hashlib, re, shutil, tempfile, unittest
from pathlib import Path
from backend.data.repo import Repo
from backend.server import predictions_for

ROOT=Path(__file__).resolve().parents[1]

class V632UIContract(unittest.TestCase):
    def test_retrospective_result_is_never_presented_as_hit_or_miss(self):
        ms=predictions_for(Repo(ROOT/'data'/'lian.db'),'2026-09-03',allow_persist=False)
        self.assertTrue(ms)
        for m in ms:
            r=m.get('result') or {}
            self.assertFalse(r.get('eligible_for_metrics'))
            self.assertEqual(r.get('evaluation_status'),'RETROSPECTIVE_DISPLAY_ONLY')

    def test_platform_and_predictive_versions_are_explicit(self):
        status=__import__('backend.data.status',fromlist=['DataStatus']).DataStatus(Repo(ROOT/'data'/'lian.db')).report()
        self.assertEqual(status['version'],'64.6.0')
        self.assertEqual(status['model_version'],'64.0.0')
        audit=__import__('backend.services.professional_audit',fromlist=['ProfessionalAudit']).ProfessionalAudit(Repo(ROOT/'data'/'lian.db')).report()
        self.assertEqual(audit['platform_version'],'64.6.0')
        self.assertEqual(audit['predictive_model_version'],'64.0.0')

    def test_static_assets_are_cache_protected(self):
        server=(ROOT/'backend'/'server.py').read_text(encoding='utf-8')
        self.assertGreaterEqual(server.count("Cache-Control"),2)
        self.assertIn('no-store, max-age=0, must-revalidate',server)

    def test_frontend_refresh_preserves_error_view(self):
        js=(ROOT/'frontend'/'app.js').read_text(encoding='utf-8')
        self.assertIn("else if(view==='errors')await loadErrors()",js)
        self.assertIn('SIN EVALUACIÓN',js)
        self.assertIn('Plataforma',js)
        self.assertIn('Motor predictivo',js)

    def test_frontend_platform_header_is_current(self):
        html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
        self.assertIn('LiAn V64.6.0',html)
        self.assertNotIn('LIAN V63.0.0',html)

    def test_predictive_core_remains_byte_identical(self):
        model=(ROOT/'backend/core/model.py').read_text(encoding='utf-8')
        self.assertIn("VERSION='64.0.0'",model)
        self.assertIn("BASE_MODEL_VERSION='63.0.0'",model)

if __name__=='__main__': unittest.main()
