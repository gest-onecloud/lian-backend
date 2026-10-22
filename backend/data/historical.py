import csv,io,json,urllib.request,urllib.error,datetime,re
from pathlib import Path

# Verified public structured source. OpenFootball documents these season/competition paths.
OPENFOOTBALL={
 'Premier League':('EN-PL','en.1.json'),'LaLiga':('ES-LALIGA','es.1.json'),'Bundesliga':('DE-BUND','de.1.json'),
 'Serie A':('IT-SERIEA','it.1.json'),'Ligue 1':('FR-L1','fr.1.json')}
SEASONS=['2019-20','2020-21','2021-22','2022-23','2023-24','2024-25']
BASE='https://raw.githubusercontent.com/openfootball/football.json/master'
LIGAMX='https://raw.githubusercontent.com/CarlosYoung0/ligamx-data/main/data/historical.csv'

def _slug(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
class HistoricalSync:
 def __init__(self,repo,timeout=20): self.r=repo; self.timeout=timeout
 def fetch(self,url):
  req=urllib.request.Request(url,headers={'User-Agent':'LiAn/55.0 Historical Orchestrator'})
  with urllib.request.urlopen(req,timeout=self.timeout) as resp:return resp.status,resp.read()
 def parse_openfootball(self,raw,league,season):
  obj=json.loads(raw.decode('utf-8-sig')); out=[]
  for m in obj.get('matches',[]):
   score=m.get('score'); ft=score.get('ft') if isinstance(score,dict) else None
   if not isinstance(ft,list) or len(ft)!=2:continue
   out.append({'date':m.get('date'),'time':m.get('time'),'season':season,'competition':league,'home':m.get('team1'),'away':m.get('team2'),'home_score':int(ft[0]),'away_score':int(ft[1]),'round':m.get('round')})
  return out
 def parse_ligamx(self,raw):
  out=[]
  for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
   if not r.get('date') or r.get('home_score') in ('',None) or r.get('away_score') in ('',None):continue
   try: hs,as_=int(r['home_score']),int(r['away_score'])
   except:continue
   out.append({'date':r['date'],'season':r.get('season'),'competition':'Liga MX','home':r.get('home_team'),'away':r.get('away_team'),'home_score':hs,'away_score':as_,'round':r.get('round')})
  return out
 def upsert(self,rows,cid,source,region='Europe',country=''):
  n=0; c=self.r.connect()
  try:
   for x in rows:
    if not x.get('date') or not x.get('home') or not x.get('away'):continue
    mid=f"hist:{cid}:{x['date']}:{_slug(x['home'])}:{_slug(x['away'])}"
    c.execute('''INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url,data_quality)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(date,home,away) DO UPDATE SET home_score=excluded.home_score,away_score=excluded.away_score,status='finished',source=excluded.source,updated_at=excluded.updated_at,season=excluded.season,source_url=excluded.source_url,data_quality=max(matches.data_quality,excluded.data_quality)''',
      (mid,x['date'],x.get('time'),cid,x['competition'],region,country,x['home'],x['away'],x['home_score'],x['away_score'],'finished',source,datetime.datetime.now().isoformat(timespec='seconds'),x.get('season'),source,0.95)); n+=1
   c.commit()
  finally:c.close()
  return n
 def run(self):
  report={'sources':0,'parsed':0,'inserted':0,'failures':[],'providers':[]}
  for league,(cid,fn) in OPENFOOTBALL.items():
   for season in SEASONS:
    url=f'{BASE}/{season}/{fn}'; report['sources']+=1
    try:
     status,raw=self.fetch(url)
     if status!=200:raise RuntimeError(f'HTTP {status}')
     rows=self.parse_openfootball(raw,league,season); report['parsed']+=len(rows); report['inserted']+=self.upsert(rows,cid,url); report['providers'].append({'source':'openfootball','league':league,'season':season,'status':'ok','rows':len(rows)})
    except Exception as e:report['failures'].append({'source':'openfootball','league':league,'season':season,'url':url,'error':str(e)})
  report['sources']+=1
  try:
   status,raw=self.fetch(LIGAMX)
   if status!=200:raise RuntimeError(f'HTTP {status}')
   rows=self.parse_ligamx(raw); report['parsed']+=len(rows); report['inserted']+=self.upsert(rows,'MX-LIGA',LIGAMX,'Americas','México'); report['providers'].append({'source':'ligamx-data','status':'ok','rows':len(rows)})
  except Exception as e:report['failures'].append({'source':'ligamx-data','url':LIGAMX,'error':str(e)})
  return report
 def search_and_cache(self,home,away,competition_id=None,days=3650):
  # Local-first. External sources can be added without changing prediction code.
  params=[home,away,home,away]
  rows=self.r.rows('''SELECT * FROM matches WHERE status='finished' AND ((lower(home)=lower(?) AND lower(away)=lower(?)) OR (lower(home)=lower(?) AND lower(away)=lower(?))) ORDER BY date DESC LIMIT 50''',params)
  return {'found':len(rows)>0,'matches':rows,'source':'local' if rows else 'none','request_required':not bool(rows)}
