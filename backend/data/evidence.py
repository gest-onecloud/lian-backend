import json, math, datetime

class EvidenceEngine:
    def __init__(self, repo):
        self.r=repo; self.init()
    def init(self):
        c=self.r.connect()
        try:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS evidence_snapshots(
              id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT NOT NULL, model_version TEXT NOT NULL,
              collected_at TEXT DEFAULT CURRENT_TIMESTAMP, source_count INTEGER DEFAULT 0,
              historical_matches INTEGER DEFAULT 0, h2h_matches INTEGER DEFAULT 0,
              feature_count INTEGER DEFAULT 0, quality REAL DEFAULT 0, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS postmatch_reviews(
              id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT UNIQUE NOT NULL, model_version TEXT,
              predicted TEXT, actual TEXT, brier REAL, log_loss REAL, goal_error REAL,
              calibration_gap REAL, diagnosis TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS feature_performance(
              feature TEXT PRIMARY KEY, samples INTEGER DEFAULT 0, correct REAL DEFAULT 0,
              error REAL DEFAULT 0, weight REAL DEFAULT 1, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS source_registry(
              source TEXT PRIMARY KEY, kind TEXT, priority INTEGER, enabled INTEGER DEFAULT 1,
              last_success TEXT, last_failure TEXT, failures INTEGER DEFAULT 0, notes TEXT);
            ''')
            sources=[('local_store','local',1),('openfootball','historical',2),('football_data','historical',3),('football_data_org','api',4),('on_demand_search','on-demand',5)]
            for s in sources:
                c.execute('INSERT OR IGNORE INTO source_registry(source,kind,priority) VALUES(?,?,?)',s)
        finally:c.close()
    @staticmethod
    def brier(p,actual):
        return sum((p.get(k,0)-(1 if k==actual else 0))**2 for k in ('1','X','2'))
    @staticmethod
    def logloss(p,actual): return -math.log(max(1e-12,p.get(actual,1e-12)))
    def save(self, match, prediction):
        existing=self.r.one('SELECT id FROM evidence_snapshots WHERE match_id=? AND model_version=?',(match['id'],prediction.get('model_version','55.0')))
        if existing: return
        f=prediction.get('features',{}); p=prediction.get('probabilities',{})
        payload={'match':match,'prediction':prediction,'rules':['no_future_leakage','temporal_features','source_quality_weighted']}
        self.r.execute('INSERT INTO evidence_snapshots(match_id,model_version,source_count,historical_matches,h2h_matches,feature_count,quality,payload) VALUES(?,?,?,?,?,?,?,?)',
          (match['id'],prediction.get('model_version','55.0'),prediction.get('source_count',0),f.get('home_history',0)+f.get('away_history',0),f.get('h2h',0),len(prediction.get('feature_vector',{})),prediction.get('evidence',0),json.dumps(payload,ensure_ascii=False)))
    def review(self,match,prediction):
        if match.get('status')!='finished' or match.get('home_score') is None:return None
        actual='1' if match['home_score']>match['away_score'] else 'X' if match['home_score']==match['away_score'] else '2'
        p=prediction['probabilities']; b=self.brier(p,actual); ll=self.logloss(p,actual); ge=abs((prediction.get('expected_goals',{}).get('home',0)-match['home_score']))+abs((prediction.get('expected_goals',{}).get('away',0)-match['away_score']))
        diagnosis=self.diagnose(match,prediction,actual)
        self.r.execute('INSERT OR REPLACE INTO postmatch_reviews(match_id,model_version,predicted,actual,brier,log_loss,goal_error,calibration_gap,diagnosis) VALUES(?,?,?,?,?,?,?,?,?)',
          (match['id'],prediction.get('model_version','55.0'),prediction['pick'],actual,b,ll,ge,abs(max(p.values())-(1 if prediction['pick']==actual else 0)),json.dumps(diagnosis,ensure_ascii=False)))
        return {'actual':actual,'brier':b,'log_loss':ll,'goal_error':ge,'diagnosis':diagnosis}
    def diagnose(self,match,pred,actual):
        p=pred['probabilities']; winner=pred['pick']; diag=[]
        if winner!=actual: diag.append('prediction_wrong')
        if max(p.values())>.65 and winner!=actual: diag.append('overconfidence')
        if abs(p['1']-p['2'])<.08: diag.append('highly_balanced')
        if pred.get('features',{}).get('home_history',0)+pred.get('features',{}).get('away_history',0)<10: diag.append('low_sample')
        return diag
    def report(self):
        r=self.r.one('SELECT COUNT(*) n, AVG(brier) b, AVG(log_loss) l FROM postmatch_reviews') or {}
        e=self.r.one('SELECT COUNT(*) n FROM evidence_snapshots') or {}
        return {'reviews':r.get('n',0),'brier':r.get('b'),'log_loss':r.get('l'),'evidence_snapshots':e.get('n',0)}
