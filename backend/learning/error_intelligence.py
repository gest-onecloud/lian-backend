"""League/team/context error intelligence for LiAn V55.7.
Diagnostic only: it never changes model weights automatically. It aggregates
verified post-match reviews and exposes patterns that are large enough to be useful.
"""
from __future__ import annotations
import json, math
from collections import defaultdict

LABELS={'1':'local','X':'empate','2':'visitante'}

class ErrorIntelligence:
    MIN_SCOPE=5
    def __init__(self, repo):
        self.r=repo
        self.r.init_learning()
        self.r.execute("""CREATE TABLE IF NOT EXISTS error_intelligence_snapshots(
            id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, entity TEXT NOT NULL,
            samples INTEGER NOT NULL, accuracy REAL, brier REAL, log_loss REAL,
            local_bias REAL, away_bias REAL, draw_bias REAL, evidence_avg REAL,
            diagnosis TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        self.r.execute("""CREATE TABLE IF NOT EXISTS error_segment_metrics(
            scope TEXT NOT NULL, entity TEXT NOT NULL, samples INTEGER NOT NULL,
            accuracy REAL, brier REAL, log_loss REAL, pick_local_rate REAL,
            actual_local_rate REAL, pick_draw_rate REAL, actual_draw_rate REAL,
            pick_away_rate REAL, actual_away_rate REAL, avg_evidence REAL,
            avg_confidence REAL, avg_separation REAL, wrong_rate REAL,
            PRIMARY KEY(scope,entity))""")

    def _reviews(self):
        return self.r.rows("""SELECT r.*, m.competition_id, m.competition, m.home, m.away,
            m.date, m.status, m.result_source_type, p.confidence AS pred_confidence, p.evidence AS pred_evidence,
            p.p_home, p.p_draw, p.p_away
            FROM postmatch_reviews r JOIN matches m ON m.id=r.match_id
            LEFT JOIN predictions p ON p.match_id=r.match_id
            WHERE m.status='finished' AND r.actual IN ('1','X','2')""")

    @staticmethod
    def _diag(rows):
        if not rows: return []
        diags=defaultdict(int)
        for r in rows:
            try:
                for d in json.loads(r.get('diagnosis') or '[]'):
                    diags[d]+=1
            except Exception: pass
        return [{'diagnosis':k,'count':v,'rate':v/len(rows)} for k,v in sorted(diags.items(),key=lambda x:x[1],reverse=True)]

    def _metrics(self, rows):
        n=len(rows)
        if not n: return {'samples':0}
        wrong=sum(r['predicted']!=r['actual'] for r in rows)
        return {
            'samples':n,
            'accuracy':(n-wrong)/n,
            'brier':sum(float(r['brier'] or 0) for r in rows)/n,
            'log_loss':sum(float(r['log_loss'] or 0) for r in rows)/n,
            'wrong_rate':wrong/n,
            'pick_local_rate':sum(r['predicted']=='1' for r in rows)/n,
            'actual_local_rate':sum(r['actual']=='1' for r in rows)/n,
            'pick_draw_rate':sum(r['predicted']=='X' for r in rows)/n,
            'actual_draw_rate':sum(r['actual']=='X' for r in rows)/n,
            'pick_away_rate':sum(r['predicted']=='2' for r in rows)/n,
            'actual_away_rate':sum(r['actual']=='2' for r in rows)/n,
            'avg_evidence':sum(float(self._evidence(r)) for r in rows)/n,
            'avg_confidence':sum(float(self._confidence(r)) for r in rows)/n,
            'avg_separation':sum(float(self._separation(r)) for r in rows)/n,
        }

    @staticmethod
    def _evidence(r):
        # Stored review does not currently persist evidence; recover it from the original prediction.
        return float(r.get('pred_evidence') or 0)
    @staticmethod
    def _confidence(r): return float(r.get('pred_confidence') or 0)
    @staticmethod
    def _separation(r):
        vals=sorted([float(r.get('p_home') or 0),float(r.get('p_draw') or 0),float(r.get('p_away') or 0)],reverse=True)
        return (vals[0]-vals[1]) if len(vals)>=2 else 0.0

    def _write(self,scope,entity,rows):
        if len(rows)<self.MIN_SCOPE: return None
        m=self._metrics(rows)
        diagnosis=[]
        for outcome,label in LABELS.items():
            gap=m[f'pick_{"local" if outcome=="1" else "draw" if outcome=="X" else "away"}_rate']-m[f'actual_{"local" if outcome=="1" else "draw" if outcome=="X" else "away"}_rate']
            if abs(gap)>=.10:
                direction='sobrepredicción' if gap>0 else 'subpredicción'
                diagnosis.append(f'{label}: {direction} {abs(gap)*100:.1f} pp')
        if m['accuracy']<.40: diagnosis.append('accuracy baja en esta muestra')
        if m['brier']>.60: diagnosis.append('Brier elevado')
        self.r.execute("""INSERT OR REPLACE INTO error_segment_metrics(
            scope,entity,samples,accuracy,brier,log_loss,pick_local_rate,actual_local_rate,
            pick_draw_rate,actual_draw_rate,pick_away_rate,actual_away_rate,avg_evidence,
            avg_confidence,avg_separation,wrong_rate) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (scope,entity,m['samples'],m.get('accuracy'),m.get('brier'),m.get('log_loss'),m.get('pick_local_rate'),m.get('actual_local_rate'),m.get('pick_draw_rate'),m.get('actual_draw_rate'),m.get('pick_away_rate'),m.get('actual_away_rate'),m.get('avg_evidence'),m.get('avg_confidence'),m.get('avg_separation'),m.get('wrong_rate')))
        self.r.execute("""INSERT INTO error_intelligence_snapshots(scope,entity,samples,accuracy,brier,log_loss,local_bias,away_bias,draw_bias,evidence_avg,diagnosis)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(scope,entity,m['samples'],m.get('accuracy'),m.get('brier'),m.get('log_loss'),m['pick_local_rate']-m['actual_local_rate'],m['pick_away_rate']-m['actual_away_rate'],m['pick_draw_rate']-m['actual_draw_rate'],m.get('avg_evidence'),json.dumps(diagnosis,ensure_ascii=False)))
        return dict(scope=scope,entity=entity,**m,diagnosis=diagnosis)

    def _team_rows(self, rows):
        out=defaultdict(list)
        for r in rows:
            # A review belongs to both teams, but direction is from the fixture perspective.
            out[r['home']].append(r); out[r['away']].append(r)
        return out

    def run(self):
        rows=self._reviews(); by_comp=defaultdict(list)
        for r in rows: by_comp[r['competition'] or r['competition_id'] or 'Sin competencia'].append(r)
        team=self._team_rows(rows)
        comp=[]; teams=[]
        for k,v in by_comp.items():
            x=self._write('liga',k,v)
            if x: comp.append(x)
        for k,v in team.items():
            x=self._write('equipo',k,v)
            if x: teams.append(x)
        global_m=self._metrics(rows)
        # Strong diagnostic segments: home/away prediction and evidence bands.
        bands=[]
        segments=[
            ('evidencia_baja',lambda r: float(r.get('pred_evidence') or 0)<.55),
            ('evidencia_alta',lambda r: float(r.get('pred_evidence') or 0)>=.75),
            ('confianza_baja',lambda r: float(r.get('pred_confidence') or 0)<.40),
            ('confianza_alta',lambda r: float(r.get('pred_confidence') or 0)>=.60),
            ('fallo',lambda r:r['predicted']!=r['actual']),
            ('local_pick',lambda r:r['predicted']=='1'),
            ('away_pick',lambda r:r['predicted']=='2'),
            ('draw_pick',lambda r:r['predicted']=='X')
        ]
        for label,fn in segments:
            subset=[r for r in rows if fn(r)]
            if len(subset)>=self.MIN_SCOPE: bands.append(self._write('segmento',label,subset))
        comp_sorted=sorted(comp,key=lambda x:(x['samples'],x['accuracy']),reverse=True)
        worst=sorted([x for x in comp if x['samples']>=self.MIN_SCOPE],key=lambda x:(x['accuracy'],x['brier']))[:8]
        team_worst=sorted([x for x in teams if x['samples']>=self.MIN_SCOPE],key=lambda x:(x['accuracy'],x['brier']))[:8]
        return {'samples':len(rows),'global':global_m,'leagues':comp_sorted,'worst_leagues':worst,'worst_teams':team_worst,'segments':bands,
                'diagnoses':self._diag(rows),
                'policy':'Diagnóstico únicamente. Ningún sesgo cambia pesos automáticamente. Una recalibración requiere muestra suficiente por segmento y mejora walk-forward fuera de muestra.'}

    def report(self):
        return self.run()
