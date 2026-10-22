"""Verified result ingestion with multi-source OR/fallback semantics.

Sources are consulted independently. A result is accepted only when both teams and a
completed score are present. Historical data is never replaced by a lower-quality
provider result once a verified provenance record exists.
"""
from __future__ import annotations
import json, re, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BUNDLED = Path(__file__).resolve().parents[2] / 'data' / 'verified_results.json'
MX=ZoneInfo('America/Mexico_City')
ESPN_ALL='https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
ESPN_ALT='https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
SOFA_DAY='https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}'
TSDB_DAY='https://www.thesportsdb.com/api/v1/json/3/eventsday.php'

FINISHED={'match finished','ft','aet','after extra time','finished','final','post','completed','complete'}

class ResultsSync:
    VERSION='63.0.0'
    def __init__(self, repo):
        self.r=repo; self.r.init_learning(); self._ensure_schema()
    def _ensure_schema(self):
        self.r.execute("""CREATE TABLE IF NOT EXISTS result_sources(
            match_id TEXT PRIMARY KEY, source TEXT NOT NULL, source_type TEXT NOT NULL,
            source_url TEXT, verified_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'verified'
        )""")
        self.r.execute("""CREATE TABLE IF NOT EXISTS calibration_recommendations(
            id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, scope TEXT, metric TEXT,
            samples INTEGER, current_value REAL, target_value REAL, recommendation TEXT,
            eligible INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        for col,typ in [('result_source','TEXT'),('result_source_type','TEXT'),('result_source_url','TEXT'),('result_verified_at','TEXT')]:
            try:self.r.execute(f'ALTER TABLE matches ADD COLUMN {col} {typ}')
            except Exception:pass
    @staticmethod
    def _norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower().replace('’',"'"))
    @staticmethod
    def _team_match(a,b):
        a=ResultsSync._norm(a); b=ResultsSync._norm(b)
        if not a or not b:return False
        removable={'fc','cf','club','futbol','football'}
        def compact(x):
            return ''.join(t for t in re.sub(r'[^a-z0-9]+',' ',x).split() if t not in removable)
        aa,bb=compact(a),compact(b)
        if aa==bb:return True
        # Safe suffix tolerance only; arbitrary substring matching caused collisions.
        suffix={'laguna','city','united','athletic','atletico','real','sporting','municipal'}
        ap=re.sub(r'[^a-z0-9]+',' ',a).split(); bp=re.sub(r'[^a-z0-9]+',' ',b).split()
        if ap and bp:
            ac=[x for x in ap if x not in removable]; bc=[x for x in bp if x not in removable]
            if all(x in bc for x in ac) and set(bc)-set(ac) <= suffix:return True
            if all(x in ac for x in bc) and set(ac)-set(bc) <= suffix:return True
        return False
    def _apply(self,row,source,source_type,url):
        m=self.r.one('SELECT * FROM matches WHERE id=?',(row['match_id'],))
        if not m:return False
        # Preserve verified results, but allow an authoritative bundled/official
        # observation to upgrade a lower-quality secondary observation.
        existing_type=str(m.get('result_source_type') or '').lower()
        incoming_type=str(source_type or '').lower()
        if m.get('home_score') is not None and m.get('away_score') is not None and m.get('result_source'):
            if int(m.get('home_score')) == int(row['home_score']) and int(m.get('away_score')) == int(row['away_score']):
                return True
            if existing_type == 'official' or incoming_type != 'official':
                return False
        now=datetime.now(timezone.utc).isoformat()
        self.r.execute("UPDATE matches SET status='finished',home_score=?,away_score=?,result_source=?,result_source_type=?,result_source_url=?,result_verified_at=? WHERE id=?",
                        (int(row['home_score']),int(row['away_score']),source,source_type,url,now,row['match_id']))
        self.r.execute("INSERT OR REPLACE INTO result_sources(match_id,source,source_type,source_url,verified_at,status) VALUES(?,?,?,?,?,'verified')",
                       (row['match_id'],source,source_type,url,now))
        return True
    def bundled(self,date):
        if not BUNDLED.exists():return []
        try:data=json.loads(BUNDLED.read_text(encoding='utf-8'))
        except Exception:return []
        applied=[]
        for r in data.get(date,[]):
            if self._apply(r,r.get('source','Bundled verified snapshot'),r.get('source_type','secondary'),r.get('source_url','')):
                applied.append(r['match_id'])
        return applied
    def fetch_url(self,url,timeout=8):
        req=urllib.request.Request(url,headers={'User-Agent':'LiAn/64.6.0 result-verifier'})
        with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','ignore')
    def _scheduled(self,date):
        return self.r.rows("SELECT * FROM matches WHERE date=? AND (home_score IS NULL OR away_score IS NULL)",(date,))
    def _accept(self, events, source, url, scheduled, applied):
        for ev in events:
            hs=ev.get('home_score'); aw=ev.get('away_score'); status=str(ev.get('status') or '').lower()
            if hs is None or aw is None:continue
            if status and status not in FINISHED and not ev.get('completed'):continue
            for m in scheduled:
                if self._team_match(ev.get('home'),m.get('home')) and self._team_match(ev.get('away'),m.get('away')):
                    if self._apply({'match_id':m['id'],'home_score':int(hs),'away_score':int(aw)},source,'public',url):applied.append(m['id'])
                    break
    def _espn(self,date):
        ymd=date.replace('-',''); urls=[ESPN_ALL+'?'+urllib.parse.urlencode({'dates':ymd}),ESPN_ALT+'?'+urllib.parse.urlencode({'dates':ymd})]
        diagnostics=[]; events=[]
        for url in urls:
            try:
                data=json.loads(self.fetch_url(url) or '{}'); count=0
                for ev in data.get('events') or []:
                    comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
                    h=next((x for x in teams if x.get('homeAway')=='home'),None); a=next((x for x in teams if x.get('homeAway')=='away'),None)
                    if not h or not a:continue
                    stamp=ev.get('date'); d=''
                    try:d=datetime.fromisoformat(str(stamp).replace('Z','+00:00')).astimezone(MX).date().isoformat()
                    except Exception:pass
                    if d!=date:continue
                    hs=(h.get('score') or None); aw=(a.get('score') or None); st=((comp.get('status') or {}).get('type') or {})
                    events.append({'home':(h.get('team') or {}).get('displayName'),'away':(a.get('team') or {}).get('displayName'),'home_score':int(hs) if str(hs).isdigit() else None,'away_score':int(aw) if str(aw).isdigit() else None,'status':st.get('name') or st.get('description') or '', 'completed':bool(st.get('completed'))})
                    count+=1
                diagnostics.append({'source':'ESPN','ok':True,'records':count,'url':url})
                if count:break
            except Exception as ex:diagnostics.append({'source':'ESPN','ok':False,'error':repr(ex),'url':url})
        return events,diagnostics
    def _sofa(self,date):
        url=SOFA_DAY.format(date=date)
        data=json.loads(self.fetch_url(url) or '{}'); out=[]
        for ev in data.get('events') or []:
            h=ev.get('homeTeam') or {}; a=ev.get('awayTeam') or {}; st=ev.get('status') or {}
            if not h.get('name') or not a.get('name'):continue
            out.append({'home':h['name'],'away':a['name'],'home_score':(ev.get('homeScore') or {}).get('current'),'away_score':(ev.get('awayScore') or {}).get('current'),'status':st.get('type') or st.get('description') or '', 'completed':str(st.get('type','')).lower() in {'finished','afterextratime','afterpenalties'}})
        return out,{'source':'SOFASCORE','ok':True,'records':len(out),'url':url}
    def _tsdb(self,date):
        url=TSDB_DAY+'?'+urllib.parse.urlencode({'d':date,'s':'Soccer'}); data=json.loads(self.fetch_url(url) or '{}'); out=[]
        for e in data.get('events') or []:
            out.append({'home':e.get('strHomeTeam'),'away':e.get('strAwayTeam'),'home_score':int(e['intHomeScore']) if str(e.get('intHomeScore','')).isdigit() else None,'away_score':int(e['intAwayScore']) if str(e.get('intAwayScore','')).isdigit() else None,'status':e.get('strStatus') or ''})
        return out,{'source':'THESPORTSDB','ok':True,'records':len(out),'url':url}
    def online(self,date):
        scheduled=self._scheduled(date); applied=[]; diagnostics=[]
        for fn in (self._espn,self._sofa,self._tsdb):
            try:
                events,diag=fn(date); diagnostics.extend(diag if isinstance(diag,list) else [diag]); self._accept(events,diag[0]['source'] if isinstance(diag,list) else diag['source'],diag[0]['url'] if isinstance(diag,list) else diag['url'],scheduled,applied)
            except Exception as ex: diagnostics.append({'source':getattr(fn,'__name__','provider'),'ok':False,'error':repr(ex)})
            if len(applied)>=len(scheduled):break
        return applied,diagnostics
    def sync(self,date):
        applied=self.bundled(date); online_attempted=False; errors=[]; diagnostics=[]
        import os
        if os.getenv('LIAN_DISABLE_LIVE_RESULTS','0')!='1':
            try:
                more,diagnostics=self.online(date); online_attempted=True
                applied.extend([x for x in more if x not in applied])
            except Exception as e:online_attempted=True; errors.append(str(e))
        return {'date':date,'applied':len(applied),'match_ids':applied,'online_attempted':online_attempted,'online_error':'; '.join(errors) or None,'diagnostics':diagnostics,'policy':'OR multi-source verified results: bundled → ESPN → SofaScore → TheSportsDB; no invented scores; verified result feeds Post-Match and Adaptive Learning.'}
