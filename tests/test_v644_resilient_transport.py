import json, shutil, tempfile, unittest, os
from pathlib import Path
from unittest.mock import patch
from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
import backend.services.fixture_sync as fs
from backend.services import http_client

ROOT=Path(__file__).resolve().parents[1]

class Resp:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.payload).encode()

class V644ResilientTransport(unittest.TestCase):
    def test_requests_is_used_when_urllib_fails(self):
        with patch.dict(os.environ, {'LIAN_TEST_MODE':'0'}), patch('backend.services.http_client._urllib_json',side_effect=OSError('urllib down')), \
             patch('backend.services.http_client._requests_json',return_value={'events':[1]}) as req:
            out=http_client.get_json('https://api.sofascore.com/api/v1/test',timeout=1)
        self.assertEqual(out,{'events':[1]}); self.assertTrue(req.called)

    def test_curl_is_last_resort_when_both_python_transports_fail(self):
        with patch.dict(os.environ, {'LIAN_TEST_MODE':'0'}), patch('backend.services.http_client._urllib_json',side_effect=OSError('urllib down')), \
             patch('backend.services.http_client._requests_json',side_effect=OSError('requests down')), \
             patch('backend.services.http_client._curl_json',return_value={'events':[2]}) as curl:
            out=http_client.get_json('https://api.espn.com/test',timeout=1)
        self.assertEqual(out,{'events':[2]}); self.assertTrue(curl.called)

    def test_total_broad_outage_does_not_fan_out_to_fourteen_leagues(self):
        td=Path(tempfile.mkdtemp(prefix='lian644_'))
        try:
            shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); r=Repo(td/'lian.db'); r.init_learning(); fx=FixtureSync(r)
            with patch.object(fx,'fetch_espn_all',side_effect=OSError('down')), \
                 patch.object(fx,'fetch_sofascore_day',side_effect=OSError('down')), \
                 patch.object(fx,'fetch_fotmob_day',side_effect=OSError('down')), \
                 patch.object(fx,'fetch_thesportsdb',return_value=([], 'tsdb')), \
                 patch.object(fx,'fetch_espn',side_effect=AssertionError('blind league fan-out')):
                x=fx.sync_day_light('2026-09-04')
            self.assertEqual(x['coverage_status'],'incomplete')
        finally: shutil.rmtree(td,ignore_errors=True)

if __name__=='__main__': unittest.main()
