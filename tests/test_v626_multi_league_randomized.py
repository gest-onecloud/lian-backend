import datetime as dt
import unittest
from unittest.mock import patch
import backend.services.targeted_search as ts

class V626MultiLeagueRandomized(unittest.TestCase):
    def test_twenty_randomized_league_cases(self):
        leagues=[
            ('Liga MX','Cruz Azul','Santos'),('LaLiga','Valencia','Barcelona'),
            ('Premier League','Arsenal','Chelsea'),('Bundesliga','Bayern Munich','Dortmund'),
            ('Serie A','Inter','Milan'),('Ligue 1','PSG','Lyon'),('Eredivisie','Ajax','PSV'),
            ('Primeira Liga','Benfica','Porto'),('Brasileirao','Flamengo','Palmeiras'),
            ('MLS','LA Galaxy','Seattle Sounders'),('Argentina','River Plate','Boca Juniors'),
            ('J1 League','Kawasaki Frontale','Urawa Reds'),('Scottish Premiership','Celtic','Rangers'),
            ('Belgium Pro League','Club Brugge','Anderlecht'),('Austria Bundesliga','RB Salzburg','Rapid Vienna'),
            ('Switzerland Super League','Basel','Young Boys'),('Greece Super League','Olympiacos','Panathinaikos'),
            ('Turkey Super Lig','Galatasaray','Fenerbahce'),('Colombia Primera A','Atlético Nacional','Millonarios'),
            ('Chile Primera Division','Colo-Colo','Universidad de Chile')]
        fixtures=[{'id':str(i),'home':h,'away':a,'date':f'2026-09-{4+i:02d}','league':lg} for i,(lg,h,a) in enumerate(leagues)]
        def fake_events(source,tid,timeout=6):
            return [x for x in fixtures if ts.team_eq(x['home'],tid) or ts.team_eq(x['away'],tid)]
        mapping={t:[('SOFA',t,t,{})] for _,h,a in leagues for t in (h,a)}
        with patch.object(ts,'_team_candidates',side_effect=lambda q,timeout=6:mapping.get(q,[])), patch.object(ts,'_events_for',side_effect=fake_events), patch.object(ts,'_google_search_hints',return_value={'ok':True,'source':'GOOGLE_WEB_HINTS','hints':[]}):
            for lg,h,a in leagues:
                x=ts.discover_team(h,today=dt.date(2026,9,3),days=30,timeout=1)
                self.assertTrue(x['found'],(lg,h))
                self.assertTrue(any(ts.team_eq(c['home'],h) or ts.team_eq(c['away'],h) for c in x['candidates']))

if __name__=='__main__': unittest.main()
