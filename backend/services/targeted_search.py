"""Targeted live fixture discovery for Match Search.

This module is deliberately a fallback for searches that are not already present in
LiAn's rolling calendar. It resolves each requested team independently through free
public endpoints, then merges the returned schedules by canonical home/away pair.
It never creates a match without an upstream event containing both teams and a date.
"""
from __future__ import annotations
import datetime as dt, json, re, urllib.parse, urllib.request, html, os
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from .http_client import get_json as robust_get_json

MX=ZoneInfo('America/Mexico_City')
TSDB_SEARCH='https://www.thesportsdb.com/api/v1/json/3/searchteams.php'
TSDB_NEXT='https://www.thesportsdb.com/api/v1/json/3/eventsnext.php'
TSDB_LAST='https://www.thesportsdb.com/api/v1/json/3/eventslast.php'
SOFA_SEARCH='https://api.sofascore.com/api/v1/search/all'
SOFA_NEXT='https://api.sofascore.com/api/v1/team/{team_id}/events/next/{page}'
SOFA_PREV='https://api.sofascore.com/api/v1/team/{team_id}/events/last/{page}'
ESPN_LEAGUE='https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard'
ESPN_TEAMS='https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams'
ESPN_TEAM_SCHEDULE='https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/schedule'
ESPN_LEAGUES=('eng.1','esp.1','ger.1','ita.1','fra.1','mex.1','usa.1','eng.league_cup','uefa.champions','uefa.europa','uefa.europa.conf','conmebol.libertadores','conmebol.sudamericana','usa.leagues_cup')
GOOGLE_SEARCH='https://www.google.com/search'
FOTMOB_DAY='https://www.fotmob.com/api/matches'

def norm(s):
    import unicodedata
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

def split_pair(q):
    x=str(q or '').strip()
    parts=re.split(r'\s+(?:vs|v|contra)\s+',x,flags=re.I,maxsplit=1)
    return (parts[0].strip(),parts[1].strip()) if len(parts)==2 and all(parts) else None

def team_eq(actual,wanted):
    a=norm(actual); w=norm(wanted)
    if not a or not w:return False
    def parts(x): return re.sub(r'[^a-z0-9]+',' ',str(x).lower()).split()
    removable={'fc','cf','club','futbol','football','futbolclub','footballclub','sporting','deportivo'}
    def core(x):
        p=parts(x)
        while p and p[0] in removable:p.pop(0)
        while p and p[-1] in removable:p.pop()
        return p
    ap,wp=core(actual),core(wanted)
    if ''.join(ap)==''.join(wp) or a==w:return True
    # Allow common geographic/club descriptors, but never arbitrary substrings.
    descriptors={'laguna','city','united','town','wanderers','rangers','athletic','athletico','real','university','universidad','municipal','central','county','rovers','albion','hotspur'}
    if len(wp)>=1 and len(wp)<=3 and all(x in ap for x in wp):
        extra=[x for x in ap if x not in wp]
        return bool(extra) and all(x in descriptors for x in extra)
    if len(ap)>=1 and len(ap)<=3 and all(x in wp for x in ap):
        extra=[x for x in wp if x not in ap]
        return bool(extra) and all(x in descriptors for x in extra)
    return False

class _GoogleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.buf=[]; self.links=[]; self._href=None
    def handle_starttag(self,tag,attrs):
        if tag=='a': self._href=dict(attrs).get('href')
    def handle_endtag(self,tag):
        if tag=='a' and self._href:
            text=' '.join(self.buf).strip()
            if text:self.links.append((text,self._href))
            self._href=None; self.buf=[]
    def handle_data(self,data):
        if data and data.strip(): self.buf.append(data.strip())

