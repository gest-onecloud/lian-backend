from ..core.model import Model

def raw_matches(repo,date):
 return repo.rows('SELECT * FROM matches WHERE date=? ORDER BY CASE WHEN time IS NULL OR time="" THEN 1 ELSE 0 END,time,competition,home',(date,))

def matches(repo,date):
 rows=raw_matches(repo,date); model=Model(repo)
 return [{**m,**model.predict(m)} for m in rows]

def competitions(repo,date):
 return repo.rows('SELECT competition_id,competition,region,country,COUNT(*) n FROM matches WHERE date=? GROUP BY competition_id,competition,region,country ORDER BY region,competition',(date,))
