import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
from backend.services.decision_intelligence import report
from backend.learning.backtest import BacktestEngine

class V553DecisionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=Repo(ROOT/'data'/'lian.db'); cls.model=Model(cls.r)
 def test_version_and_external_evidence(self):
  self.assertIn(self.model.VERSION,{'55.3','55.5','55.6','55.7','55.8','55.9','55.9.1','55.9.3','55.9.5','55.9.6','55.9.8','60.0.0','60.3.0','61.1.5','62.0.0','62.6.0','63.0.0','64.0.0','64.1.0','64.2.0','64.6.0'})
  self.assertIn('cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc',self.model.external)
 def test_monterrey_venue_and_external_form_are_used(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
  p=self.model.predict(m)
  self.assertEqual(p['features']['venue_side'],'away')
  self.assertTrue(p['features']['venue_verified'])
  self.assertLess(p['features']['external_form_diff'],0)
  self.assertGreater(p['features']['venue_advantage_away'],0)
  self.assertLess(p['features']['venue_advantage_home'],0)
 def test_decision_has_explanation_consensus_stability_counterfactual(self):
  m=self.r.one("SELECT * FROM matches WHERE id='cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc'")
  p=self.model.predict(m); e=report(p,m)
  self.assertIn(e['status'],{'FAVORITO CLARO','VENTAJA MODERADA','LIGERA VENTAJA','SIN VENTAJA CLARA','SIN FAVORITO CLARO','DATOS INSUFICIENTES'})
  self.assertIn('consensus_score',e); self.assertIn('stability_score',e); self.assertIn('counterfactual',e)
  self.assertIn('what_changes_choice',e['counterfactual'])
 def test_advanced_feature_fields_exist(self):
  m=self.r.one("SELECT * FROM matches WHERE status='scheduled' ORDER BY date LIMIT 1")
  p=self.model.predict(m); f=p['features']
  for k in ['adj_gf10_home','adj_gf10_away','adj_ga10_home','adj_ga10_away','momentum_home','momentum_away','consistency_home','consistency_away']:
   self.assertIn(k,f)
 def test_walk_forward_backtest_contract(self):
  x=BacktestEngine(self.r).run(200)
  self.assertGreaterEqual(x['samples'],1); self.assertIn('accuracy',x); self.assertIn('brier',x); self.assertIn('feature_directional_performance',x)
 def test_probabilities_sum(self):
  for m in self.r.rows("SELECT * FROM matches WHERE status='scheduled'"):
   p=self.model.predict(m)['probabilities']; self.assertAlmostEqual(sum(p.values()),1,places=6); self.assertTrue(all(0<=v<=1 for v in p.values()))
if __name__=='__main__': unittest.main()
