import datetime as dt, unittest
from unittest.mock import patch
from backend.services.targeted_search import split_pair, discover_pair
class V614Targeted(unittest.TestCase):
 def test_split_explicit_pair(self): self.assertEqual(split_pair('Valencia vs Barcelona'),('Valencia','Barcelona'))
 def test_targeted_pair_filters_wrong_fixture(self):
  import backend.services.targeted_search as t
  def events(source,tid,timeout=6): return [{'id':'wrong','home':'Elche','away':'Barcelona','date':'2026-09-06','league':'LaLiga'},{'id':'right','home':'Valencia CF','away':'FC Barcelona','date':'2026-09-06','league':'LaLiga'}]
  with patch.object(t,'_team_candidates',return_value=[('FAKE','1','Valencia',{})]), patch.object(t,'_events_for',side_effect=events):
   x=discover_pair('Valencia vs Barcelona',today=dt.date(2026,9,2),days=45); self.assertTrue(x['found']); self.assertEqual(x['candidates'][0]['id'],'right')
 def test_targeted_search_does_not_invent(self):
  import backend.services.targeted_search as t
  with patch.object(t,'_team_candidates',return_value=[]), patch.object(t,'discover_calendar',return_value={'found':False,'candidates':[],'sources':{}}):
   x=discover_pair('Valencia vs Barcelona',today=dt.date(2026,9,2)); self.assertFalse(x['found']); self.assertEqual(x['candidates'],[])
if __name__=='__main__': unittest.main()
