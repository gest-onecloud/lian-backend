"""Venue and hosting intelligence.

The service is deliberately isolated from the prediction model.  It distinguishes
fixture order (nominal home) from the actual venue/hosting side.  Verified
match-specific facts take precedence over generic home-field assumptions.
"""
from math import radians, sin, cos, sqrt, atan2
from ..data.competitions import CATALOG

# Match-specific facts verified for the 2026 Leagues Cup quarterfinals and
# selected common fixtures used by LiAn's current bundled calendar.
MATCH_VENUES = {
    'cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc': {
        'venue':'SeatGeek Stadium','city':'Bridgeview','region':'Illinois','country':'USA',
        'venue_side':'away','hosting_team':'Chicago Fire FC','neutral':False,
        'verified':True,'source':'Leagues Cup / Chicago Fire official',
        'source_url':'https://www.leaguescup.com/news/leagues-cup-2026-quarterfinal-schedule-and-venues-announced'
    },
    'cal-2026-08-25-concacaf-leagues-club-león-real-salt-lake': {
        'venue':"Dick's Sporting Goods Park",'city':'Commerce City','region':'Colorado','country':'USA',
        'venue_side':'away','hosting_team':'Real Salt Lake','neutral':False,
        'verified':True,'source':'Leagues Cup official',
        'source_url':'https://www.leaguescup.com/news/leagues-cup-2026-quarterfinal-schedule-and-venues-announced'
    },
}

TEAM_VENUES = {
    'cf monterrey': {'venue':'Estadio BBVA','city':'Guadalupe','region':'Nuevo León','country':'Mexico','lat':25.6698,'lon':-100.244},
    'monterrey': {'venue':'Estadio BBVA','city':'Guadalupe','region':'Nuevo León','country':'Mexico','lat':25.6698,'lon':-100.244},
    'chicago fire fc': {'venue':'SeatGeek Stadium','city':'Bridgeview','region':'Illinois','country':'USA','lat':41.7637,'lon':-87.8068},
    'valencia': {'venue':'Mestalla','city':'Valencia','region':'Valencia','country':'Spain','lat':39.4748,'lon':-0.3583},
    'real betis': {'venue':'Estadio Benito Villamarín','city':'Seville','region':'Andalusia','country':'Spain','lat':37.3565,'lon':-5.9818},
}

VENUE_COORDS = {
    'seatgeek stadium': (41.7637,-87.8068),
    "dick's sporting goods park": (39.805,-104.891),
    'mestalla': (39.4748,-0.3583),
    'estadio bbva': (25.6698,-100.244),
    'estadio benito villamarín': (37.3565,-5.9818),
}

def _norm(v):
    return ' '.join(str(v or '').strip().lower().split())

def haversine(a,b):
    if not a or not b: return None
    lat1,lon1=a; lat2,lon2=b
    R=6371.0
    p1,p2=radians(lat1),radians(lat2)
    dp=radians(lat2-lat1); dl=radians(lon2-lon1)
    h=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
    return round(2*R*atan2(sqrt(h),sqrt(max(0,1-h))))

def resolve(match):
    mid=match.get('id')
    if mid in MATCH_VENUES:
        v=dict(MATCH_VENUES[mid])
        v['status']='VERIFICADA'
        v['advantage_side']=v['venue_side'] if not v['neutral'] else None
    else:
        home=_norm(match.get('home')); away=_norm(match.get('away'))
        hv=TEAM_VENUES.get(home)
        av=TEAM_VENUES.get(away)
        if hv:
            v={**hv,'venue_side':'home','hosting_team':match.get('home'),'neutral':False,'verified':True,
               'source':'Registro de sede LiAn','source_url':None,'status':'VERIFICADA','advantage_side':'home'}
        elif av:
            v={**av,'venue_side':'away','hosting_team':match.get('away'),'neutral':False,'verified':True,
               'source':'Registro de sede LiAn','source_url':None,'status':'VERIFICADA','advantage_side':'away'}
        else:
            # Never invent a venue.  For normal league fixtures we can infer the
            # conventional home side, but explicitly label the inference.
            v={'venue':None,'city':None,'region':None,'country':None,'venue_side':'home',
               'hosting_team':match.get('home'),'neutral':False,'verified':False,
               'source':'Inferencia por orden del fixture','source_url':None,
               'status':'INFERIDA','advantage_side':'home'}
    return v

def team_travel(match, venue):
    vc=VENUE_COORDS.get(_norm(venue.get('venue')))
    if not vc: return {'home_km':None,'away_km':None,'difference_km':None}
    hk=TEAM_VENUES.get(_norm(match.get('home')),{}); ak=TEAM_VENUES.get(_norm(match.get('away')), {})
    home_origin=(hk.get('lat'),hk.get('lon')) if hk.get('lat') is not None else None
    away_origin=(ak.get('lat'),ak.get('lon')) if ak.get('lat') is not None else None
    h=haversine(home_origin,vc); a=haversine(away_origin,vc)
    return {'home_km':h,'away_km':a,'difference_km':None if h is None or a is None else abs(a-h)}
