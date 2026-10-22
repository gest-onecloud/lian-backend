"""Explainable decision layer: translates model signals into a human-auditable report."""
LABELS={'1':'Local','X':'Empate','2':'Visitante'}

def report(pred,match):
    p=pred['probabilities']; ordered=sorted(p.items(),key=lambda kv:kv[1],reverse=True); top,topv=ordered[0]; second,secondv=ordered[1]; margin=topv-secondv
    e=pred.get('evidence',0); c=pred.get('confidence',0); stability=pred.get('stability',{}).get('score',0); consensus=pred.get('consensus',{}).get('score',0)
    gate=pred.get('data_sufficiency') or {}
    if pred.get('data_sufficiency') is not None and not pred.get('selection_eligible',False):
        return {
          'status':'DATOS INSUFICIENTES','favorite':None,'top_result':top,'top_probability':round(topv*100,1),
          'second_result':second,'second_probability':round(secondv*100,1),'separation_points':round(margin*100,1),
          'risk':'ALTO','recommendation':gate.get('reason','No existe evidencia suficiente para seleccionar un resultado.'),
          'coverage':f'{LABELS[top]} + {LABELS[second]}',
          'analysis':f"{match['home']} vs {match['away']}: cobertura específica insuficiente. LiAn no promueve un ganador ni una apuesta con estos datos.",
          'why':[{'factor':'Puerta de integridad de datos','effect':gate.get('reason','evidencia insuficiente'),'weight':1.0}],
          'decision_rule':'Sin evidencia suficiente de ambos equipos no se fuerza ganador ni se incluye en Top Picks/Combinadas.',
          'consensus_score':round(consensus*100,1),'stability_score':round(stability*100,1),
          'counterfactual':pred.get('counterfactual',{}),'market_reading':[]
        }
    if abs(p['1']-p['2'])<=.015: status='SIN FAVORITO CLARO'; favorite=None
    elif margin<.02: status='SIN VENTAJA CLARA'; favorite=None
    elif margin<.07: status='LIGERA VENTAJA'; favorite=LABELS[top]
    elif margin<.12: status='VENTAJA MODERADA'; favorite=LABELS[top]
    else: status='FAVORITO CLARO'; favorite=LABELS[top]
    risk='ALTO' if c<.28 or e<.42 or stability<.70 else 'MEDIO' if c<.48 or e<.65 or stability<.86 else 'BAJO'
    if favorite is None:
        recommendation='No forzar un ganador. La distribución no separa suficientemente los escenarios; si se busca cobertura, usar doble oportunidad según la lectura y esperar nueva evidencia.'
        coverage=f'{LABELS[top]} + {LABELS[second]}'
    elif status=='LIGERA VENTAJA':
        recommendation=f'Preferencia ligera por {favorite}; la cobertura {favorite} + {LABELS[second]} reduce varianza.'; coverage=f'{favorite} + {LABELS[second]}'
    elif status=='VENTAJA MODERADA':
        recommendation=f'{favorite} es la preferencia del modelo, pero la evidencia y estabilidad deben acompañar la selección.'; coverage=f'{favorite} + {LABELS[second]}'
    else:
        recommendation=f'{favorite} es el favorito del ensemble y conserva ventaja frente al segundo escenario.'; coverage=f'{favorite} + {LABELS[second]}'
    why=[]
    for s in pred.get('signals',[])[:6]:
        if s['direction']!='neutral': why.append({'factor':s['factor'],'effect':f"favorece al {s['direction']} · impacto {s['share']*100:.1f}% del balance de señales",'weight':s['share']})
    venue=(pred.get('context') or {}).get('venue') or {}
    if venue.get('verified'): why.insert(0,{'factor':'Sede real verificada','effect':f"favorece al {'local' if venue.get('advantage_side')=='home' else 'visitante' if venue.get('advantage_side')=='away' else 'ninguno'}",'weight':.0})
    if not why: why=[{'factor':'Señales','effect':'sin bloque dominante suficiente','weight':.1}]
    cf=pred.get('counterfactual',{})
    analysis=(f"{match['home']} vs {match['away']}: {status.lower()}. {LABELS[top]} tiene {topv*100:.1f}% y {LABELS[second]} {secondv*100:.1f}%, separación {margin*100:.1f} pp. "
              f"La evidencia es {e*100:.1f}%, el consenso entre submodelos {consensus*100:.1f}% y la estabilidad {stability*100:.1f}%. "
              f"La sede es {venue.get('venue') or 'no verificada'} ({venue.get('status','SIN DATOS')}). "
              f"El modelo no convierte una señal aislada en certeza; combina fuerza, forma, producción ajustada, xG, contexto y simulación.")
    return {
      'status':status,'favorite':favorite,'top_result':top,'top_probability':round(topv*100,1),'second_result':second,'second_probability':round(secondv*100,1),'separation_points':round(margin*100,1),
      'risk':risk,'recommendation':recommendation,'coverage':coverage,'analysis':analysis,'why':why,
      'decision_rule':'Probabilidad y recomendación están separadas. La sede verificada tiene prioridad sobre la localía nominal. La confianza cae cuando baja la evidencia, consenso o estabilidad.',
      'consensus_score':round(consensus*100,1),'stability_score':round(stability*100,1),'counterfactual':cf,
      'market_reading':[f"Over 2.5: {pred.get('markets',{}).get('over_2_5',0)*100:.1f}%",f"BTTS: {pred.get('markets',{}).get('btts_yes',0)*100:.1f}%"],
    }