def _google_search_hints(query,today,days=30,timeout=5):
    """Optional Google-like discovery layer.

    Google is a discovery/hint source, never the authority for a fixture. Any candidate
    must still be corroborated by a structured football source before LiAn stores it.
    If GOOGLE_CSE_API_KEY/GOOGLE_CSE_ID are configured, the official JSON API is used;
    otherwise a lightweight public-search request supplies only text hints/links.
    """
    q=str(query or '').strip()
    if not q:return {'ok':False,'source':'GOOGLE','hints':[],'reason':'empty query'}
    api_key=os.getenv('GOOGLE_CSE_API_KEY','').strip(); cse_id=os.getenv('GOOGLE_CSE_ID','').strip()
    hints=[]
    try:
        if api_key and cse_id:
            u='https://www.googleapis.com/customsearch/v1?'+urllib.parse.urlencode({'key':api_key,'cx':cse_id,'q':q+' football fixtures','num':10})
            data=_get(u,timeout); items=data.get('items') or []
            hints=[{'title':x.get('title',''),'snippet':x.get('snippet',''),'link':x.get('link','')} for x in items]
            return {'ok':True,'source':'GOOGLE_CSE','hints':hints[:10],'reason':'configured'}
        u=GOOGLE_SEARCH+'?'+urllib.parse.urlencode({'q':q+' football fixtures '+today.isoformat(),'hl':'en','num':'10'})
        req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36'})
        with urllib.request.urlopen(req,timeout=timeout) as r: raw=r.read().decode('utf-8','ignore')
        parser=_GoogleTextParser(); parser.feed(raw)
        for text,link in parser.links:
            clean=re.sub(r'\s+',' ',html.unescape(text)).strip()
            if len(clean)>=8 and ('google.' not in link.lower()): hints.append({'title':clean[:240],'snippet':clean[:500],'link':link})
        return {'ok':True,'source':'GOOGLE_WEB_HINTS','hints':hints[:10],'reason':'public search hints'}
    except Exception as ex:
        return {'ok':False,'source':'GOOGLE','hints':[],'reason':repr(ex)}

def _get(url,timeout=8):
    """Shared resilient transport; provider failures remain visible to callers."""
    return robust_get_json(url, timeout=timeout)

def _date(ts):
    try:
        x=dt.datetime.fromtimestamp(int(ts),tz=dt.timezone.utc).astimezone(MX)
        return x.date().isoformat(),x.strftime('%H:%M')
    except Exception:return None,''

def _team_candidates(name,timeout=8):
    out=[]
    # TheSportsDB exact-ish search.
    try:
        u=TSDB_SEARCH+'?'+urllib.parse.urlencode({'t':name})
        data=_get(u,timeout); rows=data.get('teams') or []
        for t in rows[:8]:
            out.append(('TSDB',str(t.get('idTeam') or ''),str(t.get('strTeam') or ''),t))
    except Exception: pass
    # SofaScore broad search, independent from the daily endpoint.
    try:
        u=SOFA_SEARCH+'?'+urllib.parse.urlencode({'q':name})
        data=_get(u,timeout)
        for r in data.get('results') or []:
            if r.get('entity',{}).get('type')!='team': continue
            e=r.get('entity') or {}
            out.append(('SOFA',str(e.get('id') or ''),str(e.get('name') or ''),e))
    except Exception: pass
    # ESPN team directory is a structured fallback. This path is deliberately
    # independent from ESPN's global scoreboard and therefore still works when the
    # all-soccer feed omits a competition.
    def one(league):
        try:
            u=ESPN_TEAMS.format(league=league)+'?'+urllib.parse.urlencode({'limit':500})
            data=_get(u,timeout)
            rows=[]
            for sport in data.get('sports') or []:
                for lg in sport.get('leagues') or []:
                    rows.extend(lg.get('teams') or [])
            rows.extend(data.get('teams') or [])
            found=[]
            for item in rows:
                t=item.get('team') if isinstance(item,dict) and isinstance(item.get('team'),dict) else item
                if not isinstance(t,dict): continue
                tid=str(t.get('id') or '')
                tname=str(t.get('displayName') or t.get('name') or t.get('shortDisplayName') or '')
                if tid and tname and team_eq(tname,name): found.append(('ESPN',f'{league}:{tid}',tname,{'league':league,'id':tid,'sport':{'name':'Soccer'}}))
            return found
        except Exception:return []
    from concurrent.futures import ThreadPoolExecutor, as_completed
    try:
        with ThreadPoolExecutor(max_workers=min(8,len(ESPN_LEAGUES))) as pool:
            fs=[pool.submit(one,l) for l in ESPN_LEAGUES]
            for f in as_completed(fs): out.extend(f.result())
    except Exception: pass
    # Prefer exact normalized names, then football entities, then shorter names.
    def quality(row):
        src,tid,tname,e=row; exact=0 if norm(tname)==norm(name) else 1
        sport=str((e.get('sport') or {}).get('name') or '').lower() if isinstance(e,dict) else ''
        football=0 if not sport or sport in ('football','soccer') else 1
        return (exact,football,len(tname),src)
    out.sort(key=quality)
    unique=[]; seen=set()
    for row in out:
        key=(row[0],row[1])
        if key in seen: continue
        seen.add(key); unique.append(row)
    return unique[:24]

