from datetime import datetime
from zoneinfo import ZoneInfo
MX = ZoneInfo('America/Mexico_City')

def mexico_today():
    return datetime.now(MX).date()

def mexico_today_iso():
    return mexico_today().isoformat()
