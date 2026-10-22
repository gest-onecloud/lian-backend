class PlayerEngine:
 def __init__(self,repo): self.r=repo
 def team_impact(self,team,as_of):
  rows=self.r.rows('SELECT * FROM player_state WHERE lower(team_id)=lower(?) AND (last_date IS NULL OR last_date<?)',(team,as_of))
  if not rows:return {'players':0,'impact':0.0,'minutes':0.0}
  return {'players':len(rows),'impact':sum(float(x.get('impact') or 0) for x in rows)/len(rows),'minutes':sum(float(x.get('minutes') or 0) for x in rows)}
