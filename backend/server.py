import json
import urllib.parse
import os
import datetime as dt
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .data.repo import Repo
from .services.calendar import matches, raw_matches, competitions
from .services.top import top
from .services.combo import build
from .services.progol import generate, generate_contest
from .services.intel import study, search_matches
from .services.universal import canonical, data_health
from .learning.adaptive import Adaptive
from .learning.adaptive_engine import AdaptiveLearningEngine
from .learning.adaptive_calibration import AdaptiveCalibration
from .data.status import DataStatus
from .data.historical import HistoricalSync
from .data.feature_store import FeatureStore
from .core.model import Model
from .data.evidence import EvidenceEngine
from .learning.error_learning import ErrorLearning
from .learning.backtest import BacktestEngine
from .learning.benchmark import ProfessionalBenchmark
from .learning.error_intelligence import ErrorIntelligence
from .learning.error_fingerprint import ErrorFingerprint
from .learning.contextual_intelligence import ContextualIntelligence
from .learning.live_context import LiveContextEngine
from .services.results_sync import ResultsSync
from .services.fixture_sync import FixtureSync
from .services.background import BackgroundEngine
from .services.catchup import CatchUpEngine
from .services.historical_replay import HistoricalReplay
from .services.source_manager import SourceManager
from .services.timezone import MX, mexico_time
from .services.calendar_clock import mexico_today_iso
from .learning.professional_engine import ProfessionalEngine
from .services.match_lifecycle import enrich as enrich_lifecycle
from .services.historical_master import HistoricalMaster
from .learning.promotion_gate import PromotionGate

ROOT = Path(__file__).resolve().parent
REPO_PATH = ROOT / 'data' / 'lian.db'
repo = Repo(REPO_PATH)
VERSION = '64.6.0'
PORT = int(os.getenv('LIAN_PORT', '8010'))

class LianHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def predictions_for(repo, date, allow_persist=True, fast=False):
    out = []
    model = Model(repo)
    ev = EvidenceEngine(repo)
    fingerprint = ErrorFingerprint(repo)
    raw = raw_matches(repo, date)
    # FAST MODE: si fast=True, solo devuelve raw sin calcular modelo pesado
    if fast:
        for m in raw:
            mt = mexico_time(m)
            p = dict(m)
            p['time_mx'] = mt.get('time_mx')
            p['date_mx'] = mt.get('date_mx')
            p['time_status_mx'] = mt.get('status')
            p['prediction_fast'] = True
            p = enrich_lifecycle(p)
            out.append(p)
        return out

    for m in raw:
        stored = repo.one('SELECT * FROM predictions WHERE match_id=? ORDER BY generated_at ASC LIMIT 1', (m['id'],))
        if m.get('status') == 'finished':
            if stored:
                p = dict(m, **model.predict(m))
                p['probabilities'] = {'1': stored['p_home'], 'X': stored['p_draw'], '2': stored['p_away']}
                p['pick'] = stored['pick']; p['confidence'] = stored['confidence']; p['evidence'] = stored['evidence']
                p['model_version'] = stored['model_version']; p['expected_goals']['total'] = stored['expected_goals']
                p['pre_match_prediction'] = True; p['prediction_source'] = 'IMMUTABLE_PRE_MATCH_RECORD'
            else:
                p = dict(m, **model.predict(m)); p['pre_match_prediction'] = False; p['prediction_source'] = 'RETROSPECTIVE_RECONSTRUCTION'
                p['retrospective_warning'] = 'No existía una predicción prepartido almacenada'
        else:
            freeze = False
            if stored:
                try:
                    now_mx = dt.datetime.now(MX)
                    kickoff = str(m.get('time') or m.get('time_mx') or '')[:5]
                    if str(m.get('date'))[:10] < now_mx.date().isoformat(): freeze = True
                    elif str(m.get('date'))[:10] == now_mx.date().isoformat() and len(kickoff) == 5:
                        hh, mm = map(int, kickoff.split(':')); freeze = (hh*60+mm) <= (now_mx.hour*60+now_mx.minute)
                except: pass
            if stored and freeze:
                pred = model.predict(m); p = dict(m, **pred)
                p['probabilities'] = {'1': stored['p_home'], 'X': stored['p_draw'], '2': stored['p_away']}
                p['pick'] = stored['pick']; p['confidence'] = stored['confidence']; p['evidence'] = stored['evidence']
                p['model_version'] = stored['model_version']; p['expected_goals']['total'] = stored['expected_goals']
                p['pre_match_prediction'] = True; p['prediction_source'] = 'IMMUTABLE_PRE_MATCH_RECORD'
            else:
                pred = model.predict(m); p = dict(m, **pred); p['pre_match_prediction'] = True; p['prediction_source'] = 'CURRENT_MODEL'
                if allow_persist:
                    try:
                        ev.save(m, p)
                        repo.execute('INSERT OR REPLACE INTO predictions(match_id,p_home,p_draw,p_away,pick,confidence,evidence,uncertainty,expected_goals,rationale,model_version,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',
                            (m['id'], pred['probabilities']['1'], pred['probabilities']['X'], pred['probabilities']['2'], pred['pick'], pred['confidence'], pred['evidence'], 1-pred['confidence'], pred['expected_goals']['total'], pred['rationale'], pred['model_version']))
                    except: pass
        mt = mexico_time(m); p['time_mx'] = mt.get('time_mx'); p['date_mx'] = mt.get('date_mx'); p['time_status_mx'] = mt.get('status')
        try: p['error_fingerprint'] = fingerprint.assess(m, p)
        except: p['error_fingerprint'] = {'level': 'NO DISPONIBLE', 'message': 'No se pudo calcular fingerprint'}
        p = enrich_lifecycle(p)
        if m.get('status') == 'finished':
            p['result'] = {'final': f"{m.get('home_score')}–{m.get('away_score')}", 'source': m.get('result_source'), 'source_type': m.get('result_source_type'), 'source_url': m.get('result_source_url'), 'verified_at': m.get('result_verified_at')}
            if m.get('home_score') is not None and m.get('away_score') is not None:
                actual = '1' if int(m['home_score']) > int(m['away_score']) else 'X' if int(m['home_score']) == int(m['away_score']) else '2'
                p['result']['actual'] = actual; p['result']['prediction'] = p['pick']; p['result']['correct'] = (p['pick']==actual); p['result']['eligible_for_metrics'] = bool(p['pre_match_prediction'])
                p['result']['evaluation_status'] = 'PRE_MATCH_VERIFIED' if p['pre_match_prediction'] else 'RETROSPECTIVE_DISPLAY_ONLY'
                review = repo.one('SELECT * FROM postmatch_reviews WHERE match_id=?', (m['id'],))
                if review: p['postmatch_review'] = review
        out.append(p)
    return out

def fixture_key(m):
    from .services.targeted_search import norm
    d = str(m.get('date') or '')[:10]; t = str(m.get('time') or m.get('time_mx') or '')[:5]
    try: date = dt.date.fromisoformat(d)
    except: return (d, norm(m.get('home')), norm(m.get('away')), t)
    mins = None
    try: hh, mm = map(int, t.split(':')); mins = hh*60+mm
    except: pass
    if mins is not None and mins < 6*60:
        total = mins-6*60; date = date + dt.timedelta(days=-1 if total<0 else 0); total %= 24*60; t = f'{total//60:02d}:{total%60:02d}'
    def team_identity(value):
        import unicodedata, re
        raw = unicodedata.normalize('NFKD', str(value or '')).encode('ascii','ignore').decode().lower()
        parts = re.sub(r'[^a-z0-9]+',' ',raw).split()
        removable = {'fc','cf','club','futbol','football','futbolclub','footballclub','laguna'}
        return ''.join(x for x in parts if x not in removable)
    return (date.isoformat(), team_identity(m.get('home')), team_identity(m.get('away')))

