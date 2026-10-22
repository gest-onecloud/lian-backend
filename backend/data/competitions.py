CATALOG={
 'ES-LALIGA':('LaLiga','España','Europe'), 'EN-CARABAO':('Carabao Cup','Inglaterra','Europe'),
 'UEFA-UCL-Q':('UEFA Champions League — Clasificación','Europa','Europe'), 'UEFA-UCL':('UEFA Champions League','Europa','Europe'),
 'UEFA-EUL':('UEFA Europa League','Europa','Europe'), 'UEFA-UECL':('UEFA Conference League','Europa','Europe'),
 'MX-LIGA':('Liga MX','México','Americas'), 'MX-COPA':('Copa MX','México','Americas'),
 'MLS':('MLS','Estados Unidos','Americas'), 'CONCACAF-LC':('Leagues Cup','Norteamérica','Americas'),
 'CONCACAF-CCC':('Concacaf Champions Cup','Norteamérica','Americas'), 'LIB':('Copa Libertadores','Sudamérica','Americas'),
 'SUD':('Copa Sudamericana','Sudamérica','Americas'), 'DE-BUND':('Bundesliga','Alemania','Europe'),
 'IT-SERIEA':('Serie A','Italia','Europe'), 'FR-L1':('Ligue 1','Francia','Europe'), 'EN-PL':('Premier League','Inglaterra','Europe')
}
VISIBLE={k for k in CATALOG if k not in {'HR-CUP','EN-CHAMPIONSHIP'}}
def info(cid,name=''): return {'id':cid,'name':CATALOG.get(cid,(name,'',''))[0],'country':CATALOG.get(cid,(name,'',''))[1],'region':CATALOG.get(cid,(name,'',''))[2]}
