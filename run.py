from pathlib import Path
from backend.data.repo import Repo

ROOT = Path(__file__).resolve().parent
db_path = ROOT / 'backend' / 'data' / 'lian.db'

print(f"Inicializando DB en {db_path}...")
repo = Repo(db_path)

for method in ['init', 'init_db', 'init_schema', 'ensure_schema', 'create_tables', 'init_learning']:
    if hasattr(repo, method):
        try:
            print(f"Ejecutando {method}()...")
            getattr(repo, method)()
        except Exception as e:
            print(f"{method} error: {e}")

print("DB inicializada, arrancando servidor...")
import backend.server
backend.server.main()