from __future__ import annotations
import hashlib, re
from collections import defaultdict
from datetime import datetime, timezone

def norm(s):
    return re.sub(r'[^a-z0-9]+','',str(s).lower())

def logical_match_key(item):
    comp=norm(item.get('competition_id') or item.get('competition') or '')
    date=str(item.get('date') or '')[:10]
    home=norm(item.get('home') or '')
    away=norm(item.get('away') or '')
    return '|'.join((date,comp,home,away))

class DataFusion:
    """Fuse records from multiple allowed sources into one canonical record.
    Conflicting values are resolved by source priority and recency; duplicates
    are never emitted twice for the same logical match."""
    def __init__(self, repo):
        self.r=repo; self._schema()
    def _schema(self):
        self.r.execute('''CREATE TABLE IF NOT EXISTS source_observations(
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_key TEXT NOT NULL, source TEXT NOT NULL,
            observed_at TEXT NOT NULL, payload TEXT NOT NULL, fingerprint TEXT NOT NULL,
            UNIQUE(entity_key,source,fingerprint)
        )''')
        self.r.execute('''CREATE TABLE IF NOT EXISTS canonical_entities(
            entity_key TEXT PRIMARY KEY, entity_type TEXT NOT NULL, payload TEXT NOT NULL,
            source_count INTEGER DEFAULT 0, sources TEXT DEFAULT '', quality REAL DEFAULT 0,
            updated_at TEXT NOT NULL
        )''')
    @staticmethod
    def _fp(payload):
        import json
        return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    def ingest(self, source, records, priority=100):
        import json
        now=datetime.now(timezone.utc).isoformat()
        grouped=defaultdict(list)
        for item in records or []:
            k=logical_match_key(item)
            if not k or k.startswith('|||'): continue
            fp=self._fp(item)
            try:self.r.execute('INSERT OR IGNORE INTO source_observations(entity_key,source,observed_at,payload,fingerprint) VALUES(?,?,?,?,?)',(k,source,now,json.dumps(item,ensure_ascii=False),fp))
            except Exception: pass
            grouped[k].append((priority,now,item,source))
        for k, vals in grouped.items():
            # Also include prior observations, so a later source can enrich an older one.
            rows=self.r.rows('SELECT source,observed_at,payload FROM source_observations WHERE entity_key=? ORDER BY observed_at DESC',(k,))
            allv=list(vals)
            for row in rows:
                try: allv.append((priority,row['observed_at'],json.loads(row['payload']),row['source']))
                except Exception: pass
            canonical={}
            for _,ts,item,src in sorted(allv,key=lambda x:x[1],reverse=True):
                for key,val in item.items():
                    if val not in (None,'',[]): canonical.setdefault(key,val)
            sources=sorted(set(x[3] for x in allv))
            quality=min(1.0,0.35+0.15*len(sources))
            self.r.execute('INSERT OR REPLACE INTO canonical_entities(entity_key,entity_type,payload,source_count,sources,quality,updated_at) VALUES(?,?,?,?,?,?,?)',(k,'match',json.dumps(canonical,ensure_ascii=False),len(sources),','.join(sources),quality,now))
        return {'source':source,'ingested':len(records or []),'canonical':len(grouped),'duplicates_suppressed':max(0,len(records or [])-len(grouped))}
    def matches_for_date(self,date):
        import json
        out=[]
        for r in self.r.rows('SELECT * FROM canonical_entities WHERE entity_type="match"'):
            try:x=json.loads(r['payload'])
            except Exception: continue
            if str(x.get('date',''))[:10]==date:
                x['_fusion']={'source_count':r['source_count'],'sources':r['sources'].split(',') if r['sources'] else [],'quality':r['quality']}
                out.append(x)
        return out
