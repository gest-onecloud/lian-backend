"""Mexico-time presentation for fixtures.
Only converts when the source timezone is known. Match-specific official overrides
have priority; unknown timezone is explicitly marked instead of inventing a time.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
MX=ZoneInfo('America/Mexico_City')
OFFICIAL_MX_TIMES={
 'cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc':'17:30',
 'cal-2026-08-25-concacaf-leagues-club-león-real-salt-lake':'20:30',
}
COMP_TZ={'EN-CARABAO':'Europe/London','ES-LALIGA':'Europe/Madrid','DE-BUND':'Europe/Berlin','IT-SERIEA':'Europe/Rome','FR-L1':'Europe/Paris','EN-PL':'Europe/London','MX-LIGA':'America/Mexico_City','MX-COPA':'America/Mexico_City','MLS':'America/New_York'}
def mexico_time(match):
    mid=str(match.get('id',''))
    if mid in OFFICIAL_MX_TIMES:return {'date_mx':match.get('date'),'time_mx':OFFICIAL_MX_TIMES[mid],'status':'VERIFICADA','source':'horario oficial de competición/club'}
    raw=str(match.get('time') or '').strip()
    if not raw or ':' not in raw:return {'date_mx':match.get('date'),'time_mx':None,'status':'NO VERIFICADA','source':'sin hora de fuente'}
    tz=COMP_TZ.get(str(match.get('competition_id') or ''))
    if not tz:
        country=str(match.get('country') or '').lower(); tz={'inglaterra':'Europe/London','españa':'Europe/Madrid','alemania':'Europe/Berlin','italia':'Europe/Rome','francia':'Europe/Paris','méxico':'America/Mexico_City','mexico':'America/Mexico_City','estados unidos':'America/New_York'}.get(country)
    if not tz:return {'date_mx':match.get('date'),'time_mx':None,'status':'NO VERIFICADA','source':'zona horaria de sede no verificada'}
    try:
        dt=datetime.fromisoformat(f"{match['date']}T{raw}:00").replace(tzinfo=ZoneInfo(tz)); mx=dt.astimezone(MX)
        return {'date_mx':mx.date().isoformat(),'time_mx':mx.strftime('%H:%M'),'status':'CONVERTIDA','source':tz}
    except Exception:return {'date_mx':match.get('date'),'time_mx':None,'status':'NO VERIFICADA','source':'error de conversión'}
def label(match):
    x=mexico_time(match); return f"{x['date_mx']} · {x['time_mx']} MX" if x['time_mx'] else f"{match.get('date','')} · hora MX no verificada"
