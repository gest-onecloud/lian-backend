"""FixtureSync FINAL FAST - 1 request, circuit breaker, background sync."""
from __future__ import annotations
import datetime as dt, json, re, urllib.parse, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
from .http_client import get_json as robust_get_json

MX=ZoneInfo('America/Mexico_City')
ESPN_ALL_BASE='https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
ESPN_ALL_ALT='https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
ESPN_BASE='https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard'
ESPN_LEAGUES_FAST=('mex.1','usa.1','eng.1','esp.1','uefa.champions')
ESPN_LEAGUES=(
    'eng.1','esp.1','ger.1','ita.1','fra.1','mex.1','usa.1',
    'eng.league_cup','uefa.champions','uefa.europa','uefa.europa.conf',
    'conmebol.libertadores','conmebol.sudamericana','usa.leagues_cup'
)
def slug(s): return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-')
def norm_team(s): return re.sub(r'[^a-z0-9]+','',str(s).casefold())
def _mx_date_from_iso(value):
    try:
        s=str(value or '').strip()
        if not s:return None
        x=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
        if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
        return x.astimezone(MX).date().isoformat()
    except:return None

_HTTP_CACHE={}; _CACHE_LOCK=threading.Lock()
_FAILURE_COUNT={}; _FAILURE_LOCK=threading.Lock()
def _should_skip(name):
    with _FAILURE_LOCK:
        info=_FAILURE_COUNT.get(name)
        if not info: return False
        c,last=info
        if c>=3 and time.time()-last<3600: return True
        if time.time()-last>3600: _FAILURE_COUNT.pop(name,None)
    return False
def _fail(name):
    with _FAILURE_LOCK:
        c,_=_FAILURE_COUNT.get(name,(0,0)); _FAILURE_COUNT[name]=(c+1,time.time())
def _ok(name):
    with _FAILURE_LOCK: _FAILURE_COUNT.pop(name,None)

