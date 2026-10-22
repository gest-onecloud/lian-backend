import re, unicodedata, datetime as dt, json, os, urllib.request
from ..core.model import Model
from .match_lifecycle import enrich as enrich_lifecycle

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def aliases(s):
    n=norm(s); return set([n, n.replace(' fc',''), n.replace(' cf',''), n.replace(' club','')])

def resolve(repo, query, limit=12):
    """Resolve only semantically relevant local fixtures.

    IMPORTANT: temporal freshness is a ranking signal, never a relevance signal.
    A future match must not appear merely because it is future. Explicit A vs B
    queries require both sides to match; single-team queries require the team to
    match a fixture side (competition-only queries may match the competition).
    """
    q=norm(query); toks=[x for x in q.split() if len(x)>1]
    if not toks: return []
    today=dt.datetime.now().date()
    pair=re.split(r'\s+(?:vs|v|contra)\s+', q, maxsplit=1)
    explicit_pair=len(pair)==2 and all(pair)
    rows=repo.rows('SELECT * FROM matches')
    scored=[]
    def tm(v,w):
        v=v.strip(); w=w.strip()
        return bool(v and w and (v==w or (len(w)>=4 and w in v) or (len(v)>=4 and v in w)))
    for m in rows:
        h=norm(m.get('home')); a=norm(m.get('away')); c=norm(m.get('competition'))
        text=f'{h} {a} {c}'
        score=0; exact=0; relevant=False; orientation=0
        if explicit_pair:
            ph,pa=pair
            if tm(h,ph) and tm(a,pa):
                score+=500; exact=2; relevant=True; orientation=2
            elif tm(h,pa) and tm(a,ph):
                score+=180; exact=1; relevant=True; orientation=1
            # For A vs B, tokens in unrelated matches are NOT relevance.
            if not relevant:
                continue
        else:
            side_match=False
            for t in toks:
                if (len(t)>=4 and (t in h or t in a)) or t==h or t==a:
                    side_match=True; score+=18
            comp_match=all(t in c for t in toks) if toks else False
            # A one-team query must hit a team side. Competition queries remain supported.
            if side_match:
                relevant=True
            elif comp_match:
                relevant=True; score+=12
            if not relevant:
                continue
            if q and q in text: score+=80
            if all(t in text for t in toks): score+=45
        try: d=dt.date.fromisoformat(str(m.get('date',''))[:10])
        except Exception: d=dt.date.min
        if d>=today:
            temporal=(0,(d-today).days); score+=120
        elif (today-d).days<=14:
            temporal=(1,(today-d).days); score+=15
        else:
            temporal=(2,(today-d).days)
        if m.get('status')!='finished': score+=3
        scored.append((score,temporal,-exact,-orientation,m))
    scored.sort(key=lambda x:(-x[0],x[1],x[2],x[3],x[4].get('date',''),x[4].get('time','')))
    return [dict(enrich_lifecycle(m),resolve_score=s) for s,_,__,___,m in scored[:limit]]

def canonical(repo, query, match_id=None):
    if match_id:
        m=repo.one('SELECT * FROM matches WHERE id=?',(match_id,)); cand=[m] if m else []
    else: cand=resolve(repo,query)
    if not cand: return {'found':False,'query':query,'reason':'No existe coincidencia en el índice LiAn; no se inventan partidos.'}
    if len(cand)>1 and cand[0]['resolve_score']-cand[1]['resolve_score']<20:
        return {'found':False,'ambiguous':True,'query':query,'candidates':cand}
    m=enrich_lifecycle(cand[0]); pred=Model(repo).predict(m)
    stored=repo.one('SELECT * FROM predictions WHERE match_id=? ORDER BY generated_at ASC LIMIT 1',(m['id'],))
    timeline=repo.rows('SELECT model_version,p_home,p_draw,p_away,pick,confidence,evidence,created_at FROM model_runs WHERE match_id=? ORDER BY created_at',(m['id'],))
    evidence=repo.rows('SELECT model_version,collected_at,source_count,historical_matches,h2h_matches,feature_count,quality FROM evidence_snapshots WHERE match_id=? ORDER BY collected_at',(m['id'],))
    result=dict(m,**pred); result['canonical_id']=m['id']; result['stored_pre_match_prediction']=stored; result['prediction_timeline']=timeline; result['evidence_timeline']=evidence
    if m.get('status')=='finished' and m.get('home_score') is not None:
        actual='1' if int(m['home_score'])>int(m['away_score']) else 'X' if int(m['home_score'])==int(m['away_score']) else '2'
        result['historical_result']={'actual':actual,'final':f"{m['home_score']}–{m['away_score']}", 'pre_match_pick':stored.get('pick') if stored else None, 'pre_match_correct':bool(stored and stored.get('pick')==actual)}
    return {'found':True,'query':query,'match':result,'candidates':cand}

def data_health(repo):
    now=dt.datetime.utcnow(); rows=repo.rows('SELECT source,kind,priority,enabled,last_success,last_failure,failures FROM source_registry ORDER BY priority')
    fresh=0; stale=0
    for r in rows:
        try:
            t=dt.datetime.fromisoformat((r.get('last_success') or '').replace('Z','+00:00')).replace(tzinfo=None)
            (fresh if (now-t).total_seconds()<86400 else stale)
            if (now-t).total_seconds()<86400: fresh+=1
            else: stale+=1
        except: stale+=1
    return {'sources':rows,'enabled':sum(int(r['enabled'] or 0) for r in rows),'fresh_24h':fresh,'stale_or_unknown':stale,'policy':'Local-first, multi-source, deduplicated, provenance required; no paid football API is mandatory.'}