def dedup_fixtures(rows):
    seen = {}; out = []
    for m in rows or []:
        key = fixture_key(m)
        if key in seen:
            i = seen[key]; old = out[i]
            score = lambda x: (bool(x.get('time')), bool(x.get('competition')), bool(x.get('source_url')), float(x.get('data_quality') or 0))
            if score(m) > score(old): out[i] = m
            continue
        seen[key] = len(out); out.append(m)
    return out

def needs_targeted_discovery(term, result, today):
    import re
    term = str(term or '').strip()
    if not term: return False
    pair = re.split(r'\s+(?:vs|v|contra)\s+', term, maxsplit=1, flags=re.I)
    is_pair = len(pair)==2 and all(x.strip() for x in pair)
    candidates = result.get('candidates') or ([result.get('match')] if result.get('found') else [])
    if is_pair:
        if result.get('found') and not result.get('ambiguous'): return False
        return True
    for m in candidates:
        try:
            if dt.date.fromisoformat(str(m.get('date',''))[:10]) >= today: return False
        except: continue
    return True

def universal_search(repo, term, mid=None):
    term = str(term or '').strip(); mid = str(mid or '').strip() or None; refresh = None; targeted = None
    if not term: return {'found': False, 'query': term, 'reason': 'Escribe un equipo o partido.'}
    if mid: return canonical(repo, term, mid)
    today = dt.datetime.now(MX).date()
    pair = __import__('backend.services.targeted_search', fromlist=['split_pair']).split_pair(term)
    is_single = pair is None
    local = canonical(repo, term, None)
    from .services.targeted_search import discover_pair, discover_team, discover_calendar
    def _local_window(rows, max_days=30):
        out = []; end = today+dt.timedelta(days=max_days)
        for m in rows or []:
            try:
                d = dt.date.fromisoformat(str(m.get('date',''))[:10])
                if today <= d <= end: out.append(m)
            except: pass
        return out
    local_window = _local_window(local.get('candidates') if isinstance(local, dict) else [], 30)
    targeted = None
    if os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')=='1':
        if local_window:
            local_window.sort(key=lambda m: (str(m.get('date','')), str(m.get('time','')), str(m.get('competition',''))))
            selected = None
            if len(local_window)==1:
                try: selected = canonical(repo, term, local_window[0].get('id')).get('match')
                except: selected = None
                if selected is not None: local_window[0]=selected
            return {'found': True, 'query': term, 'ambiguous': len(local_window)>1, 'reason': 'Partidos actuales/futuros disponibles en índice local; descubrimiento vivo deshabilitado.', 'candidates': local_window[:30], 'match': selected if selected is not None else (local_window[0] if len(local_window)==1 else None), 'refresh': None, 'calendar_context': {'today_mx': today.isoformat(), 'window_days':30, 'live_enabled': False}}
        historical = [m for m in (local.get('candidates') or []) if str(m.get('date',''))[:10] < today.isoformat()]
        return {'found': False, 'query': term, 'reason': 'No se encontró partido actual/futuro y búsqueda viva deshabilitada.', 'historical_candidates': historical[:8], 'refresh': None, 'calendar_context': {'today_mx': today.isoformat(), 'live_enabled': False}}
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            if is_single:
                f1 = pool.submit(discover_team, term, today, 30, 4); f2 = pool.submit(discover_calendar, term, today, 30, 4)
            else:
                f1 = pool.submit(discover_pair, term, today, 30, 4); f2 = pool.submit(discover_calendar, term, today, 30, 4)
            a = f1.result(timeout=28); b = f2.result(timeout=28)
        candidates = (a.get('candidates') or []) + (b.get('candidates') or []); merged = dedup_fixtures(candidates)
        if is_single:
            merged = [e for e in merged if dt.date.fromisoformat(str(e.get('date',''))[:10]) >= today and (__import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(e.get('home'), term) or __import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(e.get('away'), term))]
        else:
            ph, pa = pair
            merged = [e for e in merged if __import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(e.get('home'), ph) and __import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(e.get('away'), pa)]
        merged.sort(key=lambda e: (str(e.get('date','')), str(e.get('time','')), str(e.get('competition',''))))
        targeted = {'found': bool(merged), 'candidates': merged[:30], 'sources': {'primary': a.get('sources', {}), 'secondary': b.get('sources', {})}}
    except Exception as ex:
        targeted = {'found': False, 'error': str(ex), 'candidates': [], 'sources': {}}
    if os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')!='1':
        try: refresh = FixtureSync(repo).sync_span_cached(today.isoformat(), (today+dt.timedelta(days=2)).isoformat(), force=False, light=True)
        except Exception as ex: refresh = {'error': str(ex), 'start': today.isoformat(), 'window_days':30}
    discovered = []
    for e in (targeted or {}).get('candidates') or []:
        try:
            d = str(e.get('date') or '')[:10]
            if not d or dt.date.fromisoformat(d) < today: continue
            FixtureSync(repo)._upsert(e, d, str(e.get('source') or 'targeted'), str(e.get('source') or 'TARGETED'))
            discovered.append(e)
        except: continue
    if discovered: local = canonical(repo, term, None)
    local_candidates = list(local_window)
    if is_single:
        candidates = []
        for m in local_candidates+discovered:
            try:
                d = str(m.get('date') or '')[:10]
                if not d or dt.date.fromisoformat(d) < today: continue
            except: continue
            if not (__import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(m.get('home'), term) or __import__('backend.services.targeted_search', fromlist=['team_eq']).team_eq(m.get('away'), term)): continue
            key = fixture_key(m)
            if any(fixture_key(existing)==key for existing in candidates): continue
            candidates.append(m)
        candidates.sort(key=lambda m: (str(m.get('date','')), str(m.get('time','')), str(m.get('competition',''))))
        if candidates:
            selected = None
            if len(candidates)==1:
                try: selected = canonical(repo, term, candidates[0].get('id')).get('match')
                except: selected = None
                if selected is not None: candidates[0]=selected
            return {'found': True, 'query': term, 'ambiguous': len(candidates)>1, 'reason': 'Se encontraron partidos actuales/futuros para el equipo.' if len(candidates)>1 else '', 'candidates': candidates[:30], 'match': selected if selected is not None else (candidates[0] if len(candidates)==1 else None), 'refresh': refresh, 'targeted_search': targeted, 'calendar_context': {'today_mx': today.isoformat(), 'window_days':30, 'window_start': today.isoformat(), 'window_end': (today+dt.timedelta(days=29)).isoformat(), 'automatic_refresh': bool(refresh)}}
        historical = [m for m in (local.get('candidates') or []) if str(m.get('date',''))[:10] < today.isoformat()]
        return {'found': False, 'query': term, 'reason': 'No se encontró partido actual/futuro relacionado.', 'historical_candidates': historical[:8], 'refresh': refresh, 'targeted_discovery': targeted, 'calendar_context': {'today_mx': today.isoformat(), 'window_days':30, 'window_start': today.isoformat(), 'window_end': (today+dt.timedelta(days=29)).isoformat(), 'automatic_refresh': bool(refresh)}}
    result = local
    if result.get('found'):
        result['refresh']=refresh; result['targeted_search']=targeted; result['calendar_context']={'today_mx': today.isoformat(), 'window_days':30, 'window_start': today.isoformat(), 'window_end': (today+dt.timedelta(days=29)).isoformat(), 'automatic_refresh': bool(refresh)}
        return result
    historical = []
    for m in (local.get('candidates') or []):
        try:
            if dt.date.fromisoformat(str(m.get('date',''))[:10]) < today: historical.append(m)
        except: pass
    return {'found': False, 'query': term, 'reason': 'No se encontró partido actual/futuro.', 'historical_candidates': historical[:8], 'targeted_discovery': targeted, 'refresh': refresh, 'calendar_context': {'today_mx': today.isoformat(), 'window_days':30, 'window_start': today.isoformat(), 'window_end': (today+dt.timedelta(days=29)).isoformat(), 'automatic_refresh': bool(refresh)}}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Max-Age','86400'); self.end_headers()
    def send(self, obj, status=200):
        def _json_default(value):
            try:
                if hasattr(value,'item'): return value.item()
            except: pass
            if isinstance(value, set): return list(value)
            return str(value)
        b = json.dumps(obj, ensure_ascii=False, default=_json_default).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store, max-age=0, must-revalidate')
        self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def static(self, p):
        fp = ROOT / 'frontend' / p
        if not fp.exists(): return self.send({'error':'static not found'},404)
        b = fp.read_bytes()
        ct = 'text/html' if p.endswith('.html') else 'text/javascript' if p.endswith('.js') else 'text/css'
        self.send_response(200); self.send_header('Content-Type', ct+'; charset=utf-8'); self.send_header('Cache-Control','no-store, max-age=0, must-revalidate'); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == '/api/professional-status': return self.send(ProfessionalEngine(repo).report(limit=200, seed=20260902))
            if u.path == '/api/health':
                try:
                    hb = repo.one('SELECT * FROM background_heartbeat WHERE id=1') if repo.one("SELECT name FROM sqlite_master WHERE type='table' AND name='background_heartbeat'") else None
                    records = repo.one('SELECT COUNT(*) n FROM matches')['n']
                except: hb=None; records=0
                return self.send({'ok': True, 'version': VERSION, 'model_version': Model.VERSION, 'port': PORT, 'records': records, 'background': hb})
            if u.path == '/api/background-status':
                hb = repo.one('SELECT * FROM background_heartbeat WHERE id=1')
                state = repo.rows('SELECT key,value,updated_at FROM engine_state ORDER BY key')
                return self.send({'version': VERSION, 'heartbeat': hb, 'state': state, 'mode': 'Windows background service / scheduled task', 'live_sources': 'optional authorized public feeds; no paid football API required'})
            if u.path == '/api/catchup': return self.send(CatchUpEngine(repo).run())
            if u.path == '/api/historical-replay':
                today = dt.datetime.now(MX).date(); days = max(1, min(45, int(q.get('days',['31'])[0]))); start = (today-dt.timedelta(days=days-1)).isoformat()
                return self.send(HistoricalReplay(repo).run(start, today.isoformat(), force=q.get('force',['0'])[0]=='1'))
            if u.path == '/api/sources':
                return self.send({'version': VERSION, 'registry': repo.rows('SELECT * FROM source_registry_v2 ORDER BY priority'), 'fusion': repo.rows('SELECT entity_key,entity_type,source_count,sources,quality,updated_at FROM canonical_entities ORDER BY updated_at DESC LIMIT 100')})

            # ===== NUEVO: ENDPOINT RÁPIDO QUE NO HACE SYNC =====
            if u.path == '/api/calendar/fast':
                mx_today = dt.datetime.now(MX).date()
                date = q.get('date',[''])[0] or mx_today.isoformat()
                try: dt.date.fromisoformat(date)
                except: return self.send({'error':'Fecha inválida. Use YYYY-MM-DD.','date':date},400)
                # Solo lee DB, sin FixtureSync, sin ResultsSync, sin Model pesado
                fast_matches = repo.rows('SELECT id,date,time,competition,home,away,status,home_score,away_score,home_xg,away_xg,source FROM matches WHERE date=? ORDER BY CASE WHEN time IS NULL OR time="" THEN 1 ELSE 0 END,time,competition,home LIMIT 100', (date,))
                # Cache info
                cache_row = repo.one('SELECT updated_at,coverage_status,match_count FROM fixture_sync_cache WHERE date=?', (date,))
                return self.send({'date': date, 'matches': fast_matches, 'competitions': competitions(repo, date), 'fast': True, 'cache': cache_row, 'count': len(fast_matches)})

            if u.path == '/api/calendar':
                mx_today = dt.datetime.now(MX).date()
                date = q.get('date',[''])[0] or mx_today.isoformat()
                try: dt.date.fromisoformat(date)
                except: return self.send({'error':'Fecha inválida. Use YYYY-MM-DD.','date':date},400)
                force = q.get('refresh',['0'])[0]=='1'
                fast = q.get('fast',['0'])[0]=='1'
                fx = FixtureSync(repo)
                fx.bootstrap_seed()
                # Si fast=1, no hace sync ni predictions pesadas
                if fast:
                    ms = predictions_for(repo, date, allow_persist=False, fast=True)
                    return self.send({'date': date, 'matches': ms, 'competitions': competitions(repo, date), 'fast': True, 'fixture_sync': {'skipped': True, 'reason': 'fast mode'}})

                if os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')=='1':
                    fixture_sync = {'date': date, 'skipped': True, 'reason': 'live fixtures disabled; local cache only', 'coverage_status': 'local-only', 'match_count': int(repo.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']), 'sources_ok':0, 'failures':[]}
                else:
                    # Solo hace sync si refresh=1 o si cache está viejo
                    if force:
                        fixture_sync = fx.sync_day_cached(date, force=True)
                    else:
                        fixture_sync = fx.sync_day_cached(date, force=False)

                result_sync = None
                # ResultsSync solo si es hoy o pasado y no estamos en fast
                if date <= mx_today.isoformat() and os.getenv('LIAN_DISABLE_LIVE_RESULTS','0')!='1' and not fast:
                    # Haz ResultsSync en background para no bloquear la respuesta principal
                    def do_result_sync():
                        try:
                            rs = ResultsSync(repo).sync(date)
                            if rs.get('applied'): AdaptiveCalibration(repo).run()
                        except: pass
                    threading.Thread(target=do_result_sync, daemon=True).start()

                ms = predictions_for(repo, date, allow_persist=(date >= mx_today.isoformat()), fast=False)
                ms = [m for m in ms if m.get('date')==date]
                pairs = [(m.get('home'), m.get('away')) for m in ms]
                duplicate_count = len(pairs)-len(set(pairs))
                db_count = repo.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']
                integrity = {'date_exact': all(m.get('date')==date for m in ms), 'unique_pairs': duplicate_count==0, 'returned_count': len(ms), 'db_count': db_count, 'prediction_records': sum(bool(m.get('pre_match_prediction')) for m in ms), 'retrospective_only': sum(m.get('prediction_source')=='RETROSPECTIVE_RECONSTRUCTION' for m in ms)}
                return self.send({'date': date, 'matches': ms, 'competitions': competitions(repo, date), 'fixture_sync': fixture_sync, 'calendar_integrity': integrity, 'live_context': {'status':'deferred','reason':'use /api/live-context per match'}, 'policy': {'historical_read_only': True, 'learning_side_effects': bool(result_sync and result_sync.get('applied')), 'result_sync_in_calendar': bool(date <= mx_today.isoformat()), 'past_status_rule': 'past dates can never be displayed as PRÓXIMO; verified scores are FINALIZADO, otherwise RESULTADO PENDIENTE'}, 'result_sync': result_sync, 'window': {'start': (mx_today-dt.timedelta(days=1)).isoformat(), 'end': (mx_today+dt.timedelta(days=29)).isoformat()}})

            if u.path == '/api/calendar-window':
                mx_today = dt.datetime.now(MX).date(); fx = FixtureSync(repo); fx.bootstrap_seed()
                start = mx_today.isoformat(); end = (mx_today+dt.timedelta(days=29)).isoformat()
                live_enabled = os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')!='1'
                if live_enabled:
                    try: sync = fx.sync_span_cached(start, end, force=q.get('refresh',['0'])[0]=='1', light=True)
                    except Exception as ex: sync = {'start': start, 'end': end, 'error': str(ex), 'match_count':0}
                else: sync = {'start': start, 'end': end, 'skipped': True, 'reason':'live fixtures disabled; local cache only', 'match_count':0}
                days = []
                for i in range(30):
                    d = (mx_today+dt.timedelta(days=i)).isoformat()
                    rows = repo.rows('SELECT id,date,time,competition,home,away,status,source FROM matches WHERE date=? ORDER BY CASE WHEN time IS NULL OR time="" THEN 1 ELSE 0 END,time,competition,home',(d,))
                    days.append({'date': d, 'matches': len(rows), 'fixtures': rows})
                return self.send({'start': start, 'end': end, 'window_days':30, 'fixture_sync': sync, 'recent_result_learning_sync':'owned_by_background_engine', 'days': days})

            if u.path == '/api/top-picks': return self.send({'items': top(repo, q.get('date',[''])[0])})
            if u.path == '/api/combinations': return self.send(build(repo, q.get('date',[''])[0]))
            if u.path == '/api/progol':
                contest = q.get('contest',[''])[0]
                if contest: return self.send(generate_contest(repo, contest))
                date = q.get('date',[''])[0]
                sync = ResultsSync(repo).sync(date)
                if sync.get('applied'): AdaptiveCalibration(repo).run()
                result = generate(repo, date); result['result_sync']=sync; return self.send(result)
            if u.path == '/api/universal-match':
                term = q.get('q',[''])[0].strip(); mid = q.get('match_id',[''])[0].strip() or None; return self.send(universal_search(repo, term, mid))
            if u.path == '/api/fixture-diagnostics':
                today = mexico_today_iso(); row = repo.rows('SELECT date,updated_at,coverage_status,match_count FROM fixture_sync_cache WHERE date>=? ORDER BY date',(today,)); return self.send({'today_mx': today, 'window_days':30, 'cache': row, 'policy':'Current/future fixture discovery is rolling and source-backed; stale historical rows are never promoted over a verified current fixture.', 'live_enabled': os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')!='1'})
            if u.path == '/api/data-health': return self.send(data_health(repo))
            if u.path == '/api/prediction-timeline':
                mid = q.get('match_id',[''])[0].strip()
                if not mid: return self.send({'error':'match_id requerido'},400)
                return self.send({'match_id': mid, 'runs': repo.rows('SELECT model_version,p_home,p_draw,p_away,pick,confidence,evidence,created_at FROM model_runs WHERE match_id=? ORDER BY created_at',(mid,)), 'evidence': repo.rows('SELECT model_version,collected_at,source_count,historical_matches,h2h_matches,feature_count,quality FROM evidence_snapshots WHERE match_id=? ORDER BY collected_at',(mid,))})
            if u.path == '/api/intelligence':
                mid = q.get('match_id',[''])[0].strip()
                if mid:
                    m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                    if not m: return self.send({'found': False, 'reason':'match_id no encontrado'},404)
                    return self.send(study(repo, m.get('home','')+' vs '+m.get('away',''), match_id=mid))
                return self.send(study(repo, q.get('q',[''])[0]))
            if u.path == '/api/search':
                term = q.get('q',[''])[0].strip(); limit = min(20, max(1, int(q.get('limit',['8'])[0]))); items = search_matches(repo, term, limit); today = mexico_today_iso(); has_current = any(str(x.get('date',''))[:10] >= today for x in items); refresh=None
                if term and not has_current and os.getenv('LIAN_DISABLE_LIVE_FIXTURES','0')!='1':
                    try:
                        refresh = FixtureSync(repo).sync_window_cached(today, days=30, force=True); items = search_matches(repo, term, limit)
                    except Exception as ex: refresh = {'error': str(ex), 'start': today}
                return self.send({'query': term, 'items': items, 'index':'LiAn local canonical match index', 'count': len(items), 'calendar_context': {'today_mx': today, 'automatic_refresh': bool(refresh), 'window_days':30}, 'refresh': refresh})
            if u.path == '/api/system-audit':
                from .services.professional_audit import ProfessionalAudit; return self.send(ProfessionalAudit(repo).report())
            if u.path == '/api/learning': return self.send(Adaptive(repo).report())
            if u.path == '/api/contextual-intelligence': return self.send(ContextualIntelligence(repo).recent_study(int(q.get('limit',['80'])[0])))
            if u.path == '/api/live-context':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                return self.send(LiveContextEngine(repo).refresh(m))
            if u.path == '/api/calibration': return self.send(AdaptiveCalibration(repo).report())
            if u.path == '/api/evidence': return self.send(EvidenceEngine(repo).report())
            if u.path == '/api/error-learning': return self.send(ErrorLearning(repo).report())
            if u.path == '/api/error-intelligence': return self.send(ErrorIntelligence(repo).report())
            if u.path == '/api/error-fingerprint':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                return self.send(ErrorFingerprint(repo).assess(m, Model(repo).predict(m)))
            if u.path == '/api/data-status': return self.send(DataStatus(repo).report())
            if u.path == '/api/historical-master': return self.send(HistoricalMaster(repo).build())
            if u.path == '/api/promotion-gate': return self.send({'policy':'candidate must improve or remain non-inferior on predictive metrics; regressions are rejected', 'latest': repo.rows('SELECT * FROM promotion_gates ORDER BY id DESC LIMIT 20')})
            if u.path == '/api/data-engine': return self.send({'sources': repo.rows('SELECT * FROM source_registry ORDER BY priority'), 'finished_matches': repo.one("SELECT COUNT(*) n FROM matches WHERE status='finished'")['n'], 'competitions': repo.rows('SELECT competition_id,competition,COUNT(*) n FROM matches GROUP BY competition_id,competition ORDER BY n DESC')})
            if u.path == '/api/historical-sync': return self.send(HistoricalSync(repo).run())
            if u.path == '/api/results-sync':
                date = q.get('date',[''])[0]; result = ResultsSync(repo).sync(date)
                if result.get('applied'): result['calibration']=AdaptiveCalibration(repo).run()
                return self.send(result)
            if u.path == '/api/feature-snapshot':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                return self.send(dict(m, **Model(repo).predict(m)))
            if u.path == '/api/venue':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                from .services.venue import resolve; return self.send(resolve(m))
            if u.path in ('/api/explain','/api/decision'):
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                return self.send(Model(repo).predict(m).get('explainability',{}))
            if u.path == '/api/backtest': return self.send(BacktestEngine(repo).run(int(q.get('limit',['200'])[0])))
            if u.path == '/api/benchmark': return self.send(ProfessionalBenchmark(repo).full_report(int(q.get('limit',['200'])[0]), int(q.get('seed',['20260902'])[0])))
            if u.path == '/api/benchmark-5': return self.send(ProfessionalBenchmark(repo).random_five(int(q.get('seed',['20260902'])[0])))
            if u.path == '/api/autopsy':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                AdaptiveCalibration(repo).run(); return self.send(repo.one('SELECT * FROM postmatch_reviews WHERE match_id=?',(mid,)) or {'status':'not_finished'})
            if u.path == '/api/review':
                mid = q.get('match_id',[''])[0]; m = repo.one('SELECT * FROM matches WHERE id=?',(mid,))
                if not m: return self.send({'error':'match_id not found'},404)
                AdaptiveCalibration(repo).run(); return self.send(repo.one('SELECT * FROM postmatch_reviews WHERE match_id=?',(mid,)) or {'status':'not_finished'})
            if u.path == '/api/competitions': return self.send({'items': repo.rows('SELECT competition_id,competition,COUNT(*) n FROM matches GROUP BY competition_id,competition ORDER BY competition'), 'version': VERSION})
            if u.path in ('/','/index.html'): return self.static('index.html')
            if u.path in ('/app.js','/style.css'): return self.static(u.path[1:])

            return self.send({'error':'not found'},404)
        except Exception as e:
            import traceback; traceback.print_exc()
            return self.send({'error': str(e)},500)

def main():
    for method in ['init','init_db','init_schema','ensure_schema','create_tables','init_learning']:
        if hasattr(repo, method):
            try: getattr(repo, method)()
            except: pass
    FixtureSync(repo).bootstrap_seed()
    # Pre-calienta hoy y mañana en background para que /api/calendar/fast siempre tenga datos
    def warm():
        try:
            today = dt.datetime.now(MX).date()
            for i in range(3):
                d = (today+dt.timedelta(days=i)).isoformat()
                try: FixtureSync(repo).sync_day_cached(d, force=False)
                except: pass
        except: pass
    threading.Thread(target=warm, daemon=True).start()
    LianHTTPServer(('0.0.0.0', PORT), H).serve_forever()

if __name__ == '__main__':
    main()
