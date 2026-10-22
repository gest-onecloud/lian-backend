import re, unicodedata, datetime as dt
from ..core.model import Model
from .calendar_clock import mexico_today
from .match_lifecycle import enrich as enrich_lifecycle

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def tokens(q): return [x for x in norm(q).split() if len(x)>1]

def score_match(m, toks, qnorm):
    home=norm(m.get('home','')); away=norm(m.get('away','')); comp=norm(m.get('competition',''))
    text=f'{home} {away} {comp}'
    score=0
    pair=re.split(r'\s+(?:vs|v|contra)\s+', qnorm, maxsplit=1)
    if len(pair)==2 and all(pair):
        ph,pa=pair
        if home==ph and away==pa: score += 260
        elif home==pa and away==ph: score += 130
        elif ph in home and pa in away: score += 190
        elif ph in away and pa in home: score += 95
    if qnorm and qnorm in text: score += 80
    if all(t in text for t in toks): score += 45
    for side in (home,away):
        if side and any(t in side for t in toks): score += 18
    if m.get('status')!='finished': score += 4
    return score

def search_matches(repo,q,limit=8):
    qnorm=norm(q); toks=tokens(q)
    if not toks: return []
    today=mexico_today()
    rows=repo.rows('SELECT * FROM matches')
    scored=[]
    pair=re.split(r'\s+(?:vs|v|contra)\s+', qnorm, maxsplit=1)
    explicit_pair=len(pair)==2 and all(pair)
    def team_match(value, wanted):
        value=value.strip(); wanted=wanted.strip()
        return bool(value and wanted and (value==wanted or (len(wanted)>=4 and wanted in value) or (len(value)>=4 and value in wanted)))
    for m in rows:
        home=norm(m.get('home','')); away=norm(m.get('away','')); comp=norm(m.get('competition',''))
        text=f'{home} {away} {comp}'
        score=0
        exact_sides=False
        if explicit_pair:
            ph,pa=pair
            if team_match(home,ph) and team_match(away,pa):
                score += 500; exact_sides=True
            elif team_match(home,pa) and team_match(away,ph):
                score += 220
            else:
                # An explicit pair is a hard semantic constraint. Never score an
                # unrelated fixture merely because one token appears in its text.
                continue
        if qnorm and qnorm in text: score += 80
        if all(t in text for t in toks): score += 45
        for side in (home,away):
            if side and any(t in side for t in toks): score += 12
        try: d=dt.date.fromisoformat(str(m.get('date',''))[:10])
        except Exception: d=dt.date.min
        if d >= today:
            score += 120
            temporal=(0,(d-today).days)
        elif (today-d).days <= 14:
            score += 15
            temporal=(1,(today-d).days)
        else:
            temporal=(2,(today-d).days)
        if m.get('status')!='finished': score += 4
        if score>0: scored.append((score,temporal,0 if exact_sides else 1,m))
    scored.sort(key=lambda z:(-z[0],z[1],z[2],z[3].get('date',''),z[3].get('time','')))
    return [dict(enrich_lifecycle(m),search_score=s) for s,_,__,m in scored[:limit]]

def study(repo,q,match_id=None):
    q=q.strip()
    if match_id:
        # Exact-ID path: never let fuzzy search replace the selected fixture.
        m=repo.one('SELECT * FROM matches WHERE id=?',(str(match_id),))
        if not m:
            return {'found':False,'reason':'match_id no encontrado','query':q,'candidates':[]}
        cand=[dict(enrich_lifecycle(m),search_score=999)]
    else:
        cand=search_matches(repo,q,limit=8)
        if not cand:
            return {'found':False,'reason':'No se encontró una coincidencia en el índice local de LiAn. No se inventaron datos.','query':q,'candidates':[],'request_required':True}
        # Auto-select only when clearly unambiguous; otherwise expose choices.
        top=cand[0]; second=cand[1] if len(cand)>1 else None
        ambiguous=bool(second and top['search_score']-second['search_score']<18 and norm(top.get('home','')+' '+top.get('away',''))!=norm(second.get('home','')+' '+second.get('away','')))
        if ambiguous:
            return {'found':False,'ambiguous':True,'query':q,'reason':'Se encontraron varios partidos compatibles. Selecciona uno para evitar analizar el encuentro equivocado.','candidates':cand}
        m=top
    pred=Model(repo).predict(m)
    stored=repo.one('SELECT * FROM predictions WHERE match_id=? ORDER BY generated_at ASC LIMIT 1',(m['id'],))
    result=dict(m,**pred)
    result['search_score']=m.get('search_score',999 if match_id else 0); result['prediction_source']='CURRENT_MODEL'
    if stored:
        result['stored_pre_match_prediction']={'pick':stored['pick'],'p_home':stored['p_home'],'p_draw':stored['p_draw'],'p_away':stored['p_away'],'model_version':stored['model_version'],'generated_at':stored['generated_at']}
    if m.get('status')=='finished' and m.get('home_score') is not None:
        actual='1' if int(m['home_score'])>int(m['away_score']) else 'X' if int(m['home_score'])==int(m['away_score']) else '2'
        result['historical_result']={'actual':actual,'final':f"{m['home_score']}–{m['away_score']}",'pre_match_pick':stored['pick'] if stored else None,'pre_match_correct':bool(stored and stored['pick']==actual)}
        if stored: result['prediction_source']='IMMUTABLE_PRE_MATCH_RECORD'
    if match_id:
        result['prediction_timeline']=repo.rows('SELECT model_version,p_home,p_draw,p_away,pick,confidence,evidence,created_at FROM model_runs WHERE match_id=? ORDER BY created_at',(str(match_id),))
        result['evidence_timeline']=repo.rows('SELECT model_version,collected_at,source_count,historical_matches,h2h_matches,feature_count,quality FROM evidence_snapshots WHERE match_id=? ORDER BY collected_at',(str(match_id),))
        result['resolution']='CANONICAL_MATCH_ID'
    return {'found':True,'query':q,'match':result,'candidates':cand}
