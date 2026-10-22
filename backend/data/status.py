from .repo import Repo

class DataStatus:
 def __init__(self,repo): self.r=repo
 def report(self):
  total=self.r.one("SELECT COUNT(*) n FROM matches")['n']
  finished=self.r.one("SELECT COUNT(*) n FROM matches WHERE status='finished'")['n']
  scheduled=self.r.one("SELECT COUNT(*) n FROM matches WHERE status='scheduled'")['n']
  reviews=self.r.one("SELECT COUNT(*) n FROM postmatch_reviews")['n']
  predictions=self.r.one("SELECT COUNT(*) n FROM predictions")['n']
  leagues=self.r.rows("SELECT competition_id,competition,COUNT(*) n FROM matches WHERE status='finished' GROUP BY competition_id,competition ORDER BY n DESC")
  return {'version':'64.6.0','model_version':'64.0.0','total_matches':total,'finished_matches':finished,'scheduled_matches':scheduled,'predictions':predictions,'reviews':reviews,'feature_snapshots':self.r.one('SELECT COUNT(*) n FROM feature_snapshots')['n'],'leagues':leagues,'historical_ready':finished>=1000,'model_evaluation_ready':reviews>=100,'policy':'Datos temporales: una predicción histórica solo se considera válida para evaluación si existía antes del resultado. Las probabilidades son estimaciones; la confianza no equivale a una tasa histórica de acierto.'}
