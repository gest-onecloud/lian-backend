import json
import urllib.parse
import os
import datetime as dt
import threading
import time
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
VERSION = '64.6.0 FINAL FAST'
PORT = int(os.getenv('LIAN_PORT', '8010'))

class LianHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Estado global para sync en background
SYNC_STATUS = {"running": False, "last_date": None, "last_result": None, "started_at": None}

def predictions_for(repo, date, allow_persist=True, fast=False):
    out = []
    if fast:
        # FAST: solo lee DB, sin Model pesado
        rows = repo.rows('SELECT id,date,time,competition,competition_id,home,away,status,home_score,away_score,source FROM matches WHERE date=? ORDER BY time,competition,home LIMIT 120', (date,))
        for m in rows:
            mt = mexico_time(m)
            p = dict(m)
            p['time_mx'] = mt.get('time_mx')
            p['date_mx'] = mt.get('date_mx')
            p['time_status_mx'] = mt.get('status')
            p['prediction_fast'] = True
            p['probabilities'] = {'1': 0, 'X': 0, '2': 0}
            p['confidence'] = 0
            p['evidence'] = 0
            p['pick'] = 'X'
            p['quality'] = 'CARGANDO'
            p = enrich_lifecycle(p)
            out.append(p)
        return out

    model = Model(repo)
    ev = EvidenceEngine(repo)
    fingerprint = ErrorFingerprint(repo)
    for m in raw_matches(repo, date):
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
        except: p['error_fingerprint'] = {'level': 'NO DISPONIBLE', 'message': 'No fingerprint'}
        p = enrich_lifecycle(p)
        if m.get('status') == 'finished':
            p['result'] = {'final': f"{m.get('home_score')}–{m.get('away_score')}", 'source': m.get('result_source')}
            if m.get('home_score') is not None and m.get('away_score') is not None:
                actual = '1' if int(m['home_score']) > int(m['away_score']) else 'X' if int(m['home_score']) == int(m['away_score']) else '2'
                p['result']['actual'] = actual; p['result']['prediction'] = p['pick']; p['result']['correct'] = (p['pick']==actual)
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

