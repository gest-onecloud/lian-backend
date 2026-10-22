import json, math, random, unicodedata
from pathlib import Path
from ..data.feature_store import FeatureStore
from .player import PlayerEngine
from .context import ContextEngine
from ..services.explainability import explain
from ..services.professional_markets import ProfessionalMarkets
from ..learning.adaptive_engine import AdaptiveLearningEngine
from ..learning.contextual_intelligence import ContextualIntelligence
from ..learning.ensemble import ProfessionalEnsemble
from ..learning.historical_intelligence import HistoricalIntelligence
from ..data.team_competitions import REGISTRY


def key(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower() if c.isalnum() or c==' ').strip()

def poisson(l,k): return math.exp(-l)*l**k/math.factorial(k)

def dist(lh,la):
    p={'1':0.0,'X':0.0,'2':0.0}
    for h in range(0,10):
        for a in range(0,10):
            q=poisson(lh,h)*poisson(la,a); p['1' if h>a else 'X' if h==a else '2']+=q
    s=sum(p.values()); return {k:v/s for k,v in p.items()}

def poisson_market(lh,la):
    p0h=poisson(lh,0); p0a=poisson(la,0)
    le1=sum(poisson(lh,h)*poisson(la,a) for h in range(10) for a in range(10) if h+a<=1)
    le2=sum(poisson(lh,h)*poisson(la,a) for h in range(10) for a in range(10) if h+a<=2)
    le3=sum(poisson(lh,h)*poisson(la,a) for h in range(10) for a in range(10) if h+a<=3)
    btts_no=p0h+p0a-p0h*p0a
    return {'over_0_5':1-math.exp(-(lh+la)),'over_1_5':1-le1,'over_2_5':1-le2,'over_3_5':1-le3,
            'btts_yes':1-btts_no,'clean_sheet_home':p0a,'clean_sheet_away':p0h}

def normalize(p):
    s=float(sum(float(v) for v in p.values()) or 1.0); return {k:float(max(0.0,float(v)/s)) for k,v in p.items()}

def l1_distance(a,b): return sum(abs(a[k]-b[k]) for k in ('1','X','2'))/2

