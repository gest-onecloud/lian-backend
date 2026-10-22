"""Deterministic match lifecycle and UI status rules.

A match cannot remain visually "PRÓXIMO" once its Mexico date has passed.
The lifecycle is conservative: a past fixture without a verified score is shown as
"RESULTADO PENDIENTE" rather than inventing a final score.
"""
from __future__ import annotations
import datetime as dt
from .timezone import MX

def lifecycle(match, now=None):
    now = now or dt.datetime.now(MX)
    today = now.date()
    try:
        d = dt.date.fromisoformat(str(match.get('date',''))[:10])
    except Exception:
        d = None
    hs, aw = match.get('home_score'), match.get('away_score')
    has_score = hs is not None and aw is not None and str(hs) != '' and str(aw) != ''
    raw = str(match.get('status') or '').lower()
    live = raw in {'inprogress','in_progress','live','halftime','1h','2h','ht','playing','paused'}
    # A future-dated fixture can carry a stale/mis-mapped provider status such as
    # "finished". Mexico-local calendar date is the authoritative temporal guard:
    # a fixture whose date is still in the future must never render as FINALIZADO.
    if d is not None and d > today:
        label='PRÓXIMO'; code='scheduled'
    elif has_score:
        label='FINALIZADO'; code='finished'
    elif raw in {'finished','final','ft','aet','after extra time','match finished','post'}:
        label='FINALIZADO'; code='finished'
    elif d is not None and d < today:
        label='RESULTADO PENDIENTE'; code='past_pending_result'
    elif d == today and live:
        label='EN VIVO'; code='live'
    else:
        label='PRÓXIMO'; code='scheduled'
    result = None
    if has_score:
        result = f'{hs}–{aw}'
    return {'code':code,'label':label,'result':result,'date_passed':bool(d is not None and d < today),'has_verified_score':has_score}

def enrich(match, now=None):
    x=lifecycle(match,now)
    out=dict(match)
    out['lifecycle']=x
    out['display_status']=x['label']
    if x['result'] is not None: out['display_result']=x['result']
    return out
