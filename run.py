from pathlib import Path
from backend.data.repo import Repo

ROOT = Path(__file__).resolve().parent
db_path = ROOT / 'backend' / 'data' / 'lian.db'

print(f"Inicializando DB en {db_path}...")
repo = Repo(db_path)
repo.init_all()  # <-- AHORA CREA TODAS LAS TABLAS

print("DB OK, arrancando servidor...")
import backend.server
backend.server.main()