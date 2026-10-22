from __future__ import annotations
import json, urllib.parse, urllib.request, datetime as dt

class LiveContextEngine:
    """Collects optional pre-match context with provenance. Missing data stays neutral."""
    VERSION='63.0.0'
    def __init__(self, repo):
        self.r=repo; self._schema()
    def _schema(self):
        self.r.execute('''CREATE TABLE IF NOT EXISTS live_context(
          match_id TEXT PRIMARY KEY, as_of TEXT NOT NULL, payload TEXT NOT NULL,
          source_count INTEGER DEFAULT 0, quality REAL DEFAULT 0, status TEXT DEFAULT 'partial')''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS context_sources(
          match_id TEXT, source TEXT, field TEXT, value TEXT, observed_at TEXT,
          PRIMARY KEY(match_id,source,field))''')
    def _get(self,url,timeout=5):
        req=urllib.request.Request(url,headers={'User-Agent':'LiAn/55.9'})
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8'))
    @staticmethod
    def _norm(s):
        import re
        return re.sub(r'[^a-z0-9]','',str(s).lower())
    def venue_coords(self,m):
        # Reuse known venue resolver when available; no fabricated coordinates.
        try:
            from ..services.venue import resolve
            v=resolve(m)
            coords=v.get('coordinates') or {}
            if coords.get('lat') is not None and coords.get('lon') is not None:return float(coords['lat']),float(coords['lon']),v
        except Exception: pass
        return None,None,{}
    def weather(self,m):
        lat,lon,v=self.venue_coords(m)
        if lat is None:return None
        try:
            url='https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode({'latitude':lat,'longitude':lon,'hourly':'temperature_2m,precipitation_probability,wind_speed_10m','timezone':'auto','forecast_days':7})
            d=self._get(url); times=d.get('hourly',{}).get('time',[]); temp=d.get('hourly',{}).get('temperature_2m',[]); rain=d.get('hourly',{}).get('precipitation_probability',[]); wind=d.get('hourly',{}).get('wind_speed_10m',[])
            target=m.get('kickoff_iso') or m.get('datetime')
            if not target:return None
            target=target.replace('Z','+00:00')
            td=dt.datetime.fromisoformat(target).replace(tzinfo=None)
            best=min(range(len(times)),key=lambda i:abs(dt.datetime.fromisoformat(times[i])-td)) if times else None
            if best is None:return None
            return {'temperature_c':temp[best] if best<len(temp) else None,'precipitation_probability':rain[best] if best<len(rain) else None,'wind_kmh':wind[best] if best<len(wind) else None,'quality':1.0,'source':'Open-Meteo'}
        except Exception:return None
    def refresh(self,m):
        import os
        if os.getenv('LIAN_DISABLE_LIVE_CONTEXT','0')=='1':
            return {'match_id':m['id'],'payload':{},'source_count':0,'quality':0,'status':'disabled'}
        payload={}; sources=0
        w=self.weather(m)
        if w:
            payload['weather']=w; sources+=1
        # Explicit/manual fields are retained and are useful for confirmed lineups/referees.
        for k in ('referee','referee_home_edge','lineup_home_quality','lineup_away_quality','fitness_home','fitness_away','xi_status','travel_km_home','travel_km_away'):
            if m.get(k) is not None:payload[k]=m[k]
        quality=min(1.0,sources/3 + sum(k in payload for k in ('referee','lineup_home_quality','lineup_away_quality','fitness_home','fitness_away'))*.1)
        status='complete' if quality>=.8 else 'partial' if payload else 'unavailable'
        self.r.execute('INSERT OR REPLACE INTO live_context(match_id,as_of,payload,source_count,quality,status) VALUES(?,?,?,?,?,?)',(m['id'],dt.datetime.now(dt.timezone.utc).isoformat(),json.dumps(payload,ensure_ascii=False),sources,quality,status))
        return {'match_id':m['id'],'payload':payload,'source_count':sources,'quality':quality,'status':status}
    def get(self,match_id):
        x=self.r.one('SELECT * FROM live_context WHERE match_id=?',(match_id,))
        if not x:return None
        try:x['payload']=json.loads(x['payload'])
        except Exception:x['payload']={}
        return x
