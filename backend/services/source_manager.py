from __future__ import annotations
import json, os, urllib.request, urllib.parse
from datetime import datetime, timezone
from .data_fusion import DataFusion

class SourceManager:
    """OR/fallback source manager. No football API is required by default.
    Sources are optional adapters configured locally. An adapter must return a
    normalized list of records. Failed sources are skipped; successful sources
    are fused and deduplicated."""
    VERSION='63.0.0'
    def __init__(self,repo):
        self.r=repo; self.fusion=DataFusion(repo); self._schema()
    def _schema(self):
        self.r.execute('''CREATE TABLE IF NOT EXISTS source_registry_v2(
            source TEXT PRIMARY KEY, kind TEXT, priority INTEGER DEFAULT 100, enabled INTEGER DEFAULT 1,
            url TEXT, last_success TEXT, last_failure TEXT, failures INTEGER DEFAULT 0, records INTEGER DEFAULT 0,
            notes TEXT
        )''')
        defaults=[('LOCAL_CACHE','local',1,1,'', 'Base local; always available'),('PUBLIC_JSON','json',50,1,os.getenv('LIAN_PUBLIC_JSON_URL',''),'Optional authorized public JSON/CSV endpoint'),('PUBLIC_JSON_2','json',55,1,os.getenv('LIAN_PUBLIC_JSON_URL_2',''),'Optional second authorized public JSON/CSV endpoint'),('PUBLIC_JSON_3','json',60,1,os.getenv('LIAN_PUBLIC_JSON_URL_3',''),'Optional third authorized public JSON/CSV endpoint')]
        for s,k,p,e,u,n in defaults:
            self.r.execute('INSERT OR IGNORE INTO source_registry_v2(source,kind,priority,enabled,url,notes) VALUES(?,?,?,?,?,?)',(s,k,p,e,u,n))
    def _fetch(self,url):
        req=urllib.request.Request(url,headers={'User-Agent':'LiAn-DataEngine/60.0'})
        with urllib.request.urlopen(req,timeout=8) as resp:return resp.read().decode('utf-8','ignore')
    def _records_from_json(self,raw):
        d=json.loads(raw)
        if isinstance(d,dict): d=d.get('matches') or d.get('events') or d.get('data') or []
        out=[]
        for x in d if isinstance(d,list) else []:
            if not isinstance(x,dict): continue
            home=x.get('home') or x.get('homeTeam') or x.get('home_team')
            away=x.get('away') or x.get('awayTeam') or x.get('away_team')
            date=str(x.get('date') or x.get('startTime') or '')[:10]
            if home and away and date: out.append({'id':x.get('id'),'date':date,'home':home,'away':away,'competition':x.get('competition') or x.get('league'),'competition_id':x.get('competition_id') or x.get('league_id'),'timestamp':x.get('timestamp'),'home_score':x.get('home_score'),'away_score':x.get('away_score')})
        return out
    def collect(self,date, local_records=None):
        report={'date':date,'sources':[],'accepted':0,'canonical':0,'failures':[]}
        if local_records:
            z=self.fusion.ingest('LOCAL_CACHE',[x for x in local_records if str(x.get('date',''))[:10]==date],1); report['sources'].append(z)
        rows=self.r.rows('SELECT * FROM source_registry_v2 WHERE enabled=1 ORDER BY priority ASC')
        for src in rows:
            if src['source']=='LOCAL_CACHE' or not src.get('url'): continue
            try:
                rec=self._records_from_json(self._fetch(src['url']))
                rec=[x for x in rec if x['date']==date]
                z=self.fusion.ingest(src['source'],rec,int(src['priority']))
                now=datetime.now(timezone.utc).isoformat(); self.r.execute('UPDATE source_registry_v2 SET last_success=?,failures=0,records=records+? WHERE source=?',(now,len(rec),src['source']))
                report['sources'].append(z)
            except Exception as ex:
                now=datetime.now(timezone.utc).isoformat(); self.r.execute('UPDATE source_registry_v2 SET last_failure=?,failures=failures+1 WHERE source=?',(now,src['source']))
                report['failures'].append({'source':src['source'],'error':str(ex)})
        report['canonical']=len(self.fusion.matches_for_date(date)); report['accepted']=report['canonical']
        report['mode']='multi-source-fusion-with-fallback'
        return report
