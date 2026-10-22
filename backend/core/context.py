from datetime import date
from ..services.venue import resolve, team_travel
from ..learning.live_context import LiveContextEngine
import json

class ContextEngine:
    def __init__(self,repo): self.r=repo; self.live=LiveContextEngine(repo)

    def _last_date(self, team, before):
        r=self.r.one('''SELECT date FROM matches WHERE status='finished' AND date<?
                       AND (lower(home)=lower(?) OR lower(away)=lower(?)) ORDER BY date DESC LIMIT 1''',(before,team,team))
        return r['date'] if r else None

    @staticmethod
    def _days(a,b):
        if not a or not b:return None
        try:return (date.fromisoformat(a)-date.fromisoformat(b)).days
        except Exception:return None

    def evaluate(self,match):
        v=resolve(match)
        hlast=self._last_date(match['home'],match['date']); alast=self._last_date(match['away'],match['date'])
        rest_h=self._days(match['date'],hlast); rest_a=self._days(match['date'],alast)
        travel=team_travel(match,v)
        live=self.live.get(match['id'])
        lp=live.get('payload',{}) if isinstance(live,dict) else {}
        if isinstance(lp,dict):
            for k,val in lp.items():
                if match.get(k) is None: match[k]=val
            w=lp.get('weather') or {}
        else: w={}
        available=sum(x is not None for x in [rest_h,rest_a,travel.get('home_km'),travel.get('away_km'),v.get('venue')])
        return {
            'venue':v,
            'rest_days_home':rest_h,'rest_days_away':rest_a,
            'travel_km_home':travel.get('home_km'),'travel_km_away':travel.get('away_km'),
            'travel_difference_km':travel.get('difference_km'),
            'altitude_delta':None,'weather_quality':w.get('quality'),'weather_temperature_c':w.get('temperature_c'),'weather_precipitation_probability':w.get('precipitation_probability'),'weather_wind_kmh':w.get('wind_kmh'),'referee_quality':1.0 if match.get('referee') else None,
            'lineup_quality_home':match.get('lineup_home_quality'),'lineup_quality_away':match.get('lineup_away_quality'),'fitness_home':match.get('fitness_home'),'fitness_away':match.get('fitness_away'),'xi_status':match.get('xi_status'),
            'live_context_quality':live.get('quality',0) if isinstance(live,dict) else 0,
            'available_fields':available
        }
