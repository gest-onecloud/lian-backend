import random, sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DB=ROOT/'data'/'lian.db'
random.seed()
c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
rows=c.execute('''SELECT m.date,m.home,m.away,m.home_score,m.away_score,p.pick,p.p_home,p.p_draw,p.p_away,p.model_version,p.generated_at
FROM matches m JOIN predictions p ON p.match_id=m.id
WHERE m.status='finished' AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
ORDER BY m.date''').fetchall()
from collections import defaultdict
days=defaultdict(list)
for r in rows: days[r['date']].append(r)
candidates=[(d,rs) for d,rs in days.items() if len(rs)>=3]
if not candidates:
    print('NO HAY UN DIA HISTORICO CON 3 PARTIDOS PREDICHOS Y FINALIZADOS.')
    raise SystemExit(2)
date,rs=random.choice(candidates); picks=random.sample(rs,3)
print('='*72); print('LiAn - PRUEBA RETROSPECTIVA ALEATORIA (SOLO CONSOLA)'); print('='*72)
print(f'Día histórico seleccionado: {date}')
hits=0
for i,r in enumerate(picks,1):
    actual='1' if r['home_score']>r['away_score'] else 'X' if r['home_score']==r['away_score'] else '2'
    ok=r['pick']==actual; hits+=ok
    probs=f"1={r['p_home']:.1%} X={r['p_draw']:.1%} 2={r['p_away']:.1%}"
    print(f'\n{i}. {r["home"]} vs {r["away"]}')
    print(f'   Predicción LiAn: {r["pick"]} | Probabilidades: {probs}')
    print(f'   Resultado real: {r["home_score"]}-{r["away_score"]} | Veredicto: {"ACIERTO" if ok else "FALLA"}')
    print(f'   Modelo registrado: V{r["model_version"]} | Generada: {r["generated_at"]}')
print(f'\nResultado de la muestra: {hits}/3 aciertos ({hits/3:.1%})')
