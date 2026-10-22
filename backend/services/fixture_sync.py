"""Strict forward fixture synchronization - FIXED ON CONFLICT

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
            # Fallback if no unique constraint
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

    # ... resto de métodos igual, solo _upsert corregido ...
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
        # FIX: Asegurar índices únicos existen antes de insertar
        try:
            self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique ON matches(date, home, away)')
        except Exception:
            pass
        try:
            self.r.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique_comp ON matches(date, competition, home, away)')
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
            # Fallback: si aún falla ON CONFLICT, usa INSERT OR REPLACE por id
            if 'ON CONFLICT' in str(ex):
                try:
                    self.r.execute('INSERT OR REPLACE INTO matches(id,date,time,competition_id,competition,region,country,home,away,home_score,away_score,status,source,updated_at,season,source_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (mid,date,raw_time,slug(league),league,region,country,home,away,int(hs) if hs is not None else None,int(aw) if aw is not None else None,'finished' if finished else 'scheduled',source,now,str(e.get('season') or ''),url))
                    return True
                except Exception:
                    raise ex
            raise
        return True

    # Para que no falle el import, mantenemos los métodos restantes con un wrapper simple que llama al original si existe
    # Si tu archivo original tenía más métodos, copia el resto de tu archivo aquí abajo - este archivo solo arregla _upsert
    def __getattr__(self, name):
        # Esto permite que si falta algún método, no crashee el import - pero idealmente copia tu archivo completo y solo reemplaza _upsert
        raise AttributeError(f"Method {name} not in fixed version - copia tu fixture_sync.py original y solo reemplaza _upsert con este")

# NOTA: Este archivo es SOLO el fix de _upsert. 
# Para arreglar rápido, abre tu backend/services/fixture_sync.py y REEMPLAZA solo la función _upsert por la de arriba.
# O si quieres, usa este archivo completo y luego copia los demás métodos de tu archivo original debajo.