def universal_search(repo, term, mid=None):
    if not term: return {'found': False, 'query': term, 'reason': 'Escribe un equipo.'}
    if mid: return canonical(repo, term, mid)
    return canonical(repo, term, None)

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
            if u.path == '/api/health':
                try:
                    hb = repo.one('SELECT * FROM background_heartbeat WHERE id=1') if repo.one("SELECT name FROM sqlite_master WHERE type='table' AND name='background_heartbeat'") else None
                    records = repo.one('SELECT COUNT(*) n FROM matches')['n']
                except: hb=None; records=0
                return self.send({'ok': True, 'version': VERSION, 'model_version': Model.VERSION, 'port': PORT, 'records': records, 'background': hb, 'sync_status': SYNC_STATUS})

            if u.path == '/api/sync-status':
                return self.send(SYNC_STATUS)

            if u.path == '/api/calendar/fast':
                mx_today = dt.datetime.now(MX).date()
                date = q.get('date',[''])[0] or mx_today.isoformat()
                fast_matches = repo.rows('SELECT id,date,time,competition,competition_id,home,away,status,home_score,away_score,source FROM matches WHERE date=? ORDER BY time,competition,home LIMIT 150', (date,))
                cache_row = repo.one('SELECT updated_at,coverage_status,match_count FROM fixture_sync_cache WHERE date=?', (date,))
                return self.send({'date': date, 'matches': fast_matches, 'competitions': competitions(repo, date), 'fast': True, 'cache': cache_row, 'count': len(fast_matches)})

            if u.path == '/api/calendar':
                mx_today = dt.datetime.now(MX).date()
                date = q.get('date',[''])[0] or mx_today.isoformat()
                force = q.get('refresh',['0'])[0]=='1'
                fast_param = q.get('fast',['0'])[0]=='1'
                fx = FixtureSync(repo)
                fx.bootstrap_seed()

                if fast_param:
                    ms = predictions_for(repo, date, allow_persist=False, fast=True)
                    return self.send({'date': date, 'matches': ms, 'competitions': competitions(repo, date), 'fast': True, 'fixture_sync': {'skipped': True, 'reason': 'fast mode'}})

                # Forced refresh en background para no bloquear
                if force:
                    if not SYNC_STATUS["running"]:
                        SYNC_STATUS["running"] = True
                        SYNC_STATUS["last_date"] = date
                        SYNC_STATUS["started_at"] = time.time()
                        def do_sync():
                            try:
                                # FAST SYNC: solo ESPN_ALL, timeout 3s
                                r = fx.sync_day(date, fast=True)
                                SYNC_STATUS["last_result"] = r
                                SYNC_STATUS["running"] = False
                            except Exception as ex:
                                SYNC_STATUS["last_result"] = {"error": str(ex)}
                                SYNC_STATUS["running"] = False
                        threading.Thread(target=do_sync, daemon=True).start()
                    # Devuelve al instante con lo que hay en DB + flag de sync en curso
                    ms = predictions_for(repo, date, allow_persist=False, fast=False)
                    ms = [m for m in ms if m.get('date')==date]
                    return self.send({'date': date, 'matches': ms, 'competitions': competitions(repo, date), 'fixture_sync': {'status': 'sync_started_background', 'running': True, 'date': date, 'message': 'Sincronización en segundo plano iniciada (10-15s)'}, 'sync_status': SYNC_STATUS})

                # Normal: usa cache, solo sincroniza si cache viejo
                fixture_sync = fx.sync_day_cached(date, force=False)
                ms = predictions_for(repo, date, allow_persist=(date >= mx_today.isoformat()), fast=False)
                ms = [m for m in ms if m.get('date')==date]
                db_count = repo.one('SELECT COUNT(*) n FROM matches WHERE date=?',(date,))['n']
                return self.send({'date': date, 'matches': ms, 'competitions': competitions(repo, date), 'fixture_sync': fixture_sync, 'calendar_integrity': {'db_count': db_count, 'returned_count': len(ms)}, 'sync_status': SYNC_STATUS})

            # Resto de endpoints igual...
            if u.path == '/api/top-picks': return self.send({'items': top(repo, q.get('date',[''])[0])})
            if u.path == '/api/combinations': return self.send(build(repo, q.get('date',[''])[0]))
            if u.path == '/api/progol':
                contest = q.get('contest',[''])[0]
                if contest: return self.send(generate_contest(repo, contest))
                date = q.get('date',[''])[0]; return self.send(generate(repo, date))
            if u.path == '/api/universal-match':
                term = q.get('q',[''])[0].strip(); mid = q.get('match_id',[''])[0].strip() or None; return self.send(universal_search(repo, term, mid))
            if u.path == '/api/search':
                term = q.get('q',[''])[0].strip(); limit = min(20, max(1, int(q.get('limit',['8'])[0]))); items = search_matches(repo, term, limit); return self.send({'query': term, 'items': items, 'count': len(items)})
            if u.path == '/api/background-status':
                hb = repo.one('SELECT * FROM background_heartbeat WHERE id=1')
                state = repo.rows('SELECT key,value,updated_at FROM engine_state ORDER BY key')
                return self.send({'version': VERSION, 'heartbeat': hb, 'state': state})
            if u.path == '/api/calendar-window':
                mx_today = dt.datetime.now(MX).date(); fx = FixtureSync(repo); fx.bootstrap_seed()
                start = mx_today.isoformat(); end = (mx_today+dt.timedelta(days=29)).isoformat()
                days = []
                for i in range(30):
                    d = (mx_today+dt.timedelta(days=i)).isoformat()
                    rows = repo.rows('SELECT id,date,time,competition,home,away,status,source FROM matches WHERE date=? ORDER BY time,competition,home',(d,))
                    days.append({'date': d, 'matches': len(rows), 'fixtures': rows})
                return self.send({'start': start, 'end': end, 'window_days':30, 'days': days})
            if u.path == '/api/learning': return self.send(Adaptive(repo).report())
            if u.path == '/api/data-status': return self.send(DataStatus(repo).report())
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
