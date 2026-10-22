from __future__ import annotations

OUTCOMES=('1','X','2')
LABEL={'1':'Local','X':'Empate','2':'Visitante'}

class ProfessionalMarkets:
    """Decision layer that preserves 1X2 while adding selective coverage markets.
    It never turns a low-confidence 1X2 into a false certainty. Coverage markets
    are evaluated separately and carry their own historical/backtest metric.
    """
    VERSION='60.0.0'
    @staticmethod
    def evaluate(probabilities, evidence):
        p={k:float(probabilities.get(k,0)) for k in OUTCOMES}
        order=sorted(OUTCOMES,key=lambda k:p[k],reverse=True)
        top1,top2=order[0],order[1]
        pair='1X' if {top1,top2}=={'1','X'} else '12' if {top1,top2}=={'1','2'} else 'X2'
        coverage=p[top1]+p[top2]
        one_x2='RECOMMEND' if p[top1]>=.52 and p[top1]-p[top2]>=.06 and evidence>=.50 else 'PASS'
        double='RECOMMEND' if coverage>=.72 and evidence>=.45 else 'CAUTION' if coverage>=.66 else 'PASS'
        return {'one_x_two':{'pick':top1,'label':LABEL[top1],'decision':one_x2,'probability':round(p[top1],4)},
                'double_chance':{'market':pair,'decision':double,'coverage_probability':round(coverage,4),'covered_outcomes':[top1,top2]},
                'method':'selective decision layer; no guarantee of future accuracy'}