def _events_for(source,team_id,timeout=8):
    rows=[]
    if source=='TSDB':
        for base in (TSDB_NEXT,TSDB_LAST):
            try:
                data=_get(base+'?'+urllib.parse.urlencode({'id':team_id}),timeout)
                for e in data.get('events') or []:
                    rows.append({'id':e.get('idEvent'),'home':e.get('strHomeTeam'),'away':e.get('strAwayTeam'),'league':e.get('strLeague'),'date':e.get('dateEvent'),'time':e.get('strTime'),'timestamp':e.get('strTimestamp'),'status':e.get('strStatus') or ''})
            except Exception: pass
    elif source=='SOFA':
        for base in (SOFA_NEXT,SOFA_PREV):
            max_pages=5 if base==SOFA_NEXT else 2
            for page in range(max_pages):
                try:
                    data=_get(base.format(team_id=team_id,page=page),timeout)
                    for e in data.get('events') or []:
                        h=e.get('homeTeam') or {}; a=e.get('awayTeam') or {}; ts=e.get('startTimestamp')
                        d,t=_date(ts)
                        if h.get('name') and a.get('name'):
                            rows.append({'id':e.get('id'),'home':h.get('name'),'away':a.get('name'),'league':((e.get('tournament') or {}).get('name') or 'Fútbol internacional'),'date':d,'time':t,'timestamp':str(ts or ''),'status':((e.get('status') or {}).get('type') or '')})
                except Exception: pass
    elif source=='ESPN':
        try:
            league,tid=str(team_id).split(':',1)
            base=ESPN_TEAM_SCHEDULE.format(league=league,team_id=tid)
            data=_get(base,timeout)
            for ev in data.get('events') or []:
                comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
                h=next((x for x in teams if x.get('homeAway')=='home'),None); a=next((x for x in teams if x.get('homeAway')=='away'),None)
                if not h or not a: continue
                stamp=ev.get('date')
                try:
                    x=dt.datetime.fromisoformat(str(stamp).replace('Z','+00:00')) if stamp else None
                    if x and x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
                    d=x.astimezone(MX).date().isoformat() if x else None; t=x.astimezone(MX).strftime('%H:%M') if x else ''
                except Exception:d=None;t=''
                if d:
                    rows.append({'id':ev.get('id'),'home':(h.get('team') or {}).get('displayName'),'away':(a.get('team') or {}).get('displayName'),'league':((comp.get('league') or {}).get('name') or league),'date':d,'time':t,'timestamp':stamp,'status':(((comp.get('status') or {}).get('type') or {}).get('name') or '')})
        except Exception: pass
    return rows


def _fotmob_events(date, timeout=6):
    """Independent broad daily football discovery from FotMob."""
    url=FOTMOB_DAY+'?'+urllib.parse.urlencode({'date':date.replace('-','')})
    data=_get(url,timeout); out=[]
    for league in data.get('leagues') or []:
        lname=str(league.get('name') or 'Fútbol internacional')
        for e in league.get('matches') or []:
            h=e.get('home') or {}; a=e.get('away') or {}; st=e.get('status') or {}
            if not h.get('name') or not a.get('name'): continue
            stamp=st.get('utcTime') or e.get('utcTime')
            d,t=_date(int(dt.datetime.fromisoformat(str(stamp).replace('Z','+00:00')).timestamp())) if stamp else (date,str(e.get('time') or '')[:5])
            if d != date: continue
            out.append({'id':e.get('id'),'home':h.get('name'),'away':a.get('name'),'league':lname,'date':d,
                        'time':t,'timestamp':stamp,'status':'finished' if st.get('finished') else 'scheduled','source':'FOTMOB'})
    return out,url

