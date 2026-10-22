"""LiAn V64.4.0 CI regression runner.
Every test module executes against a private project copy, preventing SQLite/WAL
state, caches, environment mutations, or legacy stateful tests from contaminating
another module. Modules without tests are SKIP. Maximum parallelism is 4.
"""
import pathlib, subprocess, sys, time, re, os, shutil, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=pathlib.Path(__file__).resolve().parent
files=sorted(ROOT.glob('tests/test_*.py'))

def run_one(src):
    td=pathlib.Path(tempfile.mkdtemp(prefix='lian_ci_'))
    try:
        dst=td/'project'; shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
        env=os.environ.copy(); env['PYTHONPATH']=str(dst)+os.pathsep+env.get('PYTHONPATH','')
        started=time.time()
        p=subprocess.run([sys.executable,'-m','pytest','-q',str(dst/'tests'/src.name)],cwd=dst,env=env,capture_output=True,text=True,timeout=18)
        out=(p.stdout or '')+(p.stderr or '')
        m=re.search(r'(\d+) passed',out); n=int(m.group(1)) if m else 0
        if p.returncode==0 and n>0: status='PASS'; ok=True
        elif p.returncode==5 or 'no tests ran' in out: status='SKIP'; ok=True
        else: status='FAIL'; ok=False
        return (src.name,ok,status,n,time.time()-started,out[-1400:])
    except subprocess.TimeoutExpired:
        return (src.name,False,'TIMEOUT',0,time.time()-started,'TIMEOUT')
    finally:
        shutil.rmtree(td,ignore_errors=True)

results=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    futs=[pool.submit(run_one,f) for f in files]
    for fut in as_completed(futs):
        r=fut.result(); results.append(r); print(f'{r[0]}: {r[2]} ({r[3]} tests, {r[4]:.1f}s)',flush=True)
results.sort()
total=sum(x[3] for x in results); passed=sum(x[3] for x in results if x[1]); failed=sum(not x[1] for x in results); skipped=sum(x[2]=='SKIP' for x in results)
print(f'REGRESSION SUMMARY: {passed}/{total} tests passed; files={len(results)}; skipped_files={skipped}; failed_files={failed}')
for x in results:
    if not x[1]: print(f'--- {x[0]} ---\n{x[5]}')
sys.exit(0 if failed==0 and passed==total else 1)
