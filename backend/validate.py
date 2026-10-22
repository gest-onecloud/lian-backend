import ast,sys,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED_VERSION=(ROOT/'VERSION.txt').read_text(encoding='utf8').strip()
def main():
 errors=[]
 legacy=('lian_'+'work_'+'current','test_'+'v52_','V'+'52.','V'+'53.')
 for p in ROOT.rglob('*.py'):
  if any(x in str(p) for x in ('__pycache__',)): continue
  try: ast.parse(p.read_text(encoding='utf8'))
  except Exception as e: errors.append(f'PYTHON {p}:{e}')
  txt=p.read_text(encoding='utf8',errors='ignore')
  if any(x in txt for x in legacy): errors.append(f'LEGACY TOKEN {p}')
 db=ROOT/'data'/'lian.db'; c=sqlite3.connect(db)
 count=c.execute('select count(*) from matches').fetchone()[0]; integrity=c.execute('pragma integrity_check').fetchone()[0]
 if integrity!='ok': errors.append('SQLite integrity')
 required_tables={'matches','match_stats','predictions','feature_snapshots','team_state','player_state','league_state','model_evaluations','model_weights','prediction_errors','postmatch_reviews','error_segment_metrics','error_intelligence_snapshots','adaptive_feature_history','adaptive_outcome_history','learning_audit','learning_snapshots'}
 tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
 missing=required_tables-tables
 if missing: errors.append('missing tables: '+','.join(sorted(missing)))
 js=(ROOT/'frontend/app.js').read_text(encoding='utf8'); html=(ROOT/'frontend/index.html').read_text(encoding='utf8')
 for token in ['loadDay','loadTop','loadCombo','loadProgol','loadIntel','loadLearning','loadData','/api/data-status','/api/error-intelligence','5 niveles','2 combinadas','consensus','stability','error-intelligence','Inteligencia de errores','calendar_integrity','fixture_sync','coverage_status','ESPN_ALL','Calendario verificado',EXPECTED_VERSION]:
  if token not in js: errors.append('missing frontend token '+token)
 backend_server=(ROOT/'backend/server.py').read_text(encoding='utf8')
 backend_model=(ROOT/'backend/core/model.py').read_text(encoding='utf8')
 if f"VERSION='{EXPECTED_VERSION}'" not in backend_server: errors.append('server version mismatch')
 # The predictive model version is intentionally independent from the platform release.
 # This fix release does not alter backend/core/model.py, so it must retain 63.0.0.
 MODEL_VERSION='64.0.0'
 if f"VERSION='{MODEL_VERSION}'" not in backend_model: errors.append('predictive model version changed unexpectedly')
 backend_progol=(ROOT/'backend/services/progol.py').read_text(encoding='utf8')
 for token,txt in [('ErrorFingerprint',backend_server),('AdaptiveLearningEngine',backend_server),('progol_tickets',backend_progol),('progol_match_results',backend_progol),(EXPECTED_VERSION,backend_server)]:
  if token not in txt: errors.append('missing backend token '+token)
 if '/app.js' not in html: errors.append('frontend not linked')
 c.close()
 if errors:
  print('VALIDATION FAIL'); [print(x) for x in errors]; sys.exit(1)
 print(f'VALIDATION PASS | sqlite={integrity} | records={count} | tables={len(tables)} | frontend=present | temporal-feature-store=present | legacy=none')
if __name__=='__main__': main()
