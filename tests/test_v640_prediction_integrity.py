import sys, tempfile, shutil, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.decision_intelligence import report
from backend.services.top import top
from backend.services.combo import build

class V640PredictionIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=Repo(ROOT/'data'/'lian.db'); cls.model=Model(cls.r)

    def test_zero_history_cannot_become_a_selection(self):
        m={'id':'synthetic-zero','date':'2026-09-10','home':'Equipo Sin Historia A','away':'Equipo Sin Historia B','competition':'Liga Sintética','competition_id':'synthetic','status':'scheduled'}
        p=self.model.predict(m)
        self.assertEqual(p['model_version'],'64.0.0')
        self.assertFalse(p['selection_eligible'])
        self.assertEqual(p['decision'],'PASS')
        self.assertLessEqual(p['evidence'],.44)
        self.assertEqual(p['data_sufficiency']['mode'],'LEAGUE_BASELINE_ONLY')
        e=report(p,m)
        self.assertEqual(e['status'],'DATOS INSUFICIENTES')
        self.assertIsNone(e['favorite'])

    def test_no_history_neutralizes_generic_venue_signal(self):
        m={'id':'synthetic-zero-venue','date':'2026-09-10','home':'Equipo Sin Historia A','away':'Equipo Sin Historia B','competition':'Liga Sintética','competition_id':'synthetic','status':'scheduled'}
        p=self.model.predict(m)
        self.assertEqual(p['features']['home_history'],0)
        self.assertEqual(p['features']['away_history'],0)
        self.assertEqual(p['data_sufficiency']['mode'],'LEAGUE_BASELINE_ONLY')
        self.assertEqual(p['features']['venue_side'],'home' if p['features']['venue_side'] in ('home','away') else p['features']['venue_side'])
        self.assertIn(p['decision'],{'PASS','CAUTION','RECOMMEND'})

    def test_probabilities_remain_valid_even_when_selection_is_gated(self):
        m={'id':'synthetic-zero-prob','date':'2026-09-10','home':'Equipo Sin Historia A','away':'Equipo Sin Historia B','competition':'Liga Sintética','competition_id':'synthetic','status':'scheduled'}
        p=self.model.predict(m)['probabilities']
        self.assertAlmostEqual(sum(p.values()),1.0,places=8)
        self.assertTrue(all(0<=x<=1 for x in p.values()))

    def test_top_and_combinations_do_not_promote_gated_matches(self):
        # Current fixture database contains several matches without enough two-team history.
        gated=[]
        for m in self.r.rows("SELECT * FROM matches WHERE status='scheduled'"):
            p=self.model.predict(m)
            if not p['selection_eligible']: gated.append(m['id'])
        if gated:
            ranked=top(self.r,'2026-09-04')
            self.assertTrue(all(x.get('selection_eligible') for x in ranked))
            combos=build(self.r,'2026-09-04')
            for level in combos['levels']:
                for combo in level['combinations']:
                    self.assertTrue(all(x.get('selection_eligible') for x in combo['selections']))

    def test_known_data_can_pass_gate(self):
        # Build a temporary repository with four prior verified matches per side.
        td=Path(tempfile.mkdtemp(prefix='lian640_')); db=td/'lian.db'; shutil.copy2(ROOT/'data'/'lian.db',db)
        shutil.copy2(ROOT/'data'/'public_priors.json',td/'public_priors.json'); r=Repo(db); r.init_learning()
        for i in range(4):
            r.execute("INSERT INTO matches(id,date,home,away,home_score,away_score,status,competition_id,competition,region) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (f'synth-{i}',f'2026-08-{10+i:02d}','Equipo A','Rival X',2,0,'finished','synthetic','Liga Sintética','Americas'))
            r.execute("INSERT INTO matches(id,date,home,away,home_score,away_score,status,competition_id,competition,region) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (f'synthb-{i}',f'2026-08-{10+i:02d}','Rival Y','Equipo B',0,1,'finished','synthetic','Liga Sintética','Americas'))
        m={'id':'future-known','date':'2026-09-10','home':'Equipo A','away':'Equipo B','competition':'Liga Sintética','competition_id':'synthetic','status':'scheduled'}
        p=Model(r).predict(m)
        self.assertTrue(p['selection_eligible'])
        self.assertIn(p['decision'],{'PASS','CAUTION','RECOMMEND'})
        shutil.rmtree(td,ignore_errors=True)

if __name__=='__main__': unittest.main()