def _calendar_events(date, timeout=6):
    """Fetch a broad public calendar for one Mexico date.

    This is intentionally independent of team-search endpoints. Team-search APIs can
    fail or return incomplete identities; the broad calendar still gives us the actual
    fixture with both sides present.
    """
    events=[]
    # SofaScore broad daily calendar
    try:
        data=_get(f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}",timeout)
        for e in data.get('events') or []:
            h=e.get('homeTeam') or {}; a=e.get('awayTeam') or {}
            if not h.get('name') or not a.get('name'): continue
            d,t=_date(e.get('startTimestamp'))
            if d != date: continue
            events.append({'id':e.get('id'),'home':h.get('name'),'away':a.get('name'),
                           'league':((e.get('tournament') or {}).get('name') or 'Fútbol internacional'),
                           'date':d,'time':t,'timestamp':str(e.get('startTimestamp') or ''),
                           'status':((e.get('status') or {}).get('type') or ''), 'source':'SOFA_CALENDAR'})
    except Exception: pass
    # FotMob provides an independent multi-league daily calendar.
    try:
        fot, _ = _fotmob_events(date, timeout)
        events.extend(fot)
    except Exception:
        pass
    # ESPN broad calendar is an independent cross-check.
    try:
        ymd=date.replace('-','')
        data=_get('https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?'+urllib.parse.urlencode({'dates':ymd}),timeout)
        for ev in data.get('events') or []:
            comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
            h=next((x for x in teams if x.get('homeAway')=='home'),None); a=next((x for x in teams if x.get('homeAway')=='away'),None)
            if not h or not a: continue
            d,_=_date(int(dt.datetime.fromisoformat(str(ev.get('date')).replace('Z','+00:00')).timestamp())) if ev.get('date') else (None,'')
            if d != date: continue
            league=((comp.get('league') or {}).get('name') or 'Fútbol internacional')
            events.append({'id':ev.get('id'),'home':(h.get('team') or {}).get('displayName'),'away':(a.get('team') or {}).get('displayName'),
                           'league':league,'date':d,'timestamp':ev.get('date'),'status':(((comp.get('status') or {}).get('type') or {}).get('name') or ''), 'source':'ESPN_CALENDAR'})
    except Exception: pass
    return events

def _calendar_events_range(start_date, end_date, timeout=8):
    """Fetch a multi-day public calendar in one request when the provider supports ranges.

    This is the primary on-demand discovery path. The previous implementation made one
    request per day and silently discarded every network error, which made a healthy
    local cache look like a complete search result. ESPN documents scoreboard date ranges,
    so use the range endpoint first and retain a per-source diagnostic for fallbacks.
    """
    events=[]; diagnostics=[]
    params=urllib.parse.urlencode({'dates':f"{start_date.replace('-','')}-{end_date.replace('-','')}"})
    urls=[
        ('ESPN_ALL_RANGE',f'https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?{params}'),
        ('ESPN_ALL_RANGE_ALT',f'https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?{params}'),
    ]
    for source,url in urls:
        try:
            data=_get(url,timeout)
            count=0
            for ev in data.get('events') or []:
                comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
                h=next((x for x in teams if x.get('homeAway')=='home'),None); a=next((x for x in teams if x.get('homeAway')=='away'),None)
                if not h or not a: continue
                stamp=ev.get('date')
                try:
                    x=dt.datetime.fromisoformat(str(stamp).replace('Z','+00:00')) if stamp else None
                    if x and x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
                    d=x.astimezone(MX).date().isoformat() if x else None
                    t=x.astimezone(MX).strftime('%H:%M') if x else ''
                except Exception:d=None;t=''
                if not d or d<start_date or d>end_date: continue
                league=((comp.get('league') or {}).get('name') or str((ev.get('season') or {}).get('slug') or 'Fútbol internacional'))
                status=((comp.get('status') or {}).get('type') or {})
                events.append({'id':ev.get('id'),'home':(h.get('team') or {}).get('displayName'),'away':(a.get('team') or {}).get('displayName'),
                               'league':league,'date':d,'time':t,'timestamp':stamp,'status':status.get('name') or status.get('description') or '',
                               'source':source})
                count+=1
            diagnostics.append({'source':source,'ok':True,'records':count,'url':url})
        except Exception as ex:
            diagnostics.append({'source':source,'ok':False,'error':repr(ex),'url':url})
    return events,diagnostics

