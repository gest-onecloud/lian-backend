import json, math
from datetime import date
import unicodedata

def key(s): return ''.join(c for c in unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower() if c.isalnum() or c==' ').strip()

class HistoricalMaster:
    """Leakage-safe historical warehouse exporter/upserter.
    It stores the state that can be known as of each fixture date, never the future result as a feature.
    """
    def __init__(self, repo): self.r=repo

    @staticmethod
    def result(h,a):
        if h is None or a is None:return None
        return '1' if h>a else 'X' if h==a else '2'

    def _elo_as_of(self, as_of):
        rows=self.r.rows("SELECT date,home,away,home_score,away_score FROM matches WHERE status='finished' AND date<? ORDER BY date ASC,id ASC",(as_of,))
        ratings={}
        for r in rows:
            h,a=key(r['home']),key(r['away']); rh=ratings.get(h,1500.); ra=ratings.get(a,1500.)
            exp=1/(1+10**((ra-rh)/400)); act=1 if r['home_score']>r['away_score'] else .5 if r['home_score']==r['away_score'] else 0
            k=22 if abs(r['home_score']-r['away_score'])>=2 else 20
            ratings[h]=rh+k*(act-exp); ratings[a]=ra+k*((1-act)-(1-exp))
        return ratings

    def build(self, limit=None):
        q="SELECT * FROM matches WHERE status='finished' AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY date ASC,id ASC"
        if limit:q += f" LIMIT {int(limit)}"
        rows=self.r.rows(q); n=0
        for m in rows:
            elos=self._elo_as_of(m['date']); eh=elos.get(key(m['home']),1500.); ea=elos.get(key(m['away']),1500.)
            self.r.execute('''INSERT OR REPLACE INTO historical_master(match_id,as_of,home,away,competition,season,home_score,away_score,result,home_elo,away_elo,home_tier,away_tier,data_quality,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (m['id'],m['date'],m['home'],m['away'],m.get('competition'),m.get('season'),m['home_score'],m['away_score'],self.result(m['home_score'],m['away_score']),eh,ea,None,None,1.0,m.get('source') or 'local'))
            n+=1
        return {'ingested':n}
