"""Strict forward fixture synchronization - COMPLETO Y FIXED.

Rules:
- Mexico City is the canonical calendar date.
- A provider event is accepted only when its own event timestamp/date resolves to the
  requested Mexico date. This prevents Aug-25 fixtures leaking into Aug-26.
- Multiple public providers may contribute; failures never invent fixtures.
- Existing rows are never deleted. New rows are upserted by (date, home, away).
"""
from __future__ import annotations
import datetime as dt, json, re, urllib.parse, urllib.request, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
from .http_client import get_json as robust_get_json, provider_headers

MX=ZoneInfo('America/Mexico_City')
THE_SPORTS_DB='https://www.thesportsdb.com/api/v1/json/3/eventsday.php'
ESPN_BASE='https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard'
ESPN_ALL_BASE='https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
ESPN_ALL_ALT='https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard'
SOFASCORE_DAY='https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}'
FOTMOB_DAY='https://www.fotmob.com/api/matches'
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
    except Exception:return None

class FixtureSync:
    CACHE_TTL=300
    def __init__(self, repo, timeout=10): self.r=repo; self.timeout=timeout

    def bootstrap_seed(self):
        data_dir=Path(__file__).resolve().parents[2] / 'data'
        accepted=0
        for path in sorted(data_dir.glob('fixture_seed_*.json')):
            try: rows=json.loads(path.read_text(encoding='utf-8'))
            except Exception: continue
            if not isinstance(rows,list): continue
            for e in rows:
                try:
                    d=e.get('date') or e.get('strDate')
                    if d and self._upsert(e,str(d)[:10],'bundled://fixture-seed','VerifiedFixtureSeed'): accepted+=1
                except Exception: pass
        return accepted

    def _cache_key(self,date): return self.r.one('SELECT updated_at,coverage_status,match_count FROM fixture_sync_cache WHERE date=?',(date,))

    def _cache_set(self,date,status='unknown',match_count=0):
        try:
            self.r.execute('INSERT INTO fixture_sync_cache(date,updated_at,coverage_status,match_count) VALUES(?,?,?,?) ON CONFLICT(date) DO UPDATE SET updated_at=excluded.updated_at,coverage_status=excluded.coverage_status,match_count=excluded.match_count',(date,time.time(),status,int(match_count)))
        except Exception:
            try:
                self.r.execute('INSERT OR REPLACE INTO fixture_sync_cache(date,updated_at,coverage_status,match_count) VALUES(?,?,?,?)',(date,time.time(),status,int(match_count)))
            except Exception:
                pass

    def ensure_cache_schema(self):
        try:
            self.r.execute("CREATE TABLE IF NOT EXISTS fixture_sync_cache(date TEXT PRIMARY KEY, updated_at REAL NOT NULL, coverage_status TEXT NOT NULL DEFAULT 'unknown', match_count INTEGER NOT NULL DEFAULT 0)")
        except Exception:
            pass
        for col,typ,default in [('coverage_status','TEXT',"'unknown'"),('match_count','INTEGER','0')]:
            try:self.r.execute(f'ALTER TABLE fixture_sync_cache ADD COLUMN {col} {typ} NOT NULL DEFAULT {default}')
            except Exception:pass

    def sync_window_cached(self,start_date,days=30,force=False):
        start=dt.date.fromisoformat(start_date)
        reports=[]
        for i in range(max(1,int(days))):
            d=(start+dt.timedelta(days=i)).isoformat()
            reports.append(self.sync_day_cached(d,force=force))
        return {'start':start.isoformat(),'end':(start+dt.timedelta(days=max(1,int(days))-1)).isoformat(),'reports':reports,'match_count':sum(int(r.get('match_count',0) or 0) for r in reports)}

    def sync_span_cached(self,start_date,end_date,force=False,light=True):
        start=dt.date.fromisoformat(start_date); end=dt.date.fromisoformat(end_date)
        if end < start: return {'start':start.isoformat(),'end':end.isoformat(),'reports':[],'match_count':0}
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

    def sync_day_light_cached(self,date,force=False):
        self.ensure_cache_schema()
        if not force:
            row=self._cache_key(date)
            if row and row.get('coverage_status') == 'complete' and time.time()-float(row['updated_at']) < self.CACHE_TTL:
                return {'date':date,'skipped':True,'reason':'fresh-complete-cache','coverage_status':row.get('coverage_status'),'match_count':int(row.get('match_count') or 0)}
        try: report=self.sync_day_light(date)
        except Exception as ex: report={'date':date,'accepted':0,'sources_ok':0,'failures':[{'source':'fixture-sync-light','error':str(ex)}],'coverage_status':'incomplete','match_count':0}
        try:self._cache_set(date,report.get('coverage_status','unknown'),report.get('match_count',0))
        except Exception:pass
        return report

    def sync_day_light(self,date):
        report={'date':date,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[],
                'coverage_status':'unknown','match_count':0,'primary_source':'ESPN_ALL+SOFASCORE+FOTMOB','source_counts':{}}
        providers=[]
        for name,fn in (('ESPN_ALL',self.fetch_espn_all),('SOFASCORE',self.fetch_sofascore_day),('FOTMOB',self.fetch_fotmob_day),('TheSportsDB',self.fetch_thesportsdb)):
            try:
                events,url=fn(date); providers.append((name,events,url)); report['sources_ok']+=1; report['source_counts'][name]=len(events)
            except Exception as ex:
                report['source_counts'][name]=0; report['failures'].append({'source':name,'error':str(ex)})
        broad_counts=[int(report['source_counts'].get(k,0) or 0) for k in ('ESPN_ALL','SOFASCORE','FOTMOB')]
        broad_ok=sum(1 for k in ('ESPN_ALL','SOFASCORE','FOTMOB') if any(p[0]==k for p in providers))
        if max(broad_counts or [0])==0 and broad_ok>0:
            def recover(league):
                try:
                    ev,url=self.fetch_espn(date,league); return ('ESPN',ev,url,None,league)
                except Exception as ex:
                    return ('ESPN',[],None,repr(ex),league)
            with ThreadPoolExecutor(max_workers=8) as pool:
                fs=[pool.submit(recover,l) for l in ESPN_LEAGUES]
                for f in as_completed(fs):
                    src,ev,url,err,league=f.result()
                    if err:
                        report['failures'].append({'source':src,'league':league,'error':err})
                    else:
                        report['sources_ok']+=1; providers.append((src,ev,url)); report['source_counts'][f'ESPN:{league}']=len(ev)
            report['recovery_mode']='ESPN_LEAGUE_FALLBACK'
        for src,events,url in providers:
            for e in events:
                ts=e.get('timestamp') or e.get('strTimestamp'); sd=_mx_date_from_iso(ts) if ts else (str(e.get('strDate') or '')[:10] or None)
                if sd and sd!=date: report['rejected_wrong_date']+=1; continue
                try:
                    if self._upsert(e,date,url,src): report['accepted']+=1
                except Exception as ex: report['failures'].append({'source':src,'home':e.get('home'),'away':e.get('away'),'error':str(ex)})
        count=self.r.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']; report['match_count']=int(count)
        broad=[int(report['source_counts'].get(k,0) or 0) for k in ('ESPN_ALL','SOFASCORE','FOTMOB')]
        positive=[x for x in broad if x>0]
        if report.get('recovery_mode') == 'ESPN_LEAGUE_FALLBACK' and count>0:
            report['coverage_status']='partial'
        elif len(positive)>=2 and count>0:
            ratio=min(positive)/max(positive)
            report['coverage_status']='complete' if ratio>=0.20 else 'partial'
        elif len(positive)==1 and count>0:
            report['coverage_status']='partial'
        elif len(positive)>=2 and count==0:
            report['coverage_status']='partial' if any(int(report['source_counts'].get(k,0) or 0)>0 for k in report['source_counts'] if str(k).startswith('ESPN:')) else 'incomplete'
        elif report['sources_ok']>=1:
            report['coverage_status']='incomplete'
        else:
            report['coverage_status']='incomplete'
        return report

    def sync_day_cached(self,date,force=False):
        self.ensure_cache_schema()
        if not force:
            row=self._cache_key(date)
            if row and row.get('coverage_status') == 'complete' and time.time()-float(row['updated_at']) < self.CACHE_TTL:
                return {'date':date,'skipped':True,'reason':'fresh-complete-cache','coverage_status':'complete','match_count':int(row.get('match_count') or 0)}
        try: report=self.sync_day(date)
        except Exception as ex: report={'date':date,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[{'source':'fixture-sync','error':str(ex)}]}
        try:self._cache_set(date,report.get('coverage_status','unknown'),report.get('match_count',0))
        except Exception:pass
        return report

    def _get_json(self,url):
        return robust_get_json(url, timeout=self.timeout)

    def _upsert(self,e,date,url,source):
        home=str(e.get('home') or e.get('strHomeTeam') or '').strip()
        away=str(e.get('away') or e.get('strAwayTeam') or '').strip()
        league=str(e.get('league') or e.get('strLeague') or 'Fútbol internacional').strip()
        if not home or not away:return False
        source_date=e.get('source_date') or e.get('strDate')
        timestamp=e.get('timestamp') or e.get('strTimestamp')
        resolved=_mx_date_from_iso(timestamp) if timestamp else (str(source_date)[:10] if source_date else None)
        if resolved and resolved != date:return False
        nh,na=norm_team(home),norm_team(away)
        try:
            existing=self.r.rows('SELECT id,home,away FROM matches WHERE date=?',(date,))
            for row in existing:
                if norm_team(row['home'])==nh and norm_team(row['away'])==na:
                    home,away=row['home'],row['away']
                    break
        except Exception:
            pass
        event_id=e.get('id') or e.get('idEvent') or slug(f'{date}-{league}-{home}-{away}')
        mid=f'live:{source}:{date}:{event_id}'
        raw_time=str(e.get('time_mx') or '').strip()[:5]
        timestamp=e.get('timestamp') or e.get('strTimestamp')
        if timestamp:
            try:
                x=dt.datetime.fromisoformat(str(timestamp).replace('Z','+00:00'))
                if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
                raw_time=x.astimezone(MX).strftime('%H:%M')
            except Exception: pass
        if not raw_time:
            raw_time=str(e.get('strTimeLocal') or e.get('strTime') or '').strip()[:5]
        status=str(e.get('status') or e.get('strStatus') or '').lower()
        hs=e.get('home_score') if 'home_score' in e else e.get('intHomeScore')
        aw=e.get('away_score') if 'away_score' in e else e.get('intAwayScore')
        finished=hs is not None and aw is not None and (status in ('match finished','ft','aet','after extra time','finished','final','post','completed','complete') or ('finish' in status) or status in ('status_final','finalizado'))
        region='Americas' if any(x in league.lower() for x in ('mexico','mls','concacaf','america','conmebol','libertadores','sudamericana','leagues cup')) else 'Europe' if any(x in league.lower() for x in ('uefa','england','spain','italy','germany','france','scotland','portugal')) else 'World'
        country='México' if 'mex' in league.lower() else 'Estados Unidos' if 'mls' in league.lower() else ''
        now=dt.datetime.now().isoformat(timespec='seconds')
        # FIX CRÍTICO: Crear índices únicos si no existen
        try:
            self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique ON matches(date, home, away)')
        except Exception:
            pass
        try:
            self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique_comp ON matches(date, competition, home, away)')
        except Exception:
            pass
        # Crear columnas faltantes si no existen
        for col, typ in [('season','TEXT'),('league','TEXT'),('round','TEXT'),('region','TEXT'),('country','TEXT'),('tier','INTEGER'),('competition_id','TEXT'),('source_type','TEXT'),('data_quality','REAL'),('result_source','TEXT'),('result_source_type','TEXT'),('result_source_url','TEXT'),('result_verified_at','TEXT')]:
            try:
                self.r.execute(f'ALTER TABLE matches ADD COLUMN {col} {typ}')
            except Exception:
                pass
        try:
            self.r.execute('''INSERT INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url,data_quality,result_source,result_source_type,result_source_url,result_verified_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(date,home,away) DO UPDATE SET time=CASE WHEN excluded.time IS NOT NULL AND excluded.time<>'' THEN excluded.time ELSE matches.time END,
              competition_id=excluded.competition_id,competition=excluded.competition,region=excluded.region,country=excluded.country,
              source=excluded.source,updated_at=excluded.updated_at,source_url=excluded.source_url,data_quality=max(matches.data_quality,excluded.data_quality),
              home_score=CASE WHEN excluded.status='finished' THEN excluded.home_score ELSE matches.home_score END,
              away_score=CASE WHEN excluded.status='finished' THEN excluded.away_score ELSE matches.away_score END,
              status=CASE WHEN excluded.status='finished' THEN 'finished' ELSE matches.status END,
              result_source=CASE WHEN excluded.status='finished' THEN excluded.source ELSE matches.result_source END,
              result_source_type=CASE WHEN excluded.status='finished' THEN 'public_snapshot' ELSE matches.result_source_type END,
              result_source_url=CASE WHEN excluded.status='finished' THEN excluded.source_url ELSE matches.result_source_url END,
              result_verified_at=CASE WHEN excluded.status='finished' THEN excluded.updated_at ELSE matches.result_verified_at END''',
              (mid,date,raw_time,slug(league),league,region,country,home,away,int(hs) if hs is not None else None,int(aw) if aw is not None else None,
               'finished' if finished else 'scheduled',source,now,str(e.get('season') or e.get('strSeason') or ''),url,0.82 if source=='ESPN' else 0.72,source if finished else None,'public_snapshot' if finished else None,url if finished else None,now if finished else None))
        except Exception as ex:
            if 'ON CONFLICT' in str(ex) or 'no column' in str(ex).lower():
                try:
                    self.r.execute('INSERT OR REPLACE INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (mid,date,raw_time,slug(league),league,region,country,home,away,int(hs) if hs is not None else None,int(aw) if aw is not None else None,'finished' if finished else 'scheduled',source,now,str(e.get('season') or ''),url))
                    return True
                except Exception:
                    raise ex
            raise
        return True

    def fetch_fotmob_day(self,date):
        urls=[FOTMOB_DAY+'?'+urllib.parse.urlencode({'date':date.replace('-','')}),
              FOTMOB_DAY+'?'+urllib.parse.urlencode({'date':date})]
        data=None; url=urls[0]; errors=[]
        for candidate in urls:
            try:
                data=self._get_json(candidate); url=candidate; break
            except Exception as ex:
                errors.append(f'{candidate}: {ex!r}')
        if data is None:
            raise RuntimeError('FOTMOB unavailable; '+' | '.join(errors))
        out=[]
        for league in data.get('leagues') or []:
            lname=str(league.get('name') or league.get('league',{}).get('name') or 'Fútbol internacional')
            for e in league.get('matches') or []:
                h=e.get('home') or {}; a=e.get('away') or {}; status=e.get('status') or {}
                if not h.get('name') or not a.get('name'): continue
                stamp=status.get('utcTime') or e.get('utcTime')
                out.append({'id':e.get('id'),'home':h.get('name'),'away':a.get('name'),'league':lname,
                            'strDate':date,'timestamp':stamp,'time_mx':e.get('time') or '',
                            'status':'finished' if status.get('finished') else 'scheduled',
                            'home_score':h.get('score'),'away_score':a.get('score'),
                            'season':str(e.get('season') or '')})
        return out,url

    def fetch_thesportsdb(self,date):
        url=THE_SPORTS_DB+'?'+urllib.parse.urlencode({'d':date,'s':'Soccer'})
        data=self._get_json(url); out=[]
        for e in data.get('events') or []:
            out.append({'id':e.get('idEvent'),'home':e.get('strHomeTeam'),'away':e.get('strAwayTeam'),'league':e.get('strLeague'),
                        'strDate':e.get('strDate'),'strTimestamp':e.get('strTimestamp'),'strTime':e.get('strTime'),
                        'strTimeLocal':e.get('strTimeLocal'),'intHomeScore':e.get('intHomeScore'),'intAwayScore':e.get('intAwayScore'),
                        'strStatus':e.get('strStatus'),'strSeason':e.get('strSeason')})
        return out,url

    def fetch_espn_all(self,date):
        ymd=date.replace('-','')
        params=urllib.parse.urlencode({'dates':ymd})
        urls=[ESPN_ALL_BASE+'?'+params, ESPN_ALL_ALT+'?'+params]
        data=None; url=urls[0]; errors=[]
        for candidate in urls:
            try:
                data=self._get_json(candidate); url=candidate; break
            except Exception as ex: errors.append(f'{candidate}: {ex!r}')
        if data is None: raise RuntimeError('ESPN_ALL unavailable; '+ ' | '.join(errors))
        out=[]
        for ev in data.get('events') or []:
            comp=((ev.get('competitions') or [{}])[0])
            teams=comp.get('competitors') or []
            home=next((t for t in teams if t.get('homeAway')=='home'),None)
            away=next((t for t in teams if t.get('homeAway')=='away'),None)
            if not home or not away:continue
            status=((comp.get('status') or {}).get('type') or {})
            league=((comp.get('league') or {}).get('name') or '').strip()
            season=ev.get('season') or {}
            league=league or str(season.get('slug') or 'Fútbol internacional')
            out.append({'id':ev.get('id'),'home':home.get('team',{}).get('displayName'),'away':away.get('team',{}).get('displayName'),
                        'league':league,'timestamp':ev.get('date'),'status':status.get('name') or status.get('description'),
                        'home_score':home.get('score'),'away_score':away.get('score'),'season':str(season.get('slug') or '')})
        return out,url

    def fetch_sofascore_day(self,date):
        urls=[SOFASCORE_DAY.format(date=date), f'https://www.sofascore.com/api/v1/sport/football/scheduled-events/{date}']
        data=None; url=urls[0]; errors=[]
        for candidate in urls:
            try:
                data=self._get_json(candidate); url=candidate; break
            except Exception as ex: errors.append(f'{candidate}: {ex!r}')
        if data is None: raise RuntimeError('SOFASCORE unavailable; '+ ' | '.join(errors))
        out=[]
        for ev in data.get('events') or []:
            home=ev.get('homeTeam') or {}; away=ev.get('awayTeam') or {}
            if not home.get('name') or not away.get('name'): continue
            ts=ev.get('startTimestamp')
            timestamp=dt.datetime.fromtimestamp(int(ts),tz=dt.timezone.utc).isoformat().replace('+00:00','Z') if ts else ''
            status=ev.get('status') or {}; tournament=ev.get('tournament') or {}
            league=tournament.get('name') or ((tournament.get('uniqueTournament') or {}).get('name')) or 'Fútbol internacional'
            out.append({'id':ev.get('id'),'home':home.get('name'),'away':away.get('name'),'league':league,
                        'timestamp':timestamp,'status':status.get('type') or status.get('description') or '',
                        'home_score':(ev.get('homeScore') or {}).get('current'),'away_score':(ev.get('awayScore') or {}).get('current'),
                        'season':str(((tournament.get('season') or {}).get('name')) or '')})
        return out,url

    def fetch_espn(self,date,league):
        ymd=date.replace('-','')
        url=ESPN_BASE.format(league=urllib.parse.quote(league,safe=''))+'?'+urllib.parse.urlencode({'dates':ymd})
        data=self._get_json(url); out=[]
        for ev in data.get('events') or []:
            comp=((ev.get('competitions') or [{}])[0])
            teams=comp.get('competitors') or []
            home=next((t for t in teams if t.get('homeAway')=='home'),None)
            away=next((t for t in teams if t.get('homeAway')=='away'),None)
            if not home or not away:continue
            status=((comp.get('status') or {}).get('type') or {})
            out.append({'id':ev.get('id'),'home':home.get('team',{}).get('displayName'),'away':away.get('team',{}).get('displayName'),
                        'league':((ev.get('competitions') or [{}])[0].get('league') or {}).get('name') or league,
                        'timestamp':ev.get('date'),'status':status.get('name') or status.get('description'),
                        'home_score':home.get('score'),'away_score':away.get('score'),'season':str(((ev.get('season') or {}).get('slug') or ''))})
        return out,url

    def sync_day(self,date):
        report={'date':date,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[],
                'coverage_status':'unknown','match_count':0,'primary_source':'ESPN_ALL','source_counts':{}}
        providers=[]
        try:
            events,url=self.fetch_espn_all(date); providers.append(('ESPN_ALL',events,url)); report['sources_ok']+=1; report['source_counts']['ESPN_ALL']=len(events)
        except Exception as ex:
            report['failures'].append({'source':'ESPN_ALL','error':str(ex)}); report['source_counts']['ESPN_ALL']=0
        try:
            events,url=self.fetch_sofascore_day(date); providers.append(('SOFASCORE',events,url)); report['sources_ok']+=1; report['source_counts']['SOFASCORE']=len(events)
        except Exception as ex:
            report['failures'].append({'source':'SOFASCORE','error':str(ex)}); report['source_counts']['SOFASCORE']=0
        try:
            events,url=self.fetch_fotmob_day(date); providers.append(('FOTMOB',events,url)); report['sources_ok']+=1; report['source_counts']['FOTMOB']=len(events)
        except Exception as ex:
            report['failures'].append({'source':'FOTMOB','error':str(ex)}); report['source_counts']['FOTMOB']=0
        def one(l):
            try:
                ev,url=self.fetch_espn(date,l); return ('ESPN',ev,url,None,l)
            except Exception as ex:return ('ESPN',[],None,str(ex),l)
        with ThreadPoolExecutor(max_workers=8) as pool:
            fs=[pool.submit(one,l) for l in ESPN_LEAGUES]
            for f in as_completed(fs):
                src,ev,url,err,l=f.result()
                if err: report['failures'].append({'source':src,'league':l,'error':err})
                else: report['sources_ok']+=1; providers.append((src,ev,url)); report['source_counts'][f'ESPN:{l}']=len(ev)
        try:
            events,url=self.fetch_thesportsdb(date); providers.append(('TheSportsDB',events,url)); report['sources_ok']+=1; report['source_counts']['TheSportsDB']=len(events)
        except Exception as ex:
            report['failures'].append({'source':'TheSportsDB','error':str(ex)}); report['source_counts']['TheSportsDB']=0
        for src,events,url in providers:
            for e in events:
                ts=e.get('timestamp') or e.get('strTimestamp')
                sd=_mx_date_from_iso(ts) if ts else (str(e.get('strDate') or '')[:10] or None)
                if sd and sd!=date: report['rejected_wrong_date']+=1; continue
                try:
                    if self._upsert(e,date,url,src): report['accepted']+=1
                except Exception as ex: report['failures'].append({'source':src,'home':e.get('home'),'away':e.get('away'),'error':str(ex)})
        count=self.r.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']
        report['match_count']=int(count)
        report['local_after_sync']=int(count)
        broad=[int(report['source_counts'].get(k,0) or 0) for k in ('ESPN_ALL','SOFASCORE','FOTMOB')]
        positive=[x for x in broad if x>0]
        if report.get('recovery_mode') == 'ESPN_LEAGUE_FALLBACK' and count>0:
            report['coverage_status']='partial'
        elif len(positive)>=2 and count>0:
            ratio=min(positive)/max(positive)
            report['coverage_status']='complete' if ratio>=0.20 else 'partial'
        elif len(positive)==1 and count>0:
            report['coverage_status']='partial'
        elif len(positive)>=2 and count==0:
            report['coverage_status']='incomplete'
        else:
            report['coverage_status']='incomplete'
        if report['sources_ok']==0 and count>0:
            report['coverage_status']='local-fallback'
            report['fallback']='existing local fixtures retained; no provider data accepted'
        report['broad_sources']={'ESPN_ALL':broad[0],'SOFASCORE':broad[1],'FOTMOB':broad[2]}
        report['primary_source']='ESPN_ALL+SOFASCORE+FOTMOB'
        report['free_tier_note']='TheSportsDB eventsday free tier may cap results; it is never used as the completeness authority.'
        return report

    def sync_window(self,start_date,days=30):
        start=dt.date.fromisoformat(start_date)
        dates=[(start+dt.timedelta(days=i)).isoformat() for i in range(days)]
        report={'start':start_date,'end':dates[-1],'days':days,'accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[]}
        self.ensure_cache_schema()
        with ThreadPoolExecutor(max_workers=min(4,days)) as pool:
            fs=[pool.submit(self.sync_day_cached,d) for d in dates]
            for f in as_completed(fs):
                try: r=f.result()
                except Exception as ex: r={'date':'?','accepted':0,'rejected_wrong_date':0,'sources_ok':0,'failures':[{'source':'fixture-sync','error':str(ex)}]}
                report['accepted']+=r.get('accepted',0); report['rejected_wrong_date']+=r.get('rejected_wrong_date',0); report['sources_ok']+=r.get('sources_ok',0); report['failures'].extend(r.get('failures',[]))
        return report
