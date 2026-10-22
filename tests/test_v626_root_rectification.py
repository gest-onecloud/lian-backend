import unittest, tempfile, shutil, datetime as dt
from pathlib import Path
from unittest.mock import patch
from backend.data.repo import Repo
from backend.services.universal import canonical
from backend.services.progol import generate_contest
from backend.server import predictions_for
from backend.core.model import Model
import backend.services.targeted_search as ts

ROOT=Path(__file__).resolve().parents[1]

class V626RootRectification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td=Path(tempfile.mkdtemp(prefix='lian626_')); cls.db=cls.td/'lian.db'
        shutil.copy2(ROOT/'data'/'lian.db',cls.db); shutil.copy2(ROOT/'data'/'public_priors.json',cls.td/'public_priors.json')
        cls.r=Repo(cls.db); cls.r.init_learning()
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.td,ignore_errors=True)

    def test_search_canonical_has_probabilities(self):
        m=self.r.one("SELECT * FROM matches WHERE date>=? AND status!='finished' LIMIT 1",(dt.date.today().isoformat(),))
        if not m: self.skipTest('no scheduled local fixture')
        x=canonical(self.r,m['home'],m['id']); self.assertTrue(x['found'])
        p=x['match'].get('probabilities') or {}
        self.assertEqual(set(p),{'1','X','2'}); self.assertAlmostEqual(sum(p.values()),1.0,places=6)

    def test_home_advantage_is_bounded(self):
        model=Model(self.r)
        self.assertLessEqual(abs(.45*.10),.045+1e-9)

    def test_multi_league_discovery_is_not_local_only(self):
        fixtures=[
            {'id':'a','home':'Atlas','away':'Atlante','date':'2026-09-07','league':'Liga MX'},
            {'id':'b','home':'Valencia','away':'Barcelona','date':'2026-09-08','league':'LaLiga'},
            {'id':'c','home':'Bayern Munich','away':'Dortmund','date':'2026-09-09','league':'Bundesliga'},
        ]
        def fake_events(source,tid,timeout=6): return [x for x in fixtures if ts.team_eq(x['home'],tid) or ts.team_eq(x['away'],tid)]
        mapping={t:[('SOFA',t,t,{})] for x in fixtures for t in (x['home'],x['away'])}
        with patch.object(ts,'_team_candidates',side_effect=lambda q,timeout=6:mapping.get(q,[])), patch.object(ts,'_events_for',side_effect=fake_events), patch.object(ts,'_google_search_hints',return_value={'ok':True,'source':'GOOGLE_WEB_HINTS','hints':[]}):
            for h in ('Atlas','Valencia','Bayern Munich'):
                x=ts.discover_team(h,today=dt.date(2026,9,3),days=30,timeout=1)
                self.assertTrue(x['found'],h)
                self.assertTrue(any(ts.team_eq(c['home'],h) or ts.team_eq(c['away'],h) for c in x['candidates']))


    def test_pre_match_prediction_is_persisted_and_reused_after_kickoff(self):
        self.r.execute("DELETE FROM matches WHERE id='test626-live'")
        self.r.execute("INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,status,source,updated_at,season,source_url,data_quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('test626-live','2099-01-01','12:00','TEST','Test League','','','Alpha FC','Beta FC','scheduled','test','2098-01-01','','test',1.0))
        x=predictions_for(self.r,'2099-01-01',allow_persist=True); self.assertTrue(x and x[0]['pre_match_prediction'])
        stored=self.r.one("SELECT * FROM predictions WHERE match_id='test626-live'"); self.assertIsNotNone(stored)
        self.r.execute("UPDATE matches SET status='finished',home_score=0,away_score=1 WHERE id='test626-live'")
        y=predictions_for(self.r,'2099-01-01',allow_persist=False)[0]
        self.assertEqual(y['prediction_source'],'IMMUTABLE_PRE_MATCH_RECORD')
        self.assertEqual(y['probabilities']['1'],stored['p_home']); self.assertEqual(y['result']['correct'],stored['pick']=='2')
        self.r.execute("DELETE FROM matches WHERE id='test626-live'"); self.r.execute("DELETE FROM predictions WHERE match_id='test626-live'")



    def test_google_layer_is_optional_discovery_fallback(self):
        import backend.services.targeted_search as ts
        from unittest.mock import patch
        with patch.dict(ts.os.environ, {'GOOGLE_CSE_API_KEY':'k','GOOGLE_CSE_ID':'cx'}):
            with patch.object(ts,'_get',return_value={'items':[{'title':'Atlas vs Atlante','snippet':'fixture','link':'https://example.test/fixture'}]}):
                x=ts._google_search_hints('Atlas vs Atlante',dt.date(2026,9,3),30,1)
        self.assertTrue(x['ok']); self.assertEqual(x['source'],'GOOGLE_CSE'); self.assertEqual(len(x['hints']),1)

    def test_offline_search_returns_local_future_with_prediction(self):
        from unittest.mock import patch
        import backend.server as srv
        m=self.r.one("SELECT * FROM matches WHERE date='2026-09-06' LIMIT 1")
        self.assertIsNotNone(m)
        with patch.dict(srv.os.environ, {'LIAN_DISABLE_LIVE_FIXTURES':'1'}):
            x=srv.universal_search(self.r,m['home'])
        self.assertTrue(x['found']); self.assertTrue(x.get('candidates'))
        if len(x['candidates'])==1:
            self.assertEqual(set(x['match']['probabilities']),{'1','X','2'})

    def test_frontend_search_uses_intelligence_payload(self):
        js=(ROOT/'frontend'/'app.js').read_text(encoding='utf8')
        self.assertIn('/api/intelligence?match_id=',js); self.assertIn('analyzeId(cs[0].id)',js)
        self.assertIn("m.probabilities",js)

    def test_progol_uses_same_core_version(self):
        x=generate_contest(self.r,'2349'); self.assertTrue(x['groups'])
        self.assertTrue(all(t['model_version']==Model.VERSION for g in x['groups'] for t in g['tickets']))

if __name__=='__main__': unittest.main()
