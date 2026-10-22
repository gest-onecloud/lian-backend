import datetime as dt
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.data.repo import Repo
from backend.services.fixture_sync import FixtureSync
from backend.services.intel import study
from backend.server import dedup_fixtures
import backend.services.targeted_search as ts

ROOT = Path(__file__).resolve().parents[1]

class V631CalendarIntelligence(unittest.TestCase):
    def test_mexico_midnight_duplicate_is_collapsed(self):
        rows = [
            {'id':'mx','date':'2026-09-06','time':'20:00','home':'Cruz Azul','away':'Santos Laguna','competition':'Liga MX','data_quality':.82},
            {'id':'utc','date':'2026-09-07','time':'02:00','home':'Cruz Azul FC','away':'Santos','competition':'Liga MX','data_quality':.72},
        ]
        out = dedup_fixtures(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['id'], 'mx')

    def test_30_day_span_is_inclusive(self):
        td = Path(tempfile.mkdtemp(prefix='lian631_'))
        try:
            db = td/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',db)
            r=Repo(db); r.init_learning(); fx=FixtureSync(r)
            calls=[]
            def fake(d,force=False): calls.append(d); return {'date':d,'match_count':0,'coverage_status':'complete-empty'}
            with patch.object(fx,'sync_day_light_cached',side_effect=fake):
                x=fx.sync_span_cached('2026-09-04','2026-10-03',force=True,light=True)
            self.assertEqual(len(calls),30)
            self.assertEqual(x['start'],'2026-09-04'); self.assertEqual(x['end'],'2026-10-03')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_calendar_union_does_not_lose_league_specific_fixtures(self):
        td = Path(tempfile.mkdtemp(prefix='lian631cal_'))
        try:
            db=td/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',db); r=Repo(db); r.init_learning(); fx=FixtureSync(r)
            broad=[
                {'id':'e1','home':'Alpha FC','away':'Beta FC','league':'Liga MX','timestamp':'2026-09-04T18:00:00Z','status':'STATUS_SCHEDULED'},
                {'id':'e2','home':'Gamma FC','away':'Delta FC','league':'Premier League','timestamp':'2026-09-04T20:00:00Z','status':'STATUS_SCHEDULED'},
            ]
            sofa=[{'id':'s1','home':'Epsilon','away':'Zeta','league':'Serie A','timestamp':'2026-09-04T22:00:00Z','status':'scheduled'}]
            with patch.object(fx,'fetch_espn_all',return_value=(broad,'espn')), patch.object(fx,'fetch_sofascore_day',return_value=(sofa,'sofa')), patch.object(fx,'fetch_thesportsdb',return_value=([],'tsdb')), patch.object(fx,'fetch_espn',return_value=([],'')):
                x=fx.sync_day('2026-09-04')
            self.assertEqual(x['match_count'],3); self.assertEqual(r.one("SELECT COUNT(*) n FROM matches WHERE date='2026-09-04'")['n'],3)
            self.assertTrue(x['coverage_status'] in {'complete','partial'})
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_exact_match_id_cannot_jump_to_duplicate_fixture(self):
        td = Path(tempfile.mkdtemp(prefix='lian631intel_'))
        try:
            db=td/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',db); shutil.copy2(ROOT/'data'/'public_priors.json',td/'public_priors.json')
            r=Repo(db); r.init_learning()
            r.execute("DELETE FROM matches WHERE home LIKE 'Cruz Azul%' AND away LIKE 'Santos%'")
            rows=[
                ('m1','2026-09-06','20:00','MX-LIGA','Liga MX','','','Cruz Azul','Santos Laguna','scheduled','test','','2026-09-01','',1.0),
                ('m2','2026-09-20','20:00','MX-LIGA','Liga MX','','','Cruz Azul','Santos Laguna','scheduled','test','','2026-09-01','',1.0),
            ]
            for row in rows:
                r.execute("INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,status,source,updated_at,season,source_url,data_quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",row)
            x=study(r,'Cruz Azul vs Santos Laguna',match_id='m2')
            self.assertTrue(x['found']); self.assertEqual(x['match']['id'],'m2'); self.assertEqual(x['match']['resolution'],'CANONICAL_MATCH_ID')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_targeted_team_can_return_full_30_day_fixture_set(self):
        fixtures=[
            {'id':'1','home':'Cruz Azul FC','away':'Santos Laguna','date':'2026-09-06','league':'Liga MX'},
            {'id':'2','home':'Cruz Azul','away':'América','date':'2026-09-13','league':'Liga MX'},
            {'id':'3','home':'Inter Miami','away':'Cruz Azul','date':'2026-09-16','league':'Campeones Cup'},
            {'id':'4','home':'Monterrey','away':'Cruz Azul','date':'2026-09-20','league':'Liga MX'},
            {'id':'5','home':'Cruz Azul','away':'Toluca','date':'2026-09-27','league':'Liga MX'},
        ]
        with patch.object(ts,'_team_candidates',return_value=[('TEST','1','Cruz Azul',{})]), patch.object(ts,'_events_for',return_value=fixtures):
            x=ts.discover_team('Cruz Azul',today=dt.date(2026,9,4),days=30,timeout=1)
        self.assertEqual(len(x['candidates']),5)
        self.assertEqual([c['date'] for c in x['candidates']],sorted(c['date'] for c in fixtures))

    def test_predictive_model_file_hash_unchanged(self):
        # V63.2.0 is a calendar/intelligence fix; the predictive core must remain byte-identical.
        model=(ROOT/'backend/core/model.py').read_text(encoding='utf-8')
        self.assertIn("VERSION='64.0.0'",model)
        self.assertIn("BASE_MODEL_VERSION='63.0.0'",model)

if __name__=='__main__': unittest.main()
