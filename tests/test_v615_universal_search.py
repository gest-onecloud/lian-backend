import datetime as dt, unittest
from unittest.mock import patch
class V615Universal(unittest.TestCase):
 def test_single_team_discovery_filters_short_substrings(self):
  import backend.services.targeted_search as t
  with patch.object(t,'_team_candidates',return_value=[('FAKE','1','FC Barcelona',{})]), patch.object(t,'_events_for',return_value=[{'id':'old','home':'Elche','away':'FC Barcelona','date':'2026-08-23','league':'LaLiga'},{'id':'new','home':'Valencia CF','away':'FC Barcelona','date':'2026-09-06','league':'LaLiga'},{'id':'bad','home':'A','away':'B','date':'2026-09-07','league':'Test'}]):
   x=t.discover_team('Barcelona',today=dt.date(2026,9,2),days=45); self.assertTrue(x['found']); self.assertEqual(x['candidates'][0]['id'],'new'); self.assertTrue(all(c['id']!='bad' for c in x['candidates']))
 def test_split_pair_still_works(self):
  from backend.services.targeted_search import split_pair; self.assertEqual(split_pair('Valencia vs Barcelona'),('Valencia','Barcelona'))
 def test_short_team_names_do_not_match_arbitrarily(self):
  from backend.services.universal import resolve
  class R:
   def rows(self,q): return [{'id':'1','home':'A','away':'B','competition':'Test','date':'2099-01-01','status':'scheduled'}]
  self.assertEqual(resolve(R(),'Valencia vs Barcelona'),[])
 def test_local_resolver_never_returns_unrelated_future_match(self):
  from backend.services.universal import resolve
  class R:
   def rows(self,q): return [{'id':'wrong','home':'Corpus Christi FC','away':'Tormenta','competition':'USL','date':'2026-09-03','status':'scheduled'},{'id':'right','home':'Valencia CF','away':'FC Barcelona','competition':'LaLiga','date':'2026-09-06','status':'scheduled'}]
  self.assertEqual([m['id'] for m in resolve(R(),'Valencia vs Barcelona',5)],['right'])
 def test_single_team_local_resolver_excludes_unrelated_future_matches(self):
  from backend.services.universal import resolve
  class R:
   def rows(self,q): return [{'id':'wrong','home':'Corpus Christi FC','away':'Tormenta','competition':'USL','date':'2026-09-03','status':'scheduled'},{'id':'right','home':'FC Barcelona','away':'Feyenoord','competition':'Champions League','date':'2026-09-09','status':'scheduled'}]
  self.assertEqual([m['id'] for m in resolve(R(),'Barcelona')],['right'])
if __name__=='__main__': unittest.main()
