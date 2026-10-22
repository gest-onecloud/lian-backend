import sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from backend.data.repo import Repo
from backend.learning.benchmark import ProfessionalBenchmark
r=Repo(ROOT/'data'/'lian.db')
b=ProfessionalBenchmark(r)
out=b.random_five(20260902,'cal-2026-08-25-en-carabao-birmingham-city-brentford')
print(json.dumps(out,ensure_ascii=False,indent=2))
