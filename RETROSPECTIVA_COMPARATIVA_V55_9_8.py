import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.core.model import Model
r=Repo(ROOT/'data'/'lian.db'); m=Model(r)
ids=['cal-2026-08-25-en-carabao-cardiff-city-norwich-city','cal-2026-08-25-es-laliga-valencia-real-betis','cal-2026-08-25-en-carabao-southampton-west-ham-united']
print('='*92);print('LiAn V55.9.8 - COMPARATIVA RETROSPECTIVA FIJA (NO ALIMENTA APRENDIZAJE)');print('='*92)
old1=new1=old2=new2=0
for i,id in enumerate(ids,1):
 x=r.one('SELECT * FROM matches WHERE id=?',(id,)); old=r.one('SELECT * FROM predictions WHERE match_id=? ORDER BY generated_at ASC LIMIT 1',(id,)); p=m.predict(x)
 a='1' if x['home_score']>x['away_score'] else 'X' if x['home_score']==x['away_score'] else '2'; oldok=bool(old and old['pick']==a); newok=p['pick']==a
 op=sorted(['1','X','2'],key=lambda k:old[{'1':'p_home','X':'p_draw','2':'p_away'}[k]],reverse=True) if old else []
 oldcov=a in op[:2] if old else False; newcov=a in sorted(p['probabilities'],key=p['probabilities'].get,reverse=True)[:2]
 old1+=oldok;new1+=newok;old2+=oldcov;new2+=newcov
 print(f"\n{i}. {x['home']} vs {x['away']} | resultado {x['home_score']}-{x['away_score']} ({a})")
 print(f"  V{old['model_version']}: 1X2={old['pick']} {'ACIERTO' if oldok else 'FALLA'} | cobertura2={'SI' if oldcov else 'NO'}")
 print(f"  V55.9.8: 1X2={p['pick']} {'ACIERTO' if newok else 'FALLA'} | cobertura2={'SI' if newcov else 'NO'} | mercado={p['professional_markets']['double_chance']['market']} | decision={p['professional_markets']['double_chance']['decision']}")
print('\nRESUMEN 3 FIJOS')
print(f'1X2 anterior: {old1}/3 = {old1/3:.1%} | nuevo: {new1}/3 = {new1/3:.1%}')
print(f'Doble oportunidad anterior: {old2}/3 = {old2/3:.1%} | nuevo: {new2}/3 = {new2/3:.1%}')
print('Esta muestra no se usa para afirmar 80%; sirve solo como control de regresión comparativa.')
