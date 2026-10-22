import unittest
from backend.services.explainability import explain

class ExplainabilityTests(unittest.TestCase):
    def base(self,p):
        return {'probabilities':p,'evidence':.25,'confidence':.113,'quality':'BAJA','features':{'elo_diff':0,'form_diff':0,'home_history':0,'away_history':0,'h2h':0},'expected_goals':{'home':1.42,'away':1.42},'player_impact':{'home':0,'away':0}}
    def test_equal_home_away_does_not_force_pick(self):
        r=explain(self.base({'1':.359,'X':.282,'2':.359}),{'home':'CF Monterrey','away':'Chicago Fire FC'})
        self.assertEqual(r['status'],'SIN FAVORITO CLARO')
        self.assertIsNone(r['favorite'])
    def test_small_edge_is_labeled(self):
        r=explain(self.base({'1':.39,'X':.28,'2':.33}),{'home':'A','away':'B'})
        self.assertEqual(r['status'],'LIGERA VENTAJA')
        self.assertEqual(r['favorite'],'Local')
    def test_clear_favorite(self):
        r=explain(self.base({'1':.60,'X':.22,'2':.18}),{'home':'A','away':'B'})
        self.assertEqual(r['status'],'FAVORITO CLARO')
        self.assertEqual(r['favorite'],'Local')
if __name__=='__main__': unittest.main()
