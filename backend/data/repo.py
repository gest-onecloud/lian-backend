import sqlite3, re
from pathlib import Path

class Repo:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        c = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout=20000')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA journal_mode=WAL')
        return c

    # Lista COMPLETA de todas las columnas que tu motor puede pedir
    ALL_STATS_COLS = [
        'home_fouls','away_fouls','home_corners','away_corners',
        'home_yellow','away_yellow','home_yellow_cards','away_yellow_cards',
        'home_red','away_red','home_red_cards','away_red_cards',
        'home_sot','away_sot','home_shots','away_shots',
        'home_xg','away_xg','home_xga','away_xga','home_xa','away_xa',
        'home_possession','away_possession','home_goals','away_goals',
        'home_offsides','away_offsides','home_saves','away_saves',
        'season','league','round','region','country','tier','competition_id','source_type','data_quality',
        'result_source','result_source_type','result_source_url','result_verified_at'
    ]

    def _ensure_all_stats_columns(self):
        # Crea TODAS las columnas posibles de una vez para no estar reintentando una por una
        for col in self.ALL_STATS_COLS:
            typ = 'INTEGER' if any(k in col for k in ['_sot','_shots','_goals','_corners','_fouls','_cards','_yellow','_red','_saves','_offsides']) else 'REAL' if any(k in col for k in ['xg','xa','xga','possession','elo','attack']) else 'TEXT'
            if col in ['season','league','round','region','country','competition_id','source_type','result_source','result_source_type','result_source_url','result_verified_at']:
                typ = 'TEXT'
            for tbl in ['matches','match_stats','predictions','team_state','player_state','historical_master']:
                try:
                    cc = self.connect()
                    cc.execute(f'ALTER TABLE {tbl} ADD COLUMN {col} {typ}')
                    cc.close()
                except Exception:
                    try: cc.close()
                    except: pass

    def _try_add_missing_column(self, err_msg):
        m = re.search(r'no such column:\s*([a-zA-Z0-9_\.]+)', str(err_msg), re.I)
        if not m:
            return False
        col = m.group(1).split('.')[-1]
        col = re.sub(r'[^a-zA-Z0-9_]', '', col)
        if not col: return False
        # Si es yellow a secas, agrega también yellow_cards
        to_add = [col]
        if col == 'away_yellow': to_add.extend(['away_yellow_cards','home_yellow_cards','home_yellow','away_yellow'])
        if col == 'home_yellow': to_add.extend(['home_yellow_cards','away_yellow_cards'])
        if col == 'away_fouls': to_add.extend(['home_fouls','away_fouls','home_corners','away_corners'])
        if col == 'away_sot': to_add.extend(['home_sot','away_sot','home_shots','away_shots'])
        
        added = False
        for cname in set(to_add):
            typ = 'INTEGER' if any(k in cname for k in ['fouls','corners','sot','shots','goals','cards','yellow','red','saves']) else 'REAL'
            for tbl in ['matches','match_stats','predictions','team_state']:
                try:
                    cc = self.connect()
                    cc.execute(f'ALTER TABLE {tbl} ADD COLUMN {cname} {typ}')
                    cc.close()
                    added = True
                except:
                    try: cc.close()
                    except: pass
        return added

    def _ensure_table(self, table_name):
        try:
            c = self.connect()
            if table_name == 'match_stats':
                c.executescript("CREATE TABLE IF NOT EXISTS match_stats(match_id TEXT PRIMARY KEY, stats_json TEXT);")
            c.close()
        except: pass

    def rows(self, sql, args=()):
        attempts = 0
        while True:
            attempts += 1
            if attempts > 100:
                raise RuntimeError(f"Se alcanzó límite de reintentos (100) para: {sql}")
            c = self.connect()
            try:
                res = [dict(r) for r in c.execute(sql, args).fetchall()]
                c.close()
                return res
            except Exception as e:
                c.close()
                msg = str(e)
                if 'no such column' in msg.lower():
                    if self._try_add_missing_column(msg):
                        continue
                if 'no such table' in msg.lower():
                    mm = re.search(r'no such table:\s*([a-zA-Z0-9_]+)', msg, re.I)
                    if mm:
                        self._ensure_table(mm.group(1))
                        try: self.init_all()
                        except: pass
                        continue
                raise

    def one(self, sql, args=()):
        attempts = 0
        while True:
            attempts += 1
            if attempts > 100:
                raise RuntimeError(f"Límite 100 reintentos: {sql}")
            c = self.connect()
            try:
                r = c.execute(sql, args).fetchone()
                c.close()
                return dict(r) if r else None
            except Exception as e:
                c.close()
                msg = str(e)
                if 'no such column' in msg.lower():
                    if self._try_add_missing_column(msg):
                        continue
                if 'no such table' in msg.lower():
                    mm = re.search(r'no such table:\s*([a-zA-Z0-9_]+)', msg, re.I)
                    if mm:
                        self._ensure_table(mm.group(1))
                        try: self.init_all()
                        except: pass
                        continue
                raise

    def execute(self, sql, args=()):
        attempts = 0
        while True:
            attempts += 1
            if attempts > 100:
                raise RuntimeError(f"Límite 100 reintentos: {sql}")
            c = self.connect()
            try:
                c.execute('BEGIN IMMEDIATE')
                c.execute(sql, args)
                c.execute('COMMIT')
                c.close()
                return
            except Exception as e:
                try: c.execute('ROLLBACK')
                except: pass
                c.close()
                msg = str(e)
                if 'no such column' in msg.lower():
                    if self._try_add_missing_column(msg):
                        continue
                if 'no such table' in msg.lower():
                    mm = re.search(r'no such table:\s*([a-zA-Z0-9_]+)', msg, re.I)
                    if mm:
                        self._ensure_table(mm.group(1))
                        try: self.init_all()
                        except: pass
                        continue
                if 'ON CONFLICT' in msg:
                    try:
                        cc = self.connect()
                        cc.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique ON matches(date, home, away)')
                        cc.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique_comp ON matches(date, competition, home, away)')
                        cc.close()
                        continue
                    except: pass
                raise

    def init(self): return self.init_all()

    def init_all(self):
        c = self.connect()
        try:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS matches(
                id TEXT PRIMARY KEY, date TEXT NOT NULL, time TEXT, competition TEXT, competition_id TEXT,
                home TEXT NOT NULL, away TEXT NOT NULL, status TEXT DEFAULT 'scheduled',
                home_score INTEGER, away_score INTEGER,
                home_xg REAL, away_xg REAL, home_xga REAL, away_xga REAL, home_xa REAL, away_xa REAL,
                home_sot INTEGER, away_sot INTEGER, home_shots INTEGER, away_shots INTEGER,
                home_fouls INTEGER, away_fouls INTEGER, home_corners INTEGER, away_corners INTEGER,
                home_yellow INTEGER, away_yellow INTEGER, home_yellow_cards INTEGER, away_yellow_cards INTEGER,
                home_red INTEGER, away_red INTEGER, home_red_cards INTEGER, away_red_cards INTEGER,
                home_possession REAL, away_possession REAL,
                source TEXT, source_url TEXT, source_type TEXT, data_quality REAL DEFAULT 0,
                result_source TEXT, result_source_type TEXT, result_source_url TEXT, result_verified_at TEXT,
                region TEXT, country TEXT, tier INTEGER, season TEXT, league TEXT, round TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS predictions(
                match_id TEXT PRIMARY KEY, p_home REAL, p_draw REAL, p_away REAL, pick TEXT,
                confidence REAL, evidence REAL, uncertainty REAL, expected_goals REAL,
                home_xg REAL, away_xg REAL, home_xga REAL, away_xga REAL,
                rationale TEXT, model_version TEXT, generated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS match_stats(
                match_id TEXT PRIMARY KEY, date TEXT, home TEXT, away TEXT, competition TEXT,
                home_goals INTEGER, away_goals INTEGER,
                home_xg REAL, away_xg REAL, home_xga REAL, away_xga REAL,
                home_sot INTEGER, away_sot INTEGER, home_shots INTEGER, away_shots INTEGER,
                home_fouls INTEGER, away_fouls INTEGER, home_corners INTEGER, away_corners INTEGER,
                home_yellow INTEGER, away_yellow INTEGER, home_yellow_cards INTEGER, away_yellow_cards INTEGER,
                home_red INTEGER, away_red INTEGER, home_red_cards INTEGER, away_red_cards INTEGER,
                home_possession REAL, away_possession REAL,
                stats_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fixture_sync_cache(date TEXT PRIMARY KEY, updated_at REAL NOT NULL, coverage_status TEXT NOT NULL DEFAULT 'unknown', match_count INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS fixture_sync(date TEXT, source TEXT, match_count INTEGER, status TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(date, source));
            CREATE TABLE IF NOT EXISTS background_heartbeat(id INTEGER PRIMARY KEY, last_run TEXT, status TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS engine_state(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS source_registry(source TEXT PRIMARY KEY, kind TEXT, priority INTEGER, enabled INTEGER DEFAULT 1, last_success TEXT, last_failure TEXT, failures INTEGER DEFAULT 0, notes TEXT);
            CREATE TABLE IF NOT EXISTS source_registry_v2(source TEXT PRIMARY KEY, kind TEXT, priority INTEGER, enabled INTEGER DEFAULT 1, last_success TEXT, last_failure TEXT, failures INTEGER DEFAULT 0, notes TEXT);
            CREATE TABLE IF NOT EXISTS canonical_entities(entity_key TEXT PRIMARY KEY, entity_type TEXT, source_count INTEGER, sources TEXT, quality REAL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS adaptive_events(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,scope TEXT,entity TEXT,payload TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS model_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,model_version TEXT,p_home REAL,p_draw REAL,p_away REAL,pick TEXT,confidence REAL,evidence REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,as_of TEXT,feature_json TEXT NOT NULL,source_quality REAL);
            CREATE TABLE IF NOT EXISTS model_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,model_version TEXT,scope TEXT,samples INTEGER,accuracy REAL,brier REAL,log_loss REAL,calibration_error REAL,created_at TEXT);
            CREATE TABLE IF NOT EXISTS model_weights(scope TEXT PRIMARY KEY,weights_json TEXT NOT NULL,version INTEGER DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS team_state(team_id TEXT PRIMARY KEY,name TEXT NOT NULL,competition_id TEXT,region TEXT,country TEXT,last_date TEXT,matches INTEGER DEFAULT 0,elo REAL DEFAULT 1500,attack REAL DEFAULT 1,defense REAL DEFAULT 1,home_attack REAL DEFAULT 1,away_attack REAL DEFAULT 1,form5 REAL DEFAULT .5,form10 REAL DEFAULT .5,xg REAL DEFAULT 1,xga REAL DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS player_state(player_id TEXT PRIMARY KEY,name TEXT NOT NULL,team_id TEXT,last_date TEXT,matches INTEGER DEFAULT 0,minutes REAL DEFAULT 0,goals REAL DEFAULT 0,assists REAL DEFAULT 0,xg REAL DEFAULT 0,xa REAL DEFAULT 0,xga REAL DEFAULT 0,sot INTEGER DEFAULT 0,shots REAL DEFAULT 0,key_passes REAL DEFAULT 0,tackles REAL DEFAULT 0,interceptions REAL DEFAULT 0,cards REAL DEFAULT 0,impact REAL DEFAULT 0,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS prediction_errors(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,p_home REAL,p_draw REAL,p_away REAL,result TEXT,brier REAL,log_loss REAL,goal_error REAL,model_version TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS evidence_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT NOT NULL,model_version TEXT NOT NULL,collected_at TEXT DEFAULT CURRENT_TIMESTAMP,source_count INTEGER DEFAULT 0,historical_matches INTEGER DEFAULT 0,h2h_matches INTEGER DEFAULT 0,feature_count INTEGER DEFAULT 0,quality REAL DEFAULT 0,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS postmatch_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,model_version TEXT,predicted TEXT,actual TEXT,brier REAL,log_loss REAL,goal_error REAL,calibration_gap REAL,diagnosis TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_performance(feature TEXT PRIMARY KEY,samples INTEGER DEFAULT 0,correct REAL DEFAULT 0,error REAL DEFAULT 0,weight REAL DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS calibration_recommendations(id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, scope TEXT, metric TEXT, samples INTEGER, current_value REAL, target_value REAL, recommendation TEXT, eligible INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS result_sources(match_id TEXT PRIMARY KEY,source TEXT NOT NULL,source_type TEXT NOT NULL,source_url TEXT,verified_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'verified');
            CREATE TABLE IF NOT EXISTS prediction_provenance(match_id TEXT PRIMARY KEY, provenance TEXT NOT NULL, learning_eligible INTEGER NOT NULL DEFAULT 0, classified_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS historical_master(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,as_of TEXT NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,competition TEXT,season TEXT,home_score INTEGER,away_score INTEGER,result TEXT,home_xg REAL,away_xg REAL,home_xga REAL,away_xga REAL,home_elo REAL,away_elo REAL,home_tier INTEGER,away_tier INTEGER,home_squad_strength REAL,away_squad_strength REAL,sos_home REAL,sos_away REAL,data_quality REAL DEFAULT 0,source TEXT,ingested_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS squad_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,team TEXT NOT NULL,as_of TEXT NOT NULL,source TEXT NOT NULL,quality REAL DEFAULT 0,expected_xi_strength REAL,available_squad_strength REAL,missing_strength REAL,players_json TEXT NOT NULL,UNIQUE(team,as_of,source));
            CREATE TABLE IF NOT EXISTS promotion_gates(id INTEGER PRIMARY KEY AUTOINCREMENT,baseline_version TEXT NOT NULL,candidate_version TEXT NOT NULL,samples INTEGER NOT NULL,baseline_accuracy REAL,candidate_accuracy REAL,baseline_brier REAL,candidate_brier REAL,baseline_log_loss REAL,candidate_log_loss REAL,status TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique ON matches(date, home, away);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique_comp ON matches(date, competition, home, away);
            CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
            CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
            """);
            try: c.execute("INSERT OR IGNORE INTO background_heartbeat(id, status) VALUES(1, 'initialized')")
            except: pass
        finally:
            c.close()
        # Asegura todas las columnas posibles al iniciar
        self._ensure_all_stats_columns()

    def init_learning(self):
        try: self.init_all()
        except: pass