class FixtureSync:
    CACHE_TTL=300
    def __init__(self, repo, timeout=3):
        self.r=repo; self.timeout=timeout
    def bootstrap_seed(self):
        data_dir=Path(__file__).resolve().parents[2]/'data'; acc=0
        for path in sorted(data_dir.glob('fixture_seed_*.json')):
            try: rows=json.loads(path.read_text(encoding='utf-8'))
            except: continue
            if not isinstance(rows,list): continue
            for e in rows:
                try:
                    d=e.get('date') or e.get('strDate')
                    if d and self._upsert(e,str(d)[:10],'seed','VerifiedFixtureSeed'): acc+=1
                except: pass
        return acc
    def _cache_key(self,date): return self.r.one('SELECT updated_at,coverage_status,match_count FROM fixture_sync_cache WHERE date=?',(date,))
    def _cache_set(self,date,status='unknown',match_count=0):
        try: self.r.execute('INSERT INTO fixture_sync_cache(date,updated_at,coverage_status,match_count) VALUES(?,?,?,?) ON CONFLICT(date) DO UPDATE SET updated_at=excluded.updated_at,coverage_status=excluded.coverage_status,match_count=excluded.match_count',(date,time.time(),status,int(match_count)))
        except:
            try: self.r.execute('INSERT OR REPLACE INTO fixture_sync_cache(date,updated_at,coverage_status,match_count) VALUES(?,?,?,?)',(date,time.time(),status,int(match_count)))
            except: pass
    def ensure_cache_schema(self):
        try: self.r.execute("CREATE TABLE IF NOT EXISTS fixture_sync_cache(date TEXT PRIMARY KEY, updated_at REAL NOT NULL, coverage_status TEXT NOT NULL DEFAULT 'unknown', match_count INTEGER NOT NULL DEFAULT 0)")
        except: pass
        for col,typ,default in [('coverage_status','TEXT',"'unknown'"),('match_count','INTEGER','0')]:
            try:self.r.execute(f'ALTER TABLE fixture_sync_cache ADD COLUMN {col} {typ} NOT NULL DEFAULT {default}')
            except:pass
    def sync_day_cached(self,date,force=False):
        self.ensure_cache_schema()
        if not force:
            row=self._cache_key(date)
            if row and row.get('coverage_status')=='complete' and time.time()-float(row['updated_at'])<self.CACHE_TTL:
                return {'date':date,'skipped':True,'reason':'fresh-complete-cache','coverage_status':'complete','match_count':int(row.get('match_count') or 0)}
        try: report=self.sync_day(date, fast=not force)
        except Exception as ex: report={'date':date,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[{'source':'fixture-sync','error':str(ex)}]}
        try:self._cache_set(date,report.get('coverage_status','unknown'),report.get('match_count',0))
        except:pass
        return report
    def _get_json(self,url):
        k=url
        with _CACHE_LOCK:
            if k in _HTTP_CACHE:
                ts,data=_HTTP_CACHE[k]
                if time.time()-ts<60: return data
        data=robust_get_json(url, timeout=self.timeout)
        with _CACHE_LOCK:
            _HTTP_CACHE[k]=(time.time(),data)
            if len(_HTTP_CACHE)>100:
                oldest=sorted(_HTTP_CACHE.items(), key=lambda x:x[1][0])[0][0]; _HTTP_CACHE.pop(oldest,None)
        return data
    def _upsert(self,e,date,url,source):
        home=str(e.get('home') or e.get('strHomeTeam') or '').strip(); away=str(e.get('away') or e.get('strAwayTeam') or '').strip(); league=str(e.get('league') or e.get('strLeague') or 'Fútbol internacional').strip()
        if not home or not away: return False
        sd=e.get('source_date') or e.get('strDate'); ts=e.get('timestamp') or e.get('strTimestamp'); resolved=_mx_date_from_iso(ts) if ts else (str(sd)[:10] if sd else None)
        if resolved and resolved!=date: return False
        event_id=e.get('id') or e.get('idEvent') or slug(f'{date}-{league}-{home}-{away}'); mid=f'live:{source}:{date}:{event_id}'
        raw_time=str(e.get('time_mx') or '').strip()[:5]
        if ts:
            try:
                x=dt.datetime.fromisoformat(str(ts).replace('Z','+00:00'))
                if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
                raw_time=x.astimezone(MX).strftime('%H:%M')
            except: pass
        if not raw_time: raw_time=str(e.get('strTimeLocal') or e.get('strTime') or '').strip()[:5]
        status=str(e.get('status') or e.get('strStatus') or '').lower(); hs=e.get('home_score') if 'home_score' in e else e.get('intHomeScore'); aw=e.get('away_score') if 'away_score' in e else e.get('intAwayScore')
        finished=hs is not None and aw is not None and (status in ('match finished','ft','aet','after extra time','finished','final','post','completed','complete') or ('finish' in status) or status in ('status_final','finalizado'))
        region='Americas' if any(x in league.lower() for x in ('mexico','mls','concacaf','america','conmebol','libertadores','sudamericana','leagues cup')) else 'Europe'; country='México' if 'mex' in league.lower() else 'Estados Unidos' if 'mls' in league.lower() else ''
        now=dt.datetime.now().isoformat(timespec='seconds')
        try: self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique ON matches(date, home, away)')
        except: pass
        try: self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique_comp ON matches(date, competition, home, away)')
        except: pass
        for col, typ in [('season','TEXT'),('league','TEXT'),('round','TEXT'),('region','TEXT'),('country','TEXT'),('tier','INTEGER'),('competition_id','TEXT'),('source_type','TEXT'),('data_quality','REAL'),('result_source','TEXT'),('result_source_type','TEXT'),('result_source_url','TEXT'),('result_verified_at','TEXT')]:
            try: self.r.execute(f'ALTER TABLE matches ADD COLUMN {col} {typ}')
            except: pass
        try:
            self.r.execute('''INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url,data_quality,result_source,result_source_type,result_source_url,result_verified_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(date,home,away) DO UPDATE SET time=CASE WHEN excluded.time IS NOT NULL AND excluded.time<>'' THEN excluded.time ELSE matches.time END,
              competition_id=excluded.competition_id,competition=excluded.competition,region=excluded.region,country=excluded.country,
              source=excluded.source,updated_at=excluded.updated_at,source_url=excluded.source_url,data_quality=max(matches.data_quality,excluded.data_quality)''',
              (mid,date,raw_time,slug(league),league,region,country,home,away,int(hs) if hs is not None else None,int(aw) if aw is not None else None,'finished' if finished else 'scheduled',source,now,str(e.get('season') or e.get('strSeason') or ''),url,0.82,source if finished else None,'public_snapshot' if finished else None,url if finished else None,now if finished else None))
        except Exception as ex:
            try:
                self.r.execute('INSERT OR REPLACE INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (mid,date,raw_time,slug(league),league,region,country,home,away,int(hs) if hs is not None else None,int(aw) if aw is not None else None,'finished' if finished else 'scheduled',source,now,str(e.get('season') or ''),url))
            except Exception: raise ex
        return True
    def fetch_espn_all(self,date):
        if _should_skip('ESPN_ALL'): raise RuntimeError('ESPN_ALL skipped circuit breaker')
        ymd=date.replace('-',''); params=urllib.parse.urlencode({'dates':ymd}); urls=[ESPN_ALL_BASE+'?'+params, ESPN_ALL_ALT+'?'+params]
        data=None; url=urls[0]; errs=[]
        for c in urls:
            try: data=self._get_json(c); url=c; _ok('ESPN_ALL'); break
            except Exception as ex: errs.append(f'{c}: {ex!r}'); _fail('ESPN_ALL')
        if data is None: raise RuntimeError('ESPN_ALL unavailable; '+' | '.join(errs))
        out=[]
        for ev in data.get('events') or []:
            comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
            home=next((t for t in teams if t.get('homeAway')=='home'),None); away=next((t for t in teams if t.get('homeAway')=='away'),None)
            if not home or not away: continue
            status=((comp.get('status') or {}).get('type') or {}); league=((comp.get('league') or {}).get('name') or '').strip(); season=ev.get('season') or {}; league=league or str(season.get('slug') or 'Fútbol internacional')
            out.append({'id':ev.get('id'),'home':home.get('team',{}).get('displayName'),'away':away.get('team',{}).get('displayName'),'league':league,'timestamp':ev.get('date'),'status':status.get('name') or status.get('description'),'home_score':home.get('score'),'away_score':away.get('score'),'season':str(season.get('slug') or '')})
        return out,url
    def fetch_espn(self,date,league):
        ymd=date.replace('-',''); url=ESPN_BASE.format(league=urllib.parse.quote(league,safe=''))+'?'+urllib.parse.urlencode({'dates':ymd}); data=self._get_json(url); out=[]
        for ev in data.get('events') or []:
            comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
            home=next((t for t in teams if t.get('homeAway')=='home'),None); away=next((t for t in teams if t.get('homeAway')=='away'),None)
            if not home or not away: continue
            status=((comp.get('status') or {}).get('type') or {})
            out.append({'id':ev.get('id'),'home':home.get('team',{}).get('displayName'),'away':away.get('team',{}).get('displayName'),'league':((ev.get('competitions') or [{}])[0].get('league') or {}).get('name') or league,'timestamp':ev.get('date'),'status':status.get('name') or status.get('description'),'home_score':home.get('score'),'away_score':away.get('score'),'season':str(((ev.get('season') or {}).get('slug') or ''))})
        return out,url
    def sync_day(self,date, fast=False):
        report={'date':date,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[],'coverage_status':'unknown','match_count':0,'primary_source':'ESPN_ALL_FAST' if fast else 'ESPN_ALL','source_counts':{}}
        providers=[]
        if fast:
            try: events,url=self.fetch_espn_all(date); providers.append(('ESPN_ALL',events,url)); report['sources_ok']+=1; report['source_counts']['ESPN_ALL']=len(events)
            except Exception as ex:
                report['failures'].append({'source':'ESPN_ALL','error':str(ex)}); report['source_counts']['ESPN_ALL']=0
                def one(l):
                    try: ev,url=self.fetch_espn(date,l); return ('ESPN',ev,url,None,l)
                    except Exception as ex: return ('ESPN',[],None,str(ex),l)
                with ThreadPoolExecutor(max_workers=5) as pool:
                    fs=[pool.submit(one,l) for l in ESPN_LEAGUES_FAST]
                    for f in as_completed(fs):
                        src,ev,url,err,l=f.result()
                        if err: report['failures'].append({'source':src,'league':l,'error':err})
                        else: report['sources_ok']+=1; providers.append((src,ev,url)); report['source_counts'][f'ESPN:{l}']=len(ev)
        else:
            try: events,url=self.fetch_espn_all(date); providers.append(('ESPN_ALL',events,url)); report['sources_ok']+=1; report['source_counts']['ESPN_ALL']=len(events)
            except Exception as ex: report['failures'].append({'source':'ESPN_ALL','error':str(ex)}); report['source_counts']['ESPN_ALL']=0
        for src,events,url in providers:
            for e in events:
                ts=e.get('timestamp') or e.get('strTimestamp'); sd=_mx_date_from_iso(ts) if ts else (str(e.get('strDate') or '')[:10] or None)
                if sd and sd!=date: report['rejected_wrong_date']+=1; continue
                try:
                    if self._upsert(e,date,url,src): report['accepted']+=1
                except Exception as ex: report['failures'].append({'source':src,'home':e.get('home'),'away':e.get('away'),'error':str(ex)})
        count=self.r.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']; report['match_count']=int(count); report['coverage_status']='complete' if count>0 else 'incomplete'
        return report
    def sync_day_light(self,date): return self.sync_day(date, fast=True)
    def sync_day_light_cached(self,date,force=False):
        self.ensure_cache_schema()
        if not force:
            row=self._cache_key(date)
            if row and row.get('coverage_status')=='complete' and time.time()-float(row['updated_at'])<self.CACHE_TTL:
                return {'date':date,'skipped':True,'reason':'fresh-complete-cache','coverage_status':'complete','match_count':int(row.get('match_count') or 0)}
        try: report=self.sync_day_light(date)
        except Exception as ex: report={'date':date,'accepted':0,'sources_ok':0,'failures':[{'source':'fixture-sync-light','error':str(ex)}],'coverage_status':'incomplete','match_count':0}
        try:self._cache_set(date,report.get('coverage_status','unknown'),report.get('match_count',0))
        except: pass
        return report
    def sync_span_cached(self,start_date,end_date,force=False,light=True):
        import datetime as dt
        start=dt.date.fromisoformat(start_date); end=dt.date.fromisoformat(end_date)
        if end<start: return {'start':start.isoformat(),'end':end.isoformat(),'reports':[],'match_count':0}
        dates=[(start+dt.timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
        fn=self.sync_day_light_cached if light else self.sync_day_cached
        reports=[]
        with ThreadPoolExecutor(max_workers=min(6,len(dates))) as pool:
            futs={pool.submit(fn,d,force):d for d in dates}
            for f in as_completed(futs):
                try: reports.append(f.result())
                except Exception as ex: reports.append({'date':futs[f],'error':str(ex),'match_count':0})
        reports.sort(key=lambda x:x.get('date',''))
        return {'start':start.isoformat(),'end':end.isoformat(),'reports':reports,'match_count':sum(int(r.get('match_count',0) or 0) for r in reports)}
