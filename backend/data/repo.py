import sqlite3
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

    def rows(self, sql, args=()):
        c = self.connect()
        try:
            return [dict(r) for r in c.execute(sql, args).fetchall()]
        finally:
            c.close()

    def one(self, sql, args=()):
        c = self.connect()
        try:
            r = c.execute(sql, args).fetchone()
            return dict(r) if r else None
        finally:
            c.close()

    def execute(self, sql, args=()):
        c = self.connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            c.execute(sql, args)
            c.execute('COMMIT')
        except Exception:
            try:
                c.execute('ROLLBACK')
            except Exception:
                pass
            raise
        finally:
            c.close()

    def init(self):
        """Crea TODAS las tablas necesarias para producción - fix para Render + IONOS"""
        return self.init_all()

    def init_all(self):
        c = self.connect()
        try:
            c.executescript('''
            -- TABLAS CORE DE PARTIDOS
            CREATE TABLE IF NOT EXISTS matches(
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                time TEXT,
                competition TEXT,
                competition_id TEXT,
                home TEXT NOT NULL,
                away TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                home_score INTEGER,
                away_score INTEGER,
                source TEXT,
                source_url TEXT,
                source_type TEXT,
                data_quality REAL DEFAULT 0,
                result_source TEXT,
                result_source_type TEXT,
                result_source_url TEXT,
                result_verified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS predictions(
                match_id TEXT PRIMARY KEY,
                p_home REAL,
                p_draw REAL,
                p_away REAL,
                pick TEXT,
                confidence REAL,
                evidence REAL,
                uncertainty REAL,
                expected_goals REAL,
                rationale TEXT,
                model_version TEXT,
                generated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- CACHE DE FIXTURES
            CREATE TABLE IF NOT EXISTS fixture_sync_cache(
                date TEXT PRIMARY KEY,
                updated_at TEXT,
                coverage_status TEXT,
                match_count INTEGER DEFAULT 0,
                source_counts TEXT,
                failures TEXT
            );

            CREATE TABLE IF NOT EXISTS fixture_sync(
                date TEXT,
                source TEXT,
                match_count INTEGER,
                status TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(date, source)
            );

            -- HEARTBEAT Y ESTADO
            CREATE TABLE IF NOT EXISTS background_heartbeat(
                id INTEGER PRIMARY KEY,
                last_run TEXT,
                status TEXT,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS engine_state(
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- REGISTRIES
            CREATE TABLE IF NOT EXISTS source_registry(
                source TEXT PRIMARY KEY,
                kind TEXT,
                priority INTEGER,
                enabled INTEGER DEFAULT 1,
                last_success TEXT,
                last_failure TEXT,
                failures INTEGER DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS source_registry_v2(
                source TEXT PRIMARY KEY,
                kind TEXT,
                priority INTEGER,
                enabled INTEGER DEFAULT 1,
                last_success TEXT,
                last_failure TEXT,
                failures INTEGER DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS canonical_entities(
                entity_key TEXT PRIMARY KEY,
                entity_type TEXT,
                source_count INTEGER,
                sources TEXT,
                quality REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- LEARNING (ya existía pero lo reforzamos)
            CREATE TABLE IF NOT EXISTS adaptive_events(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,scope TEXT,entity TEXT,payload TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS model_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,model_version TEXT,p_home REAL,p_draw REAL,p_away REAL,pick TEXT,confidence REAL,evidence REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,as_of TEXT,feature_json TEXT NOT NULL,source_quality REAL);
            CREATE TABLE IF NOT EXISTS model_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,model_version TEXT,scope TEXT,samples INTEGER,accuracy REAL,brier REAL,log_loss REAL,calibration_error REAL,created_at TEXT);
            CREATE TABLE IF NOT EXISTS model_weights(scope TEXT PRIMARY KEY,weights_json TEXT NOT NULL,version INTEGER DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS team_state(team_id TEXT PRIMARY KEY,name TEXT NOT NULL,competition_id TEXT,last_date TEXT,matches INTEGER DEFAULT 0,elo REAL DEFAULT 1500,attack REAL DEFAULT 1,defense REAL DEFAULT 1,home_attack REAL DEFAULT 1,away_attack REAL DEFAULT 1,form5 REAL DEFAULT .5,form10 REAL DEFAULT .5,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS player_state(player_id TEXT PRIMARY KEY,name TEXT NOT NULL,team_id TEXT,last_date TEXT,matches INTEGER DEFAULT 0,minutes REAL DEFAULT 0,goals REAL DEFAULT 0,assists REAL DEFAULT 0,xg REAL DEFAULT 0,xa REAL DEFAULT 0,shots REAL DEFAULT 0,sot REAL DEFAULT 0,key_passes REAL DEFAULT 0,tackles REAL DEFAULT 0,interceptions REAL DEFAULT 0,cards REAL DEFAULT 0,impact REAL DEFAULT 0,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS prediction_errors(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,p_home REAL,p_draw REAL,p_away REAL,result TEXT,brier REAL,log_loss REAL,goal_error REAL,model_version TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS evidence_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT NOT NULL,model_version TEXT NOT NULL,collected_at TEXT DEFAULT CURRENT_TIMESTAMP,source_count INTEGER DEFAULT 0,historical_matches INTEGER DEFAULT 0,h2h_matches INTEGER DEFAULT 0,feature_count INTEGER DEFAULT 0,quality REAL DEFAULT 0,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS postmatch_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,model_version TEXT,predicted TEXT,actual TEXT,brier REAL,log_loss REAL,goal_error REAL,calibration_gap REAL,diagnosis TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_performance(feature TEXT PRIMARY KEY,samples INTEGER DEFAULT 0,correct REAL DEFAULT 0,error REAL DEFAULT 0,weight REAL DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS calibration_recommendations(id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, scope TEXT, metric TEXT, samples INTEGER, current_value REAL, target_value REAL, recommendation TEXT, eligible INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS result_sources(match_id TEXT PRIMARY KEY,source TEXT NOT NULL,source_type TEXT NOT NULL,source_url TEXT,verified_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'verified');
            CREATE TABLE IF NOT EXISTS prediction_provenance(match_id TEXT PRIMARY KEY, provenance TEXT NOT NULL, learning_eligible INTEGER NOT NULL DEFAULT 0, classified_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS historical_master(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,as_of TEXT NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,competition TEXT,season TEXT,home_score INTEGER,away_score INTEGER,result TEXT,home_xg REAL,away_xg REAL,home_elo REAL,away_elo REAL,home_tier INTEGER,away_tier INTEGER,home_squad_strength REAL,away_squad_strength REAL,sos_home REAL,sos_away REAL,data_quality REAL DEFAULT 0,source TEXT,ingested_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS squad_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,team TEXT NOT NULL,as_of TEXT NOT NULL,source TEXT NOT NULL,quality REAL DEFAULT 0,expected_xi_strength REAL,available_squad_strength REAL,missing_strength REAL,players_json TEXT NOT NULL,UNIQUE(team,as_of,source));
            CREATE TABLE IF NOT EXISTS promotion_gates(id INTEGER PRIMARY KEY AUTOINCREMENT,baseline_version TEXT NOT NULL,candidate_version TEXT NOT NULL,samples INTEGER NOT NULL,baseline_accuracy REAL,candidate_accuracy REAL,baseline_brier REAL,candidate_brier REAL,baseline_log_loss REAL,candidate_log_loss REAL,status TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);

            -- INDICES
            CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
            CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
            CREATE INDEX IF NOT EXISTS idx_predictions_generated ON predictions(generated_at);
            CREATE INDEX IF NOT EXISTS idx_model_runs_match ON model_runs(match_id);
            ''')

            -- Columnas adicionales por compatibilidad
            for col, typ in [('result_source','TEXT'),('result_source_type','TEXT'),('result_source_url','TEXT'),('result_verified_at','TEXT'),('competition_id','TEXT'),('source_type','TEXT'),('data_quality','REAL')]:
                try:
                    c.execute(f'ALTER TABLE matches ADD COLUMN {col} {typ}')
                except Exception:
                    pass

            # Seed heartbeat
            try:
                c.execute("INSERT OR IGNORE INTO background_heartbeat(id, status) VALUES(1, 'initialized')")
            except Exception:
                pass

        finally:
            c.close()

    def init_learning(self):
        # Mantener compatibilidad, ahora llama a init_all
        try:
            self.init_all()
        except Exception:
            pass

        # Código original de learning
        c = self.connect()
        try:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS adaptive_events(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,scope TEXT,entity TEXT,payload TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS model_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,model_version TEXT,p_home REAL,p_draw REAL,p_away REAL,pick TEXT,confidence REAL,evidence REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,as_of TEXT,feature_json TEXT NOT NULL,source_quality REAL);
            CREATE TABLE IF NOT EXISTS model_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,model_version TEXT,scope TEXT,samples INTEGER,accuracy REAL,brier REAL,log_loss REAL,calibration_error REAL,created_at TEXT);
            CREATE TABLE IF NOT EXISTS model_weights(scope TEXT PRIMARY KEY,weights_json TEXT NOT NULL,version INTEGER DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS team_state(team_id TEXT PRIMARY KEY,name TEXT NOT NULL,competition_id TEXT,last_date TEXT,matches INTEGER DEFAULT 0,elo REAL DEFAULT 1500,attack REAL DEFAULT 1,defense REAL DEFAULT 1,home_attack REAL DEFAULT 1,away_attack REAL DEFAULT 1,form5 REAL DEFAULT .5,form10 REAL DEFAULT .5,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS player_state(player_id TEXT PRIMARY KEY,name TEXT NOT NULL,team_id TEXT,last_date TEXT,matches INTEGER DEFAULT 0,minutes REAL DEFAULT 0,goals REAL DEFAULT 0,assists REAL DEFAULT 0,xg REAL DEFAULT 0,xa REAL DEFAULT 0,shots REAL DEFAULT 0,sot REAL DEFAULT 0,key_passes REAL DEFAULT 0,tackles REAL DEFAULT 0,interceptions REAL DEFAULT 0,cards REAL DEFAULT 0,impact REAL DEFAULT 0,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS prediction_errors(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT,p_home REAL,p_draw REAL,p_away REAL,result TEXT,brier REAL,log_loss REAL,goal_error REAL,model_version TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS evidence_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT NOT NULL,model_version TEXT NOT NULL,collected_at TEXT DEFAULT CURRENT_TIMESTAMP,source_count INTEGER DEFAULT 0,historical_matches INTEGER DEFAULT 0,h2h_matches INTEGER DEFAULT 0,feature_count INTEGER DEFAULT 0,quality REAL DEFAULT 0,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS postmatch_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,model_version TEXT,predicted TEXT,actual TEXT,brier REAL,log_loss REAL,goal_error REAL,calibration_gap REAL,diagnosis TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_performance(feature TEXT PRIMARY KEY,samples INTEGER DEFAULT 0,correct REAL DEFAULT 0,error REAL DEFAULT 0,weight REAL DEFAULT 1,updated_at TEXT);
            CREATE TABLE IF NOT EXISTS calibration_recommendations(id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, scope TEXT, metric TEXT, samples INTEGER, current_value REAL, target_value REAL, recommendation TEXT, eligible INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS result_sources(match_id TEXT PRIMARY KEY,source TEXT NOT NULL,source_type TEXT NOT NULL,source_url TEXT,verified_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'verified');
            CREATE TABLE IF NOT EXISTS prediction_provenance(match_id TEXT PRIMARY KEY, provenance TEXT NOT NULL, learning_eligible INTEGER NOT NULL DEFAULT 0, classified_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS source_registry(source TEXT PRIMARY KEY,kind TEXT,priority INTEGER,enabled INTEGER DEFAULT 1,last_success TEXT,last_failure TEXT,failures INTEGER DEFAULT 0,notes TEXT);
            CREATE TABLE IF NOT EXISTS historical_master(id INTEGER PRIMARY KEY AUTOINCREMENT,match_id TEXT UNIQUE NOT NULL,as_of TEXT NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,competition TEXT,season TEXT,home_score INTEGER,away_score INTEGER,result TEXT,home_xg REAL,away_xg REAL,home_elo REAL,away_elo REAL,home_tier INTEGER,away_tier INTEGER,home_squad_strength REAL,away_squad_strength REAL,sos_home REAL,sos_away REAL,data_quality REAL DEFAULT 0,source TEXT,ingested_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS squad_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,team TEXT NOT NULL,as_of TEXT NOT NULL,source TEXT NOT NULL,quality REAL DEFAULT 0,expected_xi_strength REAL,available_squad_strength REAL,missing_strength REAL,players_json TEXT NOT NULL,UNIQUE(team,as_of,source));
            CREATE TABLE IF NOT EXISTS promotion_gates(id INTEGER PRIMARY KEY AUTOINCREMENT,baseline_version TEXT NOT NULL,candidate_version TEXT NOT NULL,samples INTEGER NOT NULL,baseline_accuracy REAL,candidate_accuracy REAL,baseline_brier REAL,candidate_brier REAL,baseline_log_loss REAL,candidate_log_loss REAL,status TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            ''')
        finally:
            c.close()
