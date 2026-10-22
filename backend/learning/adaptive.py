import json, math
class Adaptive:
 def __init__(self,repo): self.r=repo; self.r.init_learning()
 def report(self):
  self._ensure()
  e=self.r.one('SELECT COUNT(*) n FROM adaptive_events')['n']; runs=self.r.one('SELECT COUNT(*) n FROM model_runs')['n']; rev=self.r.one('SELECT COUNT(*) n FROM postmatch_reviews')['n'];
  ev=self.r.one('SELECT AVG(brier) b,AVG(log_loss) l FROM postmatch_reviews') or {}
  return {'scopes':['league','team','player','match','context','model'],'events':e,'runs':runs,'reviews':rev,'brier':ev.get('b'),'log_loss':ev.get('l'),'policy':'walk-forward; actual-results-only updates; no future leakage; calibration; rollback on degradation; module isolation'}
 def _ensure(self): self.r.init_learning(); self.r.one('SELECT 1')
 def record(self,match_id,scope,entity,payload): self.r.execute('INSERT INTO adaptive_events(match_id,scope,entity,payload) VALUES(?,?,?,?)',(match_id,scope,entity,json.dumps(payload,ensure_ascii=False)))
