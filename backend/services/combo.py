from .calendar import matches
import math

def _options(m):
 return sorted([(k,v) for k,v in m.get('probabilities',{}).items() if m.get('explainability',{}).get('favorite') is not None],key=lambda x:x[1],reverse=True)

def build(repo,date):
 ms=matches(repo,date)
 eligible_ms=[m for m in ms if m.get('selection_eligible') and m.get('explainability',{}).get('favorite') is not None]
 ranked=sorted(eligible_ms,key=lambda x:(x.get('evidence',0)*x.get('confidence',0),max(x.get('probabilities',{}).values() or [0])),reverse=True)
 configs=[('Nivel 1 · Máxima prudencia',.62,2),('Nivel 2 · Prudente',.56,3),('Nivel 3 · Balanceada',.50,4),('Nivel 4 · Agresiva',.44,5),('Nivel 5 · Alta varianza',.38,6)]
 levels=[]
 for label,target,size in configs:
  combos=[]
  for variant in range(2):
   pool=[]
   for m in ranked:
    opts=_options(m)
    # Variant 1: highest probability. Variant 2: second sign only when it is not materially weaker.
    choice=opts[0]
    if variant and len(opts)>1 and opts[1][1] >= opts[0][1]-.12: choice=opts[1]
    pool.append({'id':m['id'],'home':m['home'],'away':m['away'],'competition':m['competition'],'pick':choice[0], 'recommendation':m.get('explainability',{}).get('status',''),'probability':choice[1],'confidence':m.get('confidence',0),'evidence':m.get('evidence',0),'quality':m.get('quality','BAJA')})
   # For every level we generate two transparent scenarios. We never invent a sign.
   pool=sorted(pool,key=lambda x:(x['probability']*.55+x['evidence']*.25+x['confidence']*.20),reverse=True)
   chosen=[]; comps=set()
   for x in pool:
    if len(chosen)>=size:break
    if x['competition'] not in comps or len(pool)-len(chosen)<=2:chosen.append(x);comps.add(x['competition'])
   if len(chosen)<size:chosen=pool[:size]
   minp=min((x['probability'] for x in chosen),default=0)
   avg_ev=sum(x['evidence'] for x in chosen)/max(1,len(chosen))
   if minp>=target and avg_ev>=.70: status='RECOMENDADA'
   elif minp>=target-.10 and avg_ev>=.50: status='CONDICIONAL'
   else: status='NO RECOMENDADA · EVIDENCIA INSUFICIENTE'
   combos.append({'name':f'{label} · Combinada {variant+1}','size':len(chosen),'selections':chosen,'estimated_min_probability':round(math.prod(x['probability'] for x in chosen),6) if chosen else 0,'min_selection_probability':round(minp,4),'average_evidence':round(avg_ev,4),'status':status})
  levels.append({'level':label,'target_probability':target,'combinations':combos})
 return {'date':date,'investigated':len(ms),'eligible':sum(1 for m in eligible_ms if m.get('evidence',0)>=.35),'levels':levels,'status':'GENERADAS','note':'Se generan 2 escenarios por nivel. Los partidos sin favorito estadístico claro se excluyen de selecciones fuertes para evitar inventar un pick; el nivel puede quedar NO RECOMENDADA si no existe evidencia suficiente. Una combinada no es garantía de acierto.'}
