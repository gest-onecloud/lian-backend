from __future__ import annotations
from datetime import date
import math

class HistoricalIntelligence:
    """Recency-aware H2H intelligence. Historical matches are context, never truth.
    Newer H2H gets more weight; old H2H decays and cannot dominate the model.
    """
    VERSION='63.0.0'
    def __init__(self,repo): self.r=repo
    @staticmethod
    def _key(s):
        import re,unicodedata
        return ''.join(c for c in unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower() if c.isalnum())
    def evaluate(self,home,away,as_of,rows=None):
        rows=rows if rows is not None else self.r.rows('''SELECT date,home,away,home_score,away_score FROM matches
            WHERE status='finished' AND date<? AND ((lower(home)=lower(?) AND lower(away)=lower(?)) OR (lower(home)=lower(?) AND lower(away)=lower(?)))
            ORDER BY date DESC,id DESC LIMIT 20''',(as_of,home,away,away,home))
        if not rows:return {'samples':0,'home_edge':0.0,'draw_rate':0.0,'away_rate':0.0,'effective_samples':0.0,'recency_half_life_days':730}
        target=date.fromisoformat(as_of); sw=sh=sd=sa=0.0
        for x in rows:
            try: age=max(0,(target-date.fromisoformat(str(x['date'])[:10])).days)
            except Exception: age=3650
            w=math.exp(-math.log(2)*age/730.0)
            hs,aw=int(x['home_score']),int(x['away_score'])
            h_is_home=self._key(x['home'])==self._key(home)
            if hs==aw: out='X'
            elif (hs>aw)==h_is_home: out='1'
            else: out='2'
            sw+=w
            if out=='1':sh+=w
            elif out=='X':sd+=w
            else:sa+=w
        if sw<=0:return {'samples':len(rows),'home_edge':0.0,'draw_rate':0.0,'away_rate':0.0,'effective_samples':0.0,'recency_half_life_days':730}
        ph,pd,pa=sh/sw,sd/sw,sa/sw
        # Pull only a bounded directional adjustment toward the historical split.
        edge=(ph-pa)*min(.09,.025*math.sqrt(len(rows)))
        return {'samples':len(rows),'home_edge':max(-.09,min(.09,edge)),'draw_rate':pd,'away_rate':pa,'effective_samples':round(sw,3),'recency_half_life_days':730}
