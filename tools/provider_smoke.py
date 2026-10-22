from __future__ import annotations
import datetime as dt, json, sys, urllib.request
from zoneinfo import ZoneInfo
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from backend.services.http_client import get_json

MX=ZoneInfo('America/Mexico_City')
date=dt.datetime.now(MX).date().isoformat()
checks=[
 ('ESPN_ALL',f'https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date.replace("-","")}'),
 ('ESPN_ALL_ALT',f'https://site.web.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date.replace("-","")}'),
 ('SOFASCORE',f'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}'),
 ('FOTMOB',f'https://www.fotmob.com/api/matches?date={date.replace("-","")}'),
 ('THESPORTSDB',f'https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={date}&s=Soccer'),
]
failed=0
for name,url in checks:
    try:
        data=get_json(url,timeout=8)
        if name.startswith('ESPN'): n=len(data.get('events') or [])
        elif name=='SOFASCORE': n=len(data.get('events') or [])
        elif name=='FOTMOB': n=sum(len(x.get('matches') or []) for x in (data.get('leagues') or []))
        else: n=len(data.get('events') or [])
        print(f'[OK] {name}: HTTP JSON OK, registros={n}')
    except Exception as ex:
        failed+=1; print(f'[FAIL] {name}: {ex}')
print(f'FECHA_MX={date} FALLAS={failed}/{len(checks)}')
sys.exit(1 if failed else 0)