def _native(value):
    """Convert numpy/scalar containers to JSON/SQLite-safe native Python values."""
    try:
        if hasattr(value, 'item') and callable(value.item):
            return value.item()
    except Exception:
        pass
    if isinstance(value, dict): return {k:_native(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [_native(v) for v in value]
    return value

class Model:
    VERSION='64.0.0'
    BASE_MODEL_VERSION='63.0.0'
    def __init__(self,repo):
        self.r=repo; self.fs=FeatureStore(repo); self.players=PlayerEngine(repo); self.context=ContextEngine(repo)
        self._ratings_cache={}; self._adaptive_cache={}; self._predict_cache={}
        self.adaptive=AdaptiveLearningEngine(repo)
        self.contextual=ContextualIntelligence(repo)
        self.ensemble=ProfessionalEnsemble(repo); self.historical=HistoricalIntelligence(repo)
        self.priors=json.loads((Path(repo.path).parents[0]/'public_priors.json').read_text(encoding='utf8'))
        ep=Path(repo.path).parents[0]/'on_demand_evidence.json'
        self.external=json.loads(ep.read_text(encoding='utf8')) if ep.exists() else {}

    def prior(self,team): return self.priors.get('teams',{}).get(key(team),{})

    def prior_profile(self,team):
        """Return the strongest leakage-safe public prior available for a team.
        Team priors are historical season inputs, not post-match observations.
        """
        direct=self.prior(team)
        season=self.priors.get('season_context_2025_26',{}).get(key(team),{})
        return {
            'elo': float(direct.get('elo') if direct.get('elo') is not None else season.get('strength_index') or 1500),
            'gf_pg': direct.get('gf_pg'), 'ga_pg': direct.get('ga_pg'),
            'ppg': direct.get('ppg'), 'league': direct.get('league'),
            'matches': int(direct.get('matches') or 0),
            'strength_source': 'team_prior' if direct else 'season_context' if season else 'neutral'
        }

    @staticmethod
    def data_sufficiency(home_features, away_features, home_prior, away_prior):
        """Strict gate separating statistical coverage from mathematical output."""
        def one(f, prior):
            n=int(f.get('matches') or 0)
            direct=bool(prior.get('strength_source')=='team_prior')
            if n>=10: level='ADECUADA'; score=1.0
            elif n>=5: level='PARCIAL'; score=.75
            elif n>0: level='LIMITADA'; score=.40
            elif direct: level='PRIOR_ESTACIONAL'; score=.50
            else: level='AUSENTE'; score=0.0
            return {'matches':n,'prior_available':direct,'level':level,'score':score}
        h=one(home_features,home_prior); a=one(away_features,away_prior)
        both_actual=h['matches']>=4 and a['matches']>=4
        both_known=(h['score']>=.50 and a['score']>=.50)
        if h['matches']==0 and a['matches']==0 and not h['prior_available'] and not a['prior_available']:
            mode='LEAGUE_BASELINE_ONLY'
        elif both_actual: mode='TEAM_DATA'
        elif both_known: mode='MIXED_TEAM_PRIOR'
        else: mode='INSUFFICIENT_TEAM_DATA'
        return {'home':h,'away':a,'mode':mode,'score':round(min(h['score'],a['score']),4),
                'prediction_available':mode!='LEAGUE_BASELINE_ONLY',
                'selection_eligible':both_actual or (h['prior_available'] and a['prior_available'] and both_known),
                'reason':'Ambos equipos tienen al menos 4 partidos previos verificables.' if both_actual else 'No existe evidencia suficiente y simétrica de ambos equipos para promover una selección.'}

    @staticmethod
    def league_tier(league):
        if not league: return None
        x=key(league)
        # Higher value means a stronger competitive tier. Used only when the
        # team prior explicitly identifies its league; unknown teams stay neutral.
        for names,tier in [
            ({'premier league','laliga','bundesliga','serie a','ligue 1','liga mx','eredivisie','primeira liga'},5),
            ({'championship','2 bundesliga','serie b','ligue 2','segunda division'},4),
            ({'league one','league one england','serie c','primera federacion'},3),
            ({'league two','national league'},2)]:
            if x in names:return tier
        return None

    def inferred_league(self,team,as_of):
        """Infer domestic competition from pre-match domestic results only."""
        rows=self.r.rows("SELECT competition FROM matches WHERE status='finished' AND date<? AND (home=? OR away=?) ORDER BY date DESC,id DESC LIMIT 80",(as_of,team,team))
        counts={}
        for x in rows:
            c=str(x.get('competition') or ''); k=key(c)
            if any(t in k for t in ('cup','champions','europa','conference','libertadores','sudamericana','league cup','copa')): continue
            if self.league_tier(c) is not None: counts[c]=counts.get(c,0)+1
        return max(counts,key=counts.get) if counts else None

    def team_competition(self,team,as_of):
        """Resolve domestic tier with explicit metadata first, then temporal inference.
        Registry entries are only valid from their effective date; this prevents a
        current-season classification from leaking backward into older benchmarks.
        """
        k=key(team); entry=REGISTRY.get(k)
        if entry and str(as_of) >= entry['effective_from']:
            return entry['league'],entry['tier'],'registry'
        p=self.prior_profile(team)
        if p.get('league'):
            t=self.league_tier(p['league'])
            if t is not None:return p['league'],t,'team_prior'
        inf=self.inferred_league(team,as_of) if as_of else None
        t=self.league_tier(inf)
        return (inf,t,'historical_inference') if t is not None else (None,None,'unknown')

    def cross_competition_strength(self,team,base_elo,opponent,as_of=None):
        """Systematic cross-competition bridge.

        A stronger domestic tier receives a bounded strength uplift and the weaker
        tier receives the symmetric reduction. The adjustment is based on pre-match
        competition metadata only; it never inspects the target match result.
        """
        la,ta,sa=self.team_competition(team,as_of); lb,tb,sb=self.team_competition(opponent,as_of)
        if ta is None or tb is None or ta==tb:return base_elo,0.0
        gap=max(-3,min(3,ta-tb))
        # 85 Elo per domestic tier, capped at 255. This is intentionally smaller
        # than the old 90/tier bridge and is combined with a separate goal-rate
        # component; the two are audited independently.
        delta=gap*85.0
        return base_elo+delta,delta

    def _ratings(self,as_of):
        if as_of in self._ratings_cache:return self._ratings_cache[as_of]
        rows=self.r.rows("SELECT date,home,away,home_score,away_score FROM matches WHERE status='finished' AND date<? ORDER BY date ASC,id ASC",(as_of,))
        ratings={}
        for x in rows:
            h,a=x['home'],x['away']; hk=key(h); ak=key(a); rh=ratings.get(hk,1500.0); ra=ratings.get(ak,1500.0)
            expected=1/(1+10**((ra-rh)/400)); actual=1 if x['home_score']>x['away_score'] else .5 if x['home_score']==x['away_score'] else 0
            kfactor=22 if abs((x['home_score'] or 0)-(x['away_score'] or 0))>=2 else 20
            ratings[hk]=rh+kfactor*(actual-expected); ratings[ak]=ra+kfactor*((1-actual)-(1-expected))
        self._ratings_cache[as_of]=ratings
        return ratings

    def strength(self,team,as_of=None):
        if as_of:
            ratings=self._ratings(as_of)
            if key(team) in ratings:return ratings[key(team)]
        return self.prior_profile(team)['elo']

    def _mc(self,lh,la,seed,N=6000):
        rng=random.Random(seed); c={'1':0,'X':0,'2':0}
        def samp(l):
            u=rng.random(); acc=0
            for k in range(10):
                acc+=poisson(l,k)
                if u<=acc:return k
            return 9
        for _ in range(N):
            x,y=samp(lh),samp(la); c['1' if x>y else 'X' if x==y else '2']+=1
        return {k:v/N for k,v in c.items()}

    def _blend(self,poisson_p,strength_p,form_p,mc):
        # Ensemble weights are explicit and auditable. No single model dominates.
        return normalize({k:.58*poisson_p[k]+.16*strength_p[k]+.10*form_p[k]+.16*mc[k] for k in ('1','X','2')})

    def _form_probs(self,form,momentum):
        z=max(-2.5,min(2.5,form*2.1+momentum*1.4)); ph=1/(1+math.exp(-z)); pa=1/(1+math.exp(z)); px=.24
        return normalize({'1':ph*(1-px),'X':px,'2':pa*(1-px)})

    def predict(self,m):
        h,a=m['home'],m['away']; hp=self.prior_profile(h); ap=self.prior_profile(a)
        hs=self.fs.team(h,m['date'],20,m.get('competition_id')); aw=self.fs.team(a,m['date'],20,m.get('competition_id')); lg=self.fs.league(m['competition_id'],m['date'])
        data_gate=self.data_sufficiency(hs,aw,hp,ap)
        ctx=self.context.evaluate(m); contextual=self.contextual.evaluate(m,ctx); venue=ctx['venue']; comp_ctx=self.priors.get('competition_context',{}).get(m['competition'],{})

        # Match-specific verified venue always overrides generic competition assumptions.
        if venue.get('verified'):
            neutral=bool(venue.get('neutral'))
        elif comp_ctx.get('neutral_site') is not None:
            neutral=bool(comp_ctx.get('neutral_site'))
        else:
            neutral=False
        if lg.get('avg_home_goals') is not None and lg.get('avg_away_goals') is not None and lg.get('matches',0)>=8:
            base=float(lg['avg_home_goals']); away_base=float(lg['avg_away_goals'])
        else:
            base=float(comp_ctx.get('avg_goals_team') or 1.35); away_base=base
        raw_ha=float(lg.get('home_advantage') if lg.get('home_advantage') is not None else comp_ctx.get('home_advantage_goals',.16) or .16)
        # Home advantage is a contextual factor, not a default winner. Historical error
        # analysis showed that an unrestricted league HA could dominate the ensemble, so
        # V62.6 caps and shrinks it before it enters the goal rates.
        generic_ha=max(-.10,min(.10,raw_ha*.45))
        if neutral:
            venue_home_delta=venue_away_delta=0.0
        else:
            side=venue.get('advantage_side') or 'home'
            venue_home_delta=generic_ha if side=='home' else -.72*generic_ha
            venue_away_delta=-.45*generic_ha if side=='home' else generic_ha

        raw_home_strength=self.strength(h,m['date']); raw_away_strength=self.strength(a,m['date'])
        home_strength,home_cross=self.cross_competition_strength(h,raw_home_strength,a,m['date'])
        away_strength,away_cross=self.cross_competition_strength(a,raw_away_strength,h,m['date'])
        # Cross-competition gap gets a bounded goal-rate adjustment in addition
        # to the ELO bridge. It is deliberately symmetric and never forces 1/X/2.
        cross_goal=max(-0.22,min(0.22,(home_cross-away_cross)/1000.0))
        ed=max(-350,min(350,home_strength-away_strength))/400
        # Prefer opponent-adjusted production when sample exists; raw values remain as fallback.
        hgf=hs.get('adj_gf10') if hs.get('adj_gf10') is not None and hs.get('matches',0)>=5 else (hs.get('gf10') if hs.get('gf10') is not None else (hp.get('gf_pg') if hp.get('gf_pg') is not None else base))
        agf=aw.get('adj_gf10') if aw.get('adj_gf10') is not None and aw.get('matches',0)>=5 else (aw.get('gf10') if aw.get('gf10') is not None else (ap.get('gf_pg') if ap.get('gf_pg') is not None else away_base))
        hga=hs.get('adj_ga10') if hs.get('adj_ga10') is not None and hs.get('matches',0)>=5 else (hs.get('ga10') if hs.get('ga10') is not None else (hp.get('ga_pg') if hp.get('ga_pg') is not None else base))
        aga=aw.get('adj_ga10') if aw.get('adj_ga10') is not None and aw.get('matches',0)>=5 else (aw.get('ga10') if aw.get('ga10') is not None else (ap.get('ga_pg') if ap.get('ga_pg') is not None else away_base))
        hxg=hs.get('adj_xg10') if hs.get('adj_xg10') is not None else hs.get('xg10'); axg=aw.get('adj_xg10') if aw.get('adj_xg10') is not None else aw.get('xg10')
        hxga=hs.get('adj_xga10') if hs.get('adj_xga10') is not None else hs.get('xga10'); axga=aw.get('adj_xga10') if aw.get('adj_xga10') is not None else aw.get('xga10')
        h_attack=.62*hgf+.38*hxg if hxg is not None else hgf; a_attack=.62*agf+.38*axg if axg is not None else agf
        h_def=.62*hga+.38*hxga if hxga is not None else hga; a_def=.62*aga+.38*axga if axga is not None else aga
        form=(hs.get('ppg10') or .5)-(aw.get('ppg10') or .5); momentum=(hs.get('momentum') or 0)-(aw.get('momentum') or 0)
        ext=self.external.get(m['id'],{}); eh=ext.get('home',{}); ea=ext.get('away',{})
        ext_form=(float(eh.get('last5_ppg',0))-float(ea.get('last5_ppg',0))) if eh and ea else 0
        ext_comp=(float(eh.get('competition_points',0))/max(1,float(eh.get('competition_matches',1))))-(float(ea.get('competition_points',0))/max(1,float(ea.get('competition_matches',1)))) if eh and ea else 0
        if ext: form=.55*form+.30*ext_form+.15*ext_comp; momentum+=.5*ext_form
        shot=((hs.get('sot10') or 0)-(aw.get('sot10') or 0))*.006
        xg_diff=((hxg or 0)-(axg or 0))*.045 if hxg is not None and axg is not None else 0
        goal_diff=((hs.get('adj_goal_diff10') or hs.get('goal_diff10') or 0)-(aw.get('adj_goal_diff10') or aw.get('goal_diff10') or 0))*.025
        trend=(hs.get('goal_momentum') or 0)-(aw.get('goal_momentum') or 0)
        trend_effect=max(-.12,min(.12,trend*.035))
        rest_diff=((ctx.get('rest_days_home') or 7)-(ctx.get('rest_days_away') or 7))*.006
        travel_diff=(ctx.get('travel_km_away') or 0)-(ctx.get('travel_km_home') or 0); travel_effect=max(-.08,min(.08,travel_diff/10000))
        pi_h=self.players.team_impact(h,m['date']); pi_a=self.players.team_impact(a,m['date']); player_delta=max(-.15,min(.15,(pi_h.get('impact',0)-pi_a.get('impact',0))*.04))
        # Squad layer: use true player snapshots when available; otherwise remain neutral.
        squad_h=self.r.one("SELECT expected_xi_strength,available_squad_strength,missing_strength,quality FROM squad_snapshots WHERE lower(team)=lower(?) AND as_of<? ORDER BY as_of DESC,id DESC LIMIT 1",(h,m['date'])) or {}
        squad_a=self.r.one("SELECT expected_xi_strength,available_squad_strength,missing_strength,quality FROM squad_snapshots WHERE lower(team)=lower(?) AND as_of<? ORDER BY as_of DESC,id DESC LIMIT 1",(a,m['date'])) or {}
        squad_delta=max(-.10,min(.10,(float(squad_h.get('available_squad_strength') or 0)-float(squad_a.get('available_squad_strength') or 0))*.001)) if squad_h and squad_a else 0.0
        sos_h=hs.get('sos10') or 1500.0; sos_a=aw.get('sos10') or 1500.0
        sos_delta=max(-.10,min(.10,(sos_h-sos_a)/4000.0))
        # Stronger recent opponents make recent form more informative; this is bounded to avoid overreaction.
        form_sos_effect=max(-.08,min(.08,sos_delta*.55))

        lh=max(.20,min(3.8,base+venue_home_delta+.20*ed+.24*(h_attack-base)+.13*(a_def-base)+.16*form+trend_effect+shot+xg_diff+goal_diff+rest_diff+player_delta+squad_delta+form_sos_effect+travel_effect+cross_goal+contextual['home_delta']))
        la=max(.18,min(3.6,away_base+venue_away_delta-.20*ed+.24*(a_attack-away_base)+.13*(h_def-away_base)-.16*form-trend_effect-shot-xg_diff-goal_diff-rest_diff-player_delta-travel_effect-cross_goal+contextual['away_delta']))

        if data_gate['mode']=='LEAGUE_BASELINE_ONLY':
            # Keep the verified venue metadata visible/auditable, but do not let it
            # create team-specific strength when both teams have zero evidence.
            lh=max(.20,min(3.8,base)); la=max(.18,min(3.6,away_base))

        h2h=self.fs.h2h(h,a,m['date'])
        h2h_intel=self.historical.evaluate(h,a,m['date'],h2h)
        if h2h:
            edge=h2h_intel.get('home_edge',0.0)
            lh*=1+edge; la*=1-edge
        poisson_p=dist(lh,la)
        closeness=max(0,1-abs(ed)/.22); poisson_p['X']+=.055*closeness; poisson_p=normalize(poisson_p)
        strength_p=normalize({'1':1/(1+math.exp(-ed*2.6))*.76,'X':.24,'2':1/(1+math.exp(ed*2.6))*.76})
        form_p=self._form_probs(form,momentum)
        mc=self._mc(lh,la,55300+sum(ord(c) for c in m['id']))
        p=self._blend(poisson_p,strength_p,form_p,mc)
        p,ensemble_info=self.ensemble.apply(m,p,lh,la)
        # Leakage-safe adaptive calibration: only verified matches before m['date'] may influence it.
        adaptive_cal=self._adaptive_cache.get(m['date'])
        if adaptive_cal is None:
            adaptive_cal=self.adaptive.calibration_for_match(m)
            self._adaptive_cache[m['date']]=adaptive_cal
        pre_pick=max(p,key=p.get); pre_vals=sorted(p.values(),reverse=True); pre_margin=pre_vals[0]-pre_vals[1]
        
        # Stability: perturb the dominant contextual blocks and measure probability movement.
        variants=[]
        for name,dlh,dla in [
            ('sin_sede',-venue_home_delta,-venue_away_delta),
            ('sin_form',-.16*form-trend_effect,.16*form+trend_effect),
            ('sin_jugadores',-player_delta,player_delta),
            ('sin_viaje',-travel_effect,travel_effect),
            ('sin_ajuste_rival',(hgf-(hs.get('gf10') or hgf))*.24,(agf-(aw.get('gf10') or agf))*.24),
        ]:
            variants.append((name,dist(max(.2,min(3.8,lh+dlh)),max(.18,min(3.6,la+dla)))))
        stability=1-(sum(l1_distance(p,v) for _,v in variants)/max(1,len(variants)))
        stability=max(0,min(1,stability))
        consensus=1-(max(l1_distance(a,b) for a in (poisson_p,strength_p,form_p,mc) for b in (poisson_p,strength_p,form_p,mc)))
        consensus=max(0,min(1,consensus))
        q=self.fs.quality(hs,aw,lg); hist=hs.get('matches',0)+aw.get('matches',0); venue_quality=1.0 if venue.get('verified') else .45
        prior_quality=.10 if hp.get('strength_source')=='team_prior' and ap.get('strength_source')=='team_prior' else 0.0
        evidence=min(1,.08+.24*q+.20*min(1,hist/30)+.10*min(1,len(h2h)/5)+prior_quality+.14*venue_quality+.10*consensus+.10*(1 if ext else 0))
        if not data_gate['selection_eligible']: evidence=min(evidence,.44)
        confidence=min(.95,max(.05,.32*pre_margin+.40*evidence+.16*consensus+.12*stability))
        if not data_gate['selection_eligible']: confidence=min(confidence,.25)
        markets=poisson_market(lh,la)

        # Explainable contribution ledger. Values are directional model contributions, not fake causal percentages.
        raw_signals={
            'Fuerza/ELO':.20*ed,
            'Forma':.16*form+.035*momentum,
            'Ataque ajustado':.24*((h_attack-base)-(a_attack-away_base)),
            'Defensa ajustada':.13*((a_def-base)-(h_def-away_base)),
            'xG diferencial':xg_diff,
            'Producción ajustada':goal_diff,
            'Tendencia':trend_effect,
            'Sede real':venue_home_delta-venue_away_delta,
            'Descanso':rest_diff,
            'Viaje':travel_effect,
            'Jugadores':player_delta,
            'Calidad del XI/plantel':squad_delta,
            'Fuerza de rivales recientes':form_sos_effect,
            'H2H':h2h_intel.get('home_edge',0.0) if h2h else 0,
            'Contexto competitivo reciente':.06*ext_form+.035*ext_comp,
            'Fatiga/contexto adaptativo':contextual['home_delta'],
            'Plantilla/fitness':contextual['lineup_delta']+contextual['fitness_delta'],
            'Clima':contextual['weather_delta'],
            'Árbitro':contextual['referee_delta'],
            'Perfil de liga':contextual['league_delta'],
            'Brecha competitiva':cross_goal,
        }
        adaptive_feature_delta=self.adaptive.feature_delta(raw_signals,adaptive_cal)
        p=self.adaptive.apply(p,adaptive_cal,adaptive_feature_delta)
        # Historical base-rate guard: bounded blend with outcomes observed strictly
        # before the match date. This counters systematic home/away selection bias
        # without forcing any outcome and never uses the match's own result.
        base_rows=self.r.rows("SELECT home_score,away_score FROM matches WHERE status='finished' AND date<? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY date DESC,id DESC LIMIT 120",(m['date'],))
        if len(base_rows)>=12:
            nbase=len(base_rows); prior_out={'1':0,'X':0,'2':0}
            for br in base_rows:
                actual_br='1' if int(br['home_score'])>int(br['away_score']) else 'X' if int(br['home_score'])==int(br['away_score']) else '2'
                prior_out[actual_br]+=1
            base_prior={k:prior_out[k]/nbase for k in ('1','X','2')}
            p=normalize({k:.92*p[k]+.08*base_prior[k] for k in ('1','X','2')})
        else:
            base_prior={'1':.42,'X':.28,'2':.30}
        pick=max(p,key=p.get); vals=sorted(p.values(),reverse=True); margin=vals[0]-vals[1]
        confidence=min(.95,max(.05,.32*margin+.40*evidence+.16*consensus+.12*stability))
        total=sum(abs(v) for v in raw_signals.values()) or 1
        signals=[{'factor':k,'direction':'local' if v>0 else 'visitante' if v<0 else 'neutral','impact':round(v,4),'share':round(abs(v)/total,4)} for k,v in raw_signals.items() if abs(v)>=.005]
        signals.sort(key=lambda x:x['share'],reverse=True)
        no_venue=dist(max(.2,min(3.8,lh-venue_home_delta)),max(.18,min(3.6,la-venue_away_delta)))
        no_form=dist(max(.2,min(3.8,lh-(.16*form+trend_effect))),max(.18,min(3.6,la+(.16*form+trend_effect))))
        counterfactual={
            'without_venue':no_venue,
            'without_form':no_form,
            'flip_without_venue':max(no_venue,key=no_venue.get)!=pick,
            'flip_without_form':max(no_form,key=no_form.get)!=pick,
            'what_changes_choice':[]
        }
        if counterfactual['flip_without_venue']: counterfactual['what_changes_choice'].append('la sede real es decisiva para la elección')
        if counterfactual['flip_without_form']: counterfactual['what_changes_choice'].append('la forma/tendencia reciente es decisiva para la elección')
        if not counterfactual['what_changes_choice']: counterfactual['what_changes_choice'].append('ningún bloque contextual aislado cambia el líder; la elección depende del conjunto de señales')

        review_count=int(self.r.one("SELECT COUNT(*) n FROM postmatch_reviews")['n'])
        calibration_status='VALIDATED' if review_count>=100 else 'LIMITED_SAMPLE' if review_count>=50 else 'INSUFFICIENT_SAMPLE'
        # Professional decision gate: accuracy is not manufactured. A pick is
        # only promoted to BET/RECOMMEND when its calibrated probability and
        # evidence clear a threshold; otherwise LiAn explicitly abstains.
        max_p=max(p.values()); second_p=sorted(p.values(),reverse=True)[1]
        decision='RECOMMEND' if data_gate['selection_eligible'] and max_p>=0.52 and margin>=0.06 and evidence>=0.50 else 'CAUTION' if data_gate['selection_eligible'] and max_p>=0.45 and evidence>=0.40 else 'PASS'
        result={
            'model_version':self.VERSION,'base_model_version':self.BASE_MODEL_VERSION,'probabilities':p,'pick':pick,'confidence':confidence,'decision':decision,'prediction_available':data_gate['prediction_available'],'selection_eligible':data_gate['selection_eligible'],'data_sufficiency':data_gate,'professional_markets':ProfessionalMarkets.evaluate(p,evidence) if data_gate['selection_eligible'] else {'one_x2':'PASS','double_chance':'PASS'},'decision_semantics':'RECOMMEND requires probability>=52%, margin>=6pp and evidence>=0.50; PASS means no forced selection','confidence_semantics':'model_confidence_not_historical_accuracy','calibration_status':calibration_status,'calibration_samples':review_count,'evidence':evidence,'quality':'ALTA' if evidence>=.75 else 'MEDIA' if evidence>=.55 else 'BAJA',
            'expected_goals':{'home':round(lh,2),'away':round(la,2),'total':round(lh+la,2)},'markets':{k:round(v,4) for k,v in markets.items()},
            'features':{
                'elo_diff':round(ed,3),'cross_competition_home_adjustment':round(home_cross,2),'cross_competition_away_adjustment':round(away_cross,2),'cross_competition_goal_delta':round(cross_goal,3),'home_competition':self.team_competition(h,m['date'])[0],'away_competition':self.team_competition(a,m['date'])[0],'home_competition_source':self.team_competition(h,m['date'])[2],'away_competition_source':self.team_competition(a,m['date'])[2],'form_diff':round(form,3),'external_form_diff':round(ext_form,3),'external_competition_diff':round(ext_comp,3),'momentum_diff':round(momentum,3),'xg_home':None if hxg is None else round(hxg,2),'xg_away':None if axg is None else round(axg,2),
                'xga_home':None if hxga is None else round(hxga,2),'xga_away':None if axga is None else round(axga,2),'gf10_home':None if hgf is None else round(hgf,2),'gf10_away':None if agf is None else round(agf,2),'sos10_home':round(sos_h,2),'sos10_away':round(sos_a,2),'sos_delta':round(sos_delta,4),'squad_delta':round(squad_delta,4),
                'ga10_home':None if hga is None else round(hga,2),'ga10_away':None if aga is None else round(aga,2),'adj_gf10_home':None if hs.get('adj_gf10') is None else round(hs['adj_gf10'],2),
                'adj_gf10_away':None if aw.get('adj_gf10') is None else round(aw['adj_gf10'],2),'adj_ga10_home':None if hs.get('adj_ga10') is None else round(hs['adj_ga10'],2),'adj_ga10_away':None if aw.get('adj_ga10') is None else round(aw['adj_ga10'],2),
                'sot_home':None if hs.get('sot10') is None else round(hs['sot10'],2),'sot_away':None if aw.get('sot10') is None else round(aw['sot10'],2),'home_history':hs.get('matches',0),'away_history':aw.get('matches',0),'h2h':len(h2h),'league_history':lg.get('matches',0),
                'feature_quality':q,'venue_advantage_home':round(venue_home_delta,3),'venue_advantage_away':round(venue_away_delta,3),'venue_verified':venue.get('verified',False),'venue_status':venue.get('status'),'venue_side':venue.get('advantage_side'),
                'travel_km_home':ctx.get('travel_km_home'),'travel_km_away':ctx.get('travel_km_away'),'rest_home':ctx.get('rest_days_home'),'rest_away':ctx.get('rest_days_away'),'contextual_fatigue_home':contextual['fatigue_home'],'contextual_fatigue_away':contextual['fatigue_away'],'league_profile':contextual['league_profile'],
                'momentum_home':round(hs.get('momentum') or 0,3),'momentum_away':round(aw.get('momentum') or 0,3),'consistency_home':round(hs.get('consistency') or .5,3),'consistency_away':round(aw.get('consistency') or .5,3),
            },
            'feature_vector':raw_signals,'source_count':int((m.get('_fusion') or {}).get('source_count') or max(1,int(1+min(4,hist/10)))),'player_impact':{'home':round(pi_h.get('impact',0),4),'away':round(pi_a.get('impact',0),4)},'context':ctx,'contextual_intelligence':contextual,
            'consensus':{'score':round(consensus,4),'poisson':poisson_p,'strength':strength_p,'form':form_p,'monte_carlo':mc,'professional_ensemble':ensemble_info},'stability':{'score':round(stability,4),'variants':{n:v for n,v in variants}},'signals':signals,'external_evidence':ext,'historical_intelligence':h2h_intel,'historical_base_rate':base_prior,'counterfactual':counterfactual,
            'rationale':f'Ensemble V63.0.0: Poisson + Dixon-Coles + XGBoost opcional + ELO + forma/tendencia + estadísticas ajustadas por fuerza del rival + Monte Carlo 6,000 + xG + H2H + sede real + descanso + viaje + jugadores + calibración adaptativa temporal. Solo usa datos anteriores a {m["date"]}.',
            'adaptive_learning':{'samples_before_match':adaptive_cal['outcome'].get('samples',0),'feature_delta':round(adaptive_feature_delta,5),'outcome_weights':{k:round(float(adaptive_cal['outcome'].get(k,1)),4) for k in ('1','X','2')},'competition_weights':{k:round(float(adaptive_cal['competition'].get(k,1)),4) for k in ('1','X','2')}}
        }
        result['explainability']=explain(result,m)
        return _native(result)