def _espn_league_range(league,start_date,end_date,timeout=8):
    params=urllib.parse.urlencode({'dates':f"{start_date.replace('-', '')}-{end_date.replace('-', '')}"})
    url=ESPN_LEAGUE.format(league=league)+'?'+params
    data=_get(url,timeout); out=[]
    for ev in data.get('events') or []:
        comp=((ev.get('competitions') or [{}])[0]); teams=comp.get('competitors') or []
        h=next((x for x in teams if x.get('homeAway')=='home'),None); a=next((x for x in teams if x.get('homeAway')=='away'),None)
        if not h or not a:continue
        stamp=ev.get('date')
        try:
            x=dt.datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
            if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
            d=x.astimezone(MX).date().isoformat(); t=x.astimezone(MX).strftime('%H:%M')
        except Exception:continue
        if start_date<=d<=end_date:
            status=((comp.get('status') or {}).get('type') or {})
            out.append({'id':ev.get('id'),'home':(h.get('team') or {}).get('displayName'),'away':(a.get('team') or {}).get('displayName'),'league':((comp.get('league') or {}).get('name') or league),'date':d,'time':t,'timestamp':stamp,'status':status.get('name') or status.get('description') or '','source':'ESPN_LEAGUE'})
    return out,{'source':f'ESPN:{league}','ok':True,'records':len(out),'url':url}

def discover_calendar(query, today=None, days=14, timeout=8):
    """Discover current/future fixtures from multiple broad public calendars.

    IMPORTANT: a non-empty ESPN response is NOT treated as globally complete. Different
    competitions can be absent from a provider, so every on-demand team search also
    samples SofaScore's daily football calendar and merges it with ESPN. This is the
    root fix for the previous behaviour where Premier League/selected clubs appeared
    while Liga MX or another competition silently disappeared.
    """
    wanted_pair=split_pair(query)
    today=today or dt.datetime.now(MX).date()
    days=max(1,int(days)); end=today+dt.timedelta(days=days-1)
    events, diagnostics=_calendar_events_range(today.isoformat(),end.isoformat(),timeout)
    dates=[(today+dt.timedelta(days=i)).isoformat() for i in range(days)]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    # Always query the independent daily broad sources, even when ESPN returned data.
    # The merge/dedup layer below decides the canonical event set.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs=[pool.submit(_calendar_events,d,timeout) for d in dates]
        for f in as_completed(futs):
            try:
                batch=f.result(); events.extend(batch)
                diagnostics.append({'source':'DAILY_BROAD','ok':True,'records':len(batch)})
            except Exception as ex:
                diagnostics.append({'source':'DAILY_BROAD','ok':False,'error':repr(ex)})
    found=[]; seen=set()
    for e in events:
        if wanted_pair:
            ph,pa=wanted_pair
            ok=team_eq(e.get('home'),ph) and team_eq(e.get('away'),pa)
        else:
            ok=team_eq(e.get('home'),query) or team_eq(e.get('away'),query)
        if not ok:continue
        key=(e.get('date'),norm(e.get('home')),norm(e.get('away')))
        if key in seen:continue
        seen.add(key); found.append(e)
    found.sort(key=lambda e:(e.get('date',''),e.get('time','')))
    return {'found':bool(found),'candidates':found[:30], 'sources':{'broad_calendar':True,'diagnostics':diagnostics}, 'window_days':days}

