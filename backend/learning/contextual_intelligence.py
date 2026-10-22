from __future__ import annotations
import math
from collections import defaultdict
class ContextualIntelligence:
    VERSION='63.0.0'
    def __init__(self,repo): self.r=repo
    def league_profile(self,competition_id,before):
        rows=self.r.rows('SELECT home_score,away_score FROM matches WHERE status="finished" AND date<? AND competition_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY date DESC,id DESC LIMIT 80',(before,competition_id))
        if not rows:return {'samples':0,'home_goals':1.35,'away_goals':1.15,'p1':.40,'px':.28,'p2':.32,'volatility':.5}
        n=len(rows); hg=sum(float(x['home_score']) for x in rows)/n; ag=sum(float(x['away_score']) for x in rows)/n
        p1=sum(x['home_score']>x['away_score'] for x in rows)/n; px=sum(x['home_score']==x['away_score'] for x in rows)/n
        totals=[float(x['home_score'])+float(x['away_score']) for x in rows]; mean=sum(totals)/n; var=sum((v-mean)**2 for v in totals)/n
        return {'samples':n,'home_goals':hg,'away_goals':ag,'p1':p1,'px':px,'p2':1-p1-px,'volatility':min(1,math.sqrt(var)/2.2)}
    def team_fatigue(self,team,target_date):
        rows=self.r.rows('SELECT date FROM matches WHERE status="finished" AND date<? AND (lower(home)=lower(?) OR lower(away)=lower(?)) ORDER BY date DESC LIMIT 5',(target_date,team,team))
        if not rows:return {'score':0,'matches_14d':0,'matches_7d':0}
        from datetime import date
        d=date.fromisoformat(target_date); m7=sum((d-date.fromisoformat(x['date'])).days<=7 for x in rows); m14=sum((d-date.fromisoformat(x['date'])).days<=14 for x in rows)
        return {'score':-min(.12,.04*max(0,m7-1)+.015*max(0,m14-3)),'matches_14d':m14,'matches_7d':m7}
    @staticmethod
    def q(x,default=.5):
        try:return max(0,min(1,float(x)))
        except:return default
    def evaluate(self,m,base):
        prof=self.league_profile(m.get('competition_id') or '',m['date']); hf=self.team_fatigue(m['home'],m['date']); af=self.team_fatigue(m['away'],m['date'])
        def rest(v):
            if v is None:return 0
            if v<3:return -.08
            if v<4:return -.045
            if v<5:return -.018
            if v<=9:return 0
            return -.008*min(4,v-9)
        rh,ra=rest(base.get('rest_days_home')),rest(base.get('rest_days_away')); th=float(base.get('travel_km_home') or 0); ta=float(base.get('travel_km_away') or 0)
        travel=max(-.08,min(.08,(ta-th)/10000)); lineup=(self.q(m.get('lineup_home_quality'))-self.q(m.get('lineup_away_quality')))*.08 if ('lineup_home_quality' in m or 'lineup_away_quality' in m) else 0
        fitness=(self.q(m.get('fitness_home'))-self.q(m.get('fitness_away')))*.06 if ('fitness_home' in m or 'fitness_away' in m) else 0
        weather=(self.q(m.get('weather_home_quality'))-self.q(m.get('weather_away_quality')))*.025 if ('weather_home_quality' in m or 'weather_away_quality' in m) else 0
        ref=0
        if 'referee_home_edge' in m:
            try:ref=max(-.05,min(.05,float(m['referee_home_edge'])))
            except:pass
        league=(prof['p1']-prof['p2'])*.035 if prof['samples']>=12 else 0
        hd=rh-ra+lineup+fitness+weather+ref+(hf['score']-af['score'])+travel+league
        return {'league_profile':prof,'fatigue_home':hf,'fatigue_away':af,'rest_effect_home':rh,'rest_effect_away':ra,'travel_effect':travel,'lineup_delta':lineup,'fitness_delta':fitness,'weather_delta':weather,'referee_delta':ref,'league_delta':league,'home_delta':hd,'away_delta':-hd,'data_quality':sum(k in m for k in ('lineup_home_quality','lineup_away_quality','fitness_home','fitness_away','weather_home_quality','weather_away_quality','referee_home_edge'))/7}
    def recent_study(self,limit=80):
        rows=self.r.rows('SELECT competition,competition_id,date,home,away,home_score,away_score FROM matches WHERE status="finished" ORDER BY date DESC,id DESC LIMIT ?',(limit,)); by=defaultdict(list)
        for x in rows:by[x['competition']].append(x)
        out=[]
        for comp,v in by.items():
            n=len(v); hr=sum(x['home_score']>x['away_score'] for x in v)/n; dr=sum(x['home_score']==x['away_score'] for x in v)/n
            out.append({'competition':comp,'samples':n,'avg_goals':round(sum(x['home_score']+x['away_score'] for x in v)/n,3),'home_rate':round(hr,3),'draw_rate':round(dr,3),'away_rate':round(1-hr-dr,3)})
        return {'matches_studied':len(rows),'by_competition':sorted(out,key=lambda x:x['samples'],reverse=True)}
