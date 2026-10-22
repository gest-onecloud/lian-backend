import io,sys,unittest,json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.data.historical import HistoricalSync
from backend.data.repo import Repo

class HistoricalParser(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.s=HistoricalSync(Repo(ROOT/'data'/'lian.db'))
 def test_openfootball_fixture(self):
  raw=json.dumps({'matches':[{'date':'2024-08-16','time':'20:00','round':'Matchday 1','team1':'A','team2':'B','score':{'ft':[2,1]}},{'date':'2024-08-17','team1':'C','team2':'D','score':{'ft':None}}]}).encode()
  x=self.s.parse_openfootball(raw,'Premier League','2024-25'); self.assertEqual(len(x),1); self.assertEqual(x[0]['home_score'],2)
 def test_ligamx_fixture(self):
  raw='date,season,stage,round,home_team,away_team,home_score,away_score\n2024-08-01,2024-25,Apertura,1,A,B,1,0\n'.encode()
  x=self.s.parse_ligamx(raw); self.assertEqual(len(x),1); self.assertEqual(x[0]['away_score'],0)
if __name__=='__main__':unittest.main()
