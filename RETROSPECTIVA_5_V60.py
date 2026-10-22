import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
r=Repo(ROOT/'data'/'lian.db'); ids=[x['id'] for x in json.loads(Path('/mnt/data/old_results.json').read_text())]; model=Model(r); out=[]
for mid in ids:
 m=r.one('SELECT * FROM matches WHERE id=?',(mid,)); p=model.predict(m); actual='1' if m['home_score']>m['away_score'] else 'X' if m['home_score']==m['away_score'] else '2'; out.append({'id':mid,'home':m['home'],'away':m['away'],'date':m['date'],'hs':m['home_score'],'as':m['away_score'],'actual':actual,'pick':p['pick'],'prob':p['probabilities'],'version':p['model_version'],'decision':p['decision']})
print(json.dumps(out,ensure_ascii=False))
