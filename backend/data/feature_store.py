import json, math
from collections import defaultdict

class FeatureStore:
    """Temporal feature store. Every feature uses only finished matches strictly before as_of."""
    def __init__(self, repo):
        self.r = repo
        self._baseline_cache={}
        self._opponent_cache={}
        self._team_cache={}
        self._league_cache={}
        self._h2h_cache={}
        self._elo_cache={}

    @staticmethod
    def _avg(xs): return sum(xs)/len(xs) if xs else None
    def _elo_as_of(self, as_of):
        if as_of in self._elo_cache: return self._elo_cache[as_of]
        rows=self.r.rows("SELECT date,home,away,home_score,away_score FROM matches WHERE status='finished' AND date<? ORDER BY date ASC,id ASC",(as_of,))
        ratings={}
        def k(s): return str(s or '').strip().lower()
        for r in rows:
            h,a=k(r['home']),k(r['away']); rh=ratings.get(h,1500.); ra=ratings.get(a,1500.)
            exp=1/(1+10**((ra-rh)/400)); act=1 if r['home_score']>r['away_score'] else .5 if r['home_score']==r['away_score'] else 0
            mult=22 if abs(r['home_score']-r['away_score'])>=2 else 20
            ratings[h]=rh+mult*(act-exp); ratings[a]=ra+mult*((1-act)-(1-exp))
        self._elo_cache[as_of]=ratings; return ratings


    @staticmethod
    def _weighted(xs, half_life=8.0):
        if not xs: return None
        vals=[]; weights=[]
        for i,v in enumerate(xs):
            w=math.exp(-math.log(2)*i/half_life)
            vals.append(v*w); weights.append(w)
        return sum(vals)/sum(weights)

    def _league_goal_baseline(self, competition_id, as_of):
        ck=(competition_id,as_of)
        if ck in self._baseline_cache:return self._baseline_cache[ck]
        r=self.r.one('''SELECT AVG(home_score) hg, AVG(away_score) ag
                        FROM matches WHERE status='finished' AND competition_id=? AND date<?''',(competition_id,as_of))
        if not r or r['hg'] is None or r['ag'] is None:
            self._baseline_cache[ck]=1.35; return 1.35
        value=max(.65,(float(r['hg'])+float(r['ag']))/2); self._baseline_cache[ck]=value; return value

    def _opponent_profile(self, opponent, as_of, competition_id=None, limit=30):
        ck=(str(opponent).lower(),as_of,competition_id,limit)
        if ck in self._opponent_cache:return self._opponent_cache[ck]
        if competition_id:
            rows=self.r.rows('''SELECT home,away,home_score,away_score FROM matches
                WHERE status='finished' AND date<? AND competition_id=?
                AND (lower(home)=lower(?) OR lower(away)=lower(?))
                ORDER BY date DESC LIMIT ?''',(as_of,competition_id,opponent,opponent,limit))
        else:
            rows=self.r.rows('''SELECT home,away,home_score,away_score FROM matches
                WHERE status='finished' AND date<? AND (lower(home)=lower(?) OR lower(away)=lower(?))
                ORDER BY date DESC LIMIT ?''',(as_of,opponent,opponent,limit))
        gf=[]; ga=[]
        for r in rows:
            is_home=str(r['home']).lower()==str(opponent).lower()
            gf.append(float((r['home_score'] if is_home else r['away_score']) or 0))
            ga.append(float((r['away_score'] if is_home else r['home_score']) or 0))
        value={'gf':self._weighted(gf[:10]),'ga':self._weighted(ga[:10]),'matches':len(rows)}
        self._opponent_cache[ck]=value
        return value

    def team(self, team, as_of, limit=20, competition_id=None):
        ck=(str(team).lower(),as_of,limit,competition_id)
        if ck in self._team_cache:return self._team_cache[ck]
        rows=self.r.rows('''SELECT m.*,s.* FROM matches m LEFT JOIN match_stats s ON s.match_id=m.id
            WHERE m.status='finished' AND m.date<? AND (lower(m.home)=lower(?) OR lower(m.away)=lower(?))
            ORDER BY m.date DESC LIMIT ?''',(as_of,team,team,limit))
        gf=[]; ga=[]; pts=[]; shots=[]; sot=[]; corners=[]; fouls=[]; yellows=[]; reds=[]; xg=[]; xga=[]
        adj_gf=[]; adj_ga=[]; adj_xg=[]; adj_xga=[]; sos=[]; home_n=away_n=0; home_pts=[]; away_pts=[]
        baseline=self._league_goal_baseline(competition_id,as_of) if competition_id else 1.35
        for x in rows:
            is_home=str(x['home']).lower()==str(team).lower(); opponent=x['away'] if is_home else x['home']
            elo_map=self._elo_as_of(x['date']); sos.append(float(elo_map.get(str(opponent).strip().lower(),1500.0)))
            f=float((x['home_score'] if is_home else x['away_score']) or 0); a=float((x['away_score'] if is_home else x['home_score']) or 0)
            gf.append(f); ga.append(a); pts.append(3 if f>a else 1 if f==a else 0)
            if is_home: home_n+=1; home_pts.append(3 if f>a else 1 if f==a else 0)
            else: away_n+=1; away_pts.append(3 if f>a else 1 if f==a else 0)
            shots.append(x['home_shots'] if is_home else x['away_shots']); xg.append(x['home_xg'] if is_home else x['away_xg'])
            xga.append(x['away_xga'] if is_home else x['home_xga']); sot.append(x['home_sot'] if is_home else x['away_sot'])
            corners.append(x['home_corners'] if is_home else x['away_corners']); fouls.append(x['home_fouls'] if is_home else x['away_fouls'])
            yellows.append(x['home_yellow'] if is_home else x['away_yellow']); reds.append(x['home_red'] if is_home else x['away_red'])
            op=self._opponent_profile(opponent,x['date'],competition_id,20)
            op_ga=op.get('ga') or baseline; op_gf=op.get('gf') or baseline
            # Opponent-adjusted production: strong defensive opponents make a goal more valuable;
            # strong attacks make conceded goals more damaging. Clamp to prevent tiny samples exploding.
            adj_factor_for= max(.70,min(1.45,baseline/max(.35,op_ga)))
            adj_factor_against=max(.70,min(1.45,baseline/max(.35,op_gf)))
            adj_gf.append(f*adj_factor_for); adj_ga.append(a*adj_factor_against)
            xv=x['home_xg'] if is_home else x['away_xg']; xva=x['away_xga'] if is_home else x['home_xga']
            if xv is not None: adj_xg.append(float(xv)*adj_factor_for)
            if xva is not None: adj_xga.append(float(xva)*adj_factor_against)
        def nz(a): return [float(v) for v in a if v is not None]
        gf10=self._weighted(gf[:10]); ga10=self._weighted(ga[:10]); gf5=self._weighted(gf[:5]); ga5=self._weighted(ga[:5])
        ppg10=self._weighted(pts[:10]); ppg5=self._weighted(pts[:5])
        momentum=(ppg5-ppg10) if ppg5 is not None and ppg10 is not None else 0
        goal_momentum=((gf5-ga5)-(gf10-ga10)) if gf5 is not None and ga5 is not None and gf10 is not None and ga10 is not None else 0
        mean_gf=self._avg(gf[:10]); var_gf=self._avg([(v-(mean_gf or 0))**2 for v in gf[:10]]) if gf else None
        consistency=1/(1+math.sqrt(max(0,var_gf or 0))) if var_gf is not None else .5
        value={
            'matches':len(rows),'home_matches':home_n,'away_matches':away_n,
            'gf5':gf5,'ga5':ga5,'gf10':gf10,'ga10':ga10,'ppg10':ppg10,'ppg5':ppg5,
            'shots10':self._weighted(nz(shots[:10])),'sot10':self._weighted(nz(sot[:10])),
            'xg10':self._weighted(nz(xg[:10])),'xga10':self._weighted(nz(xga[:10])),
            'adj_gf10':self._weighted(adj_gf[:10]),'adj_ga10':self._weighted(adj_ga[:10]),
            'adj_xg10':self._weighted(adj_xg[:10]),'adj_xga10':self._weighted(adj_xga[:10]),
            'goal_diff10':self._weighted([g-a for g,a in zip(gf[:10],ga[:10])]),
            'adj_goal_diff10':self._weighted([g-a for g,a in zip(adj_gf[:10],adj_ga[:10])]),
            'corners10':self._weighted(nz(corners[:10])),'fouls10':self._weighted(nz(fouls[:10])),
            'yellow10':self._weighted(nz(yellows[:10])),'red10':self._weighted(nz(reds[:10])),
            'home_ppg10':self._weighted(home_pts[:10]),'away_ppg10':self._weighted(away_pts[:10]),
            'sos10':self._weighted(sos[:10]),'opponent_strength10':self._weighted(sos[:10]),
            'momentum':momentum,'goal_momentum':goal_momentum,'consistency':consistency,
            'availability':sum(v is not None for v in shots+sot+corners+fouls+yellows+reds+xg+xga)/max(1,8*len(rows)),
        }
        self._team_cache[ck]=value
        return value

    def league(self, competition_id, as_of):
        ck=(competition_id,as_of)
        if ck in self._league_cache:return self._league_cache[ck]
        rows=self.r.rows('''SELECT home_score,away_score FROM matches WHERE status='finished' AND competition_id=? AND date<?''',(competition_id,as_of))
        if not rows:
            value={'matches':0,'avg_home_goals':None,'avg_away_goals':None,'draw_rate':None,'home_advantage':None}; self._league_cache[ck]=value; return value
        hg=[r['home_score'] or 0 for r in rows]; ag=[r['away_score'] or 0 for r in rows]
        dr=sum((r['home_score'] or 0)==(r['away_score'] or 0) for r in rows)/len(rows)
        value={'matches':len(rows),'avg_home_goals':self._avg(hg),'avg_away_goals':self._avg(ag),'draw_rate':dr,'home_advantage':self._avg(hg)-self._avg(ag)}; self._league_cache[ck]=value; return value

    def h2h(self, home, away, as_of, limit=8):
        return self.r.rows('''SELECT * FROM matches WHERE status='finished' AND date<?
          AND ((home=? AND away=?) OR (home=? AND away=?)) ORDER BY date DESC LIMIT ?''',(as_of,home,away,away,home,limit))

    def snapshot(self, match):
        as_of=match['date']; hs=self.team(match['home'],as_of,20,match.get('competition_id')); aw=self.team(match['away'],as_of,20,match.get('competition_id')); lg=self.league(match['competition_id'],as_of); h2h=self.h2h(match['home'],match['away'],as_of)
        return {'match_id':match['id'],'as_of':as_of,'home':hs,'away':aw,'league':lg,'h2h_count':len(h2h),'quality':self.quality(hs,aw,lg)}

    @staticmethod
    def quality(home, away, league):
        team_cov=(home['matches']>0)+(away['matches']>0); stat_cov=(home['availability']+away['availability'])/2; league_cov=1 if league['matches']>=10 else min(1,league['matches']/10)
        return round(min(1,0.25*team_cov+0.45*stat_cov+0.30*league_cov),4)

    def persist_snapshot(self, match):
        snap=self.snapshot(match); self.r.execute('INSERT INTO feature_snapshots(match_id,as_of,feature_json,source_quality) VALUES(?,?,?,?)',(match['id'],snap['as_of'],json.dumps(snap,ensure_ascii=False),snap['quality'])); return snap
