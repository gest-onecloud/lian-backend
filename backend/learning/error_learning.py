import math,json
from .adaptive_engine import AdaptiveLearningEngine
class ErrorLearning:
 def __init__(self,repo): self.r=repo; self.r.init_learning()
 def autopsy(self,match,pred):
  if match.get('status')!='finished' or match.get('home_score') is None or match.get('away_score') is None:return {'status':'not_finished'}
  actual=AdaptiveLearningEngine.actual(match)
  p={k:float(pred.get('probabilities',{}).get(k,0) or 0) for k in ('1','X','2')}
  predicted=max(p,key=p.get)
  b=sum((p[k]-(1 if k==actual else 0))**2 for k in ('1','X','2')); ll=-math.log(max(1e-12,p[actual]))
  ge=abs(pred.get('expected_goals',{}).get('home',0)-match['home_score'])+abs(pred.get('expected_goals',{}).get('away',0)-match['away_score'])
  diagnoses=[]
  if predicted!=actual:diagnoses.append('pick_error')
  if actual=='X' and max(p.values())<.45: diagnoses.append('high_draw_uncertainty')
  if pred.get('confidence',0)<.30 and predicted!=actual: diagnoses.append('low_confidence_miss')
  if abs(p['1']-p['2'])<.03: diagnoses.append('local_away_close')
  if pred.get('confidence',0)>.70 and predicted!=actual: diagnoses.append('overconfidence')
  if pred.get('evidence',0)<.55:diagnoses.append('low_evidence')
  self.r.execute('INSERT OR REPLACE INTO postmatch_reviews(match_id,model_version,predicted,actual,brier,log_loss,goal_error,calibration_gap,diagnosis) VALUES(?,?,?,?,?,?,?,?,?)',(match['id'],pred.get('model_version',__import__('backend.core.model',fromlist=['Model']).Model.VERSION),predicted,actual,b,ll,ge,abs(max(p.values())-(1 if predicted==actual else 0)),json.dumps(diagnoses)))
  return {'status':'reviewed','actual':actual,'predicted':predicted,'brier':b,'log_loss':ll,'goal_error':ge,'diagnosis':diagnoses}

 def report(self):
  r=self.r.one('SELECT COUNT(*) n,AVG(brier) b,AVG(log_loss) l,AVG(goal_error) g FROM postmatch_reviews') or {}
  wrong=self.r.one("SELECT COUNT(*) n FROM postmatch_reviews WHERE predicted<>actual") or {}
  return {'reviews':r.get('n',0),'wrong':wrong.get('n',0),'accuracy':None if not r.get('n') else 1-wrong.get('n',0)/r.get('n'),'brier':r.get('b'),'log_loss':r.get('l'),'goal_error':r.get('g')}