def discover_team(query, today=None, days=45, timeout=6):
    """Discover upcoming/recent fixtures for a single team when it is absent locally."""
    wanted=str(query or '').strip()
    if not wanted:
        return {'found':False,'reason':'Equipo vacío.','candidates':[],'sources':{}}
    today=today or dt.datetime.now(MX).date(); days=max(1,min(30,int(days))); end=today+dt.timedelta(days=days-1); start=today-dt.timedelta(days=30)
    sources={}; all_events=[]
    # Direct team discovery is the authoritative path for an arbitrary league. A broad
    # daily calendar is useful as a cross-check, but it must never be the only way to
    # discover a club because broad providers can omit entire competitions.
    teams=_team_candidates(wanted,timeout)
    sources[wanted]={'teams':[x[2] for x in teams], 'candidate_count':len(teams), 'provider_attempted':True}
    # Fetch several identities from independent providers, not merely the first four.
    # The old cap could select one stale/incorrect team identity and hide the rest of a
    # club's schedule. Exact normalized names are preferred before alternate identities.
    def identity_quality(row):
        src,tid,tname,_=row
        return (0 if norm(tname)==norm(wanted) else 1, 0 if src in ('SOFA','ESPN') else 1, len(tname))
    identities=sorted(teams,key=identity_quality)[:8]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    jobs=[]
    with ThreadPoolExecutor(max_workers=min(8,max(1,len(identities)))) as pool:
        for src,tid,tname,meta in identities:
            if tid: jobs.append((src,tname,pool.submit(_events_for,src,tid,timeout)))
        for src,tname,f in jobs:
            try: events=f.result(timeout=max(4,timeout*8))
            except Exception: events=[]
            sources[wanted].setdefault('event_counts',{})[src]=sources[wanted].get('event_counts',{}).get(src,0)+len(events)
            for e in events:
                try:d=dt.date.fromisoformat(str(e.get('date') or '')[:10])
                except Exception: continue
                if start<=d<=end and (team_eq(e.get('home'),wanted) or team_eq(e.get('away'),wanted) or team_eq(e.get('home'),tname) or team_eq(e.get('away'),tname)):
                    all_events.append((src,e))

    # Use the broad calendars as a recovery/cross-check only when team schedules are
    # empty or suspiciously sparse. This avoids 30 daily network calls on every healthy
    # team search while still repairing the exact failure mode where one stale identity
    # exposes only a single fixture.
    if len(all_events) < 2:
        try:
            broad=discover_calendar(wanted,today=today,days=days,timeout=timeout)
            sources[wanted]['broad_crosscheck']=broad.get('sources',{})
            for e in broad.get('candidates') or []:
                all_events.append((e.get('source','BROAD'),e))
        except Exception as ex:
            sources[wanted]['broad_crosscheck_error']=repr(ex)
    found=[]; seen=set()
    for src,e in all_events:
        h,a=norm(e.get('home')),norm(e.get('away')); key=(e.get('date'),h,a)
        if key in seen: continue
        seen.add(key); found.append((e,src))
    found.sort(key=lambda z:(0 if dt.date.fromisoformat(str(z[0].get('date'))[:10])>=today else 1,
                             abs((dt.date.fromisoformat(str(z[0].get('date'))[:10])-today).days),
                             str(z[0].get('date'))))
    if not found:
        google=_google_search_hints(wanted,today,days,timeout=min(5,timeout)); sources['google']=google
    else:
        sources['google']={'ok':False,'source':'GOOGLE','hints':[],'reason':'not needed; structured fixture source already found'}
    return {'found':bool(found),'candidates':[dict(e,source=src) for e,src in found[:30]],'sources':sources}

def discover_pair(query, today=None, days=45, timeout=6):
    pair=split_pair(query)
    if not pair:return {'found':False,'reason':'La búsqueda dirigida requiere formato Equipo A vs Equipo B.','candidates':[],'sources':{}}
    today=today or dt.datetime.now(MX).date(); days=max(1,int(days)); end=today+dt.timedelta(days=days-1)
    names=pair; sources={}; all_events=[]
    from concurrent.futures import ThreadPoolExecutor
    team_jobs=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for wanted in names:
            teams=_team_candidates(wanted,timeout); sources[wanted]={'teams':[x[2] for x in teams]}
            for src,tid,tname,_ in teams[:4]:
                if tid: team_jobs.append((wanted,src,pool.submit(_events_for,src,tid,timeout)))
        for wanted,src,f in team_jobs:
            try: events=f.result(timeout=max(3,timeout*8))
            except Exception: events=[]
            for e in events:
                try:d=dt.date.fromisoformat(str(e.get('date') or '')[:10])
                except Exception:continue
                if today-dt.timedelta(days=30)<=d<=end: all_events.append((src,wanted,e))
    found=[]
    ph,pa=map(norm,names)
    seen=set()
    for src,wanted,e in all_events:
        h,a=norm(e.get('home')),norm(e.get('away'))
        if team_eq(e.get('home'),names[0]) and team_eq(e.get('away'),names[1]):
            key=(e.get('date'),h,a)
            if key in seen:continue
            seen.add(key); found.append((e,src))
    found.sort(key=lambda z:abs((dt.date.fromisoformat(str(z[0]['date'])[:10])-today).days))
    if not found:
        # A pair can be absent from both team schedule endpoints because one provider
        # has a stale team entity. Use the independent broad calendar as a final resolver.
        broad=discover_calendar(query,today=today,days=min(45,max(30,(end-today).days+1)),timeout=timeout)
        sources['broad_fallback']=broad.get('sources',{})
        found=[(e,e.get('source','BROAD')) for e in (broad.get('candidates') or [])]
    return {'found':bool(found),'candidates':[dict(e,source=src) for e,src in found[:30]],'sources':sources}
