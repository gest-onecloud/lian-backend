import shutil, tempfile, unittest, sys, sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.decision_intelligence import report
from backend.services.top import top

class V640DeepAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.model=Model(cls.r)

    def _tmp(self):
        td=Path(tempfile.mkdtemp(prefix='lian640audit_')); shutil.copy2(ROOT/'data'/'lian.db',td/'lian.db'); shutil.copy2(ROOT/'data'/'public_priors.json',td/'public_priors.json'); return td,Repo(td/'lian.db')

    def _insert_history(self,r,home,away,n=5,home_score=2,away_score=0):
        for i in range(n):
            d=f'2026-08-{10+i:02d}'
            for mid,h,a,hs,as_ in [(f'{home}-{i}',home,f'RivalH{i}',home_score,away_score),(f'{away}-{i}',f'RivalA{i}',away,0,1)]:
                r.execute("INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,data_quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (mid,d,'18:00','audit','Audit League','Americas','Mexico',h,a,hs,as_,'finished','test',1.0))

    def test_future_result_cannot_change_pre_match_prediction(self):
        td,r=self._tmp()
        try:
            self._insert_history(r,'A','B',5)
            m={'id':'future','date':'2026-09-10','home':'A','away':'B','competition':'Audit League','competition_id':'audit','status':'scheduled'}
            before=Model(r).predict(m)['probabilities']
            r.execute("INSERT INTO matches(id,date,competition_id,competition,region,country,home,away,home_score,away_score,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      ('future-result','2026-09-11','audit','Audit League','Americas','Mexico','A','B',9,0,'finished'))
            after=Model(r).predict(m)['probabilities']
            for k in ('1','X','2'): self.assertAlmostEqual(before[k],after[k],places=10)
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_zero_data_is_not_a_selection_even_with_verified_venue(self):
        a={'id':'z1','date':'2026-09-10','home':'Unknown A','away':'Unknown B','competition':'Audit League','competition_id':'audit','status':'scheduled'}
        b=dict(a); b['id']='z2';
        pa=self.model.predict(a); pb=self.model.predict(b)
        self.assertFalse(pa['selection_eligible']); self.assertEqual(pa['decision'],'PASS'); self.assertEqual(pa['data_sufficiency']['mode'],'LEAGUE_BASELINE_ONLY')
        self.assertAlmostEqual(pa['expected_goals']['home'],pb['expected_goals']['home'],places=10)

    def test_minimum_history_unlocks_prediction_gate(self):
        td,r=self._tmp()
        try:
            self._insert_history(r,'A','B',4)
            m={'id':'known','date':'2026-09-10','home':'A','away':'B','competition':'Audit League','competition_id':'audit','status':'scheduled'}
            p=Model(r).predict(m); self.assertTrue(p['selection_eligible']); self.assertEqual(p['data_sufficiency']['mode'],'TEAM_DATA')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_below_minimum_history_stays_gated(self):
        td,r=self._tmp()
        try:
            self._insert_history(r,'A','B',3)
            m={'id':'known3','date':'2026-09-10','home':'A','away':'B','competition':'Audit League','competition_id':'audit','status':'scheduled'}
            p=Model(r).predict(m); self.assertFalse(p['selection_eligible']); self.assertEqual(p['decision'],'PASS')
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_team_data_has_directional_effect(self):
        td,r=self._tmp()
        try:
            self._insert_history(r,'Strong','Weak',4,3,0)
            m={'id':'direction','date':'2026-09-10','home':'Strong','away':'Weak','competition':'Audit League','competition_id':'audit','status':'scheduled'}
            p=Model(r).predict(m)
            self.assertGreater(p['probabilities']['1'],p['probabilities']['2'])
            self.assertTrue(any(x['factor']=='Producción ajustada' for x in p['signals']))
        finally: shutil.rmtree(td,ignore_errors=True)

    def test_probabilities_are_finite_and_normalized_for_all_current_fixtures(self):
        rows=self.r.rows("SELECT * FROM matches WHERE status IN ('scheduled','finished')")
        self.assertGreater(len(rows),0)
        for m in rows:
            p=self.model.predict(m)['probabilities']; self.assertAlmostEqual(sum(p.values()),1.0,places=7); self.assertTrue(all(0<=v<=1 for v in p.values()))

    def test_gated_matches_never_enter_top_picks(self):
        rows=top(self.r,'2026-09-03')
        self.assertTrue(all(x.get('selection_eligible') for x in rows))

    def test_explainability_reports_gate_not_fake_favorite(self):
        m={'id':'gate','date':'2026-09-10','home':'Unknown A','away':'Unknown B','competition':'Audit League','competition_id':'audit','status':'scheduled'}
        p=self.model.predict(m); e=report(p,m); self.assertEqual(e['status'],'DATOS INSUFICIENTES'); self.assertIsNone(e['favorite'])

    def test_platform_and_model_versions_are_current(self):
        self.assertEqual(self.model.VERSION,'64.0.0'); self.assertEqual(self.model.BASE_MODEL_VERSION,'63.0.0')
        self.assertIn("VERSION='64.6.0'",(ROOT/'backend/server.py').read_text())

if __name__=='__main__': unittest.main()
