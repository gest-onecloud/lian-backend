"""Robust public HTTP transport for LiAn provider adapters.

The application must distinguish a provider outage from an empty football calendar.
This client tries urllib first (preserving the existing testable transport), then the
installed Requests stack, and finally the Windows/Linux curl executable when available.
No result is invented: a request is successful only when a JSON object can be decoded.
"""
from __future__ import annotations
import json, os, shutil, subprocess, urllib.request
from urllib.parse import urlparse

BROWSER_UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

def provider_headers(url):
    host=urlparse(url).netloc.lower()
    headers={'Accept':'application/json, text/plain, */*','Accept-Language':'es-MX,es;q=0.9,en;q=0.8'}
    if 'espn.com' in host:
        return {'Accept':'application/json'}
    if 'sofascore.com' in host:
        headers.update({'User-Agent':BROWSER_UA,'Referer':'https://www.sofascore.com/','Origin':'https://www.sofascore.com'})
    elif 'fotmob.com' in host:
        headers.update({'User-Agent':BROWSER_UA,'Referer':'https://www.fotmob.com/'})
    elif 'thesportsdb.com' in host:
        headers.update({'User-Agent':BROWSER_UA,'Referer':'https://www.thesportsdb.com/'})
    return headers

def _urllib_json(url, timeout):
    req=urllib.request.Request(url,headers=provider_headers(url))
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8','ignore') or '{}')

def _requests_json(url, timeout):
    import requests
    r=requests.get(url,headers=provider_headers(url),timeout=timeout)
    r.raise_for_status()
    return r.json()

def _curl_json(url, timeout):
    exe=shutil.which('curl.exe') or shutil.which('curl')
    if not exe: raise RuntimeError('curl no disponible')
    args=[exe,'--fail','--silent','--show-error','--location','--compressed','--max-time',str(max(1,int(timeout)))]
    for k,v in provider_headers(url).items(): args += ['-H',f'{k}: {v}']
    args.append(url)
    p=subprocess.run(args,capture_output=True,text=True,timeout=max(2,int(timeout)+2),check=False)
    if p.returncode!=0: raise RuntimeError(f'curl rc={p.returncode}: {(p.stderr or "").strip()[:300]}')
    return json.loads(p.stdout or '{}')

def get_json(url, timeout=8):
    errors=[]
    transports=[('urllib',_urllib_json)] if os.getenv('LIAN_TEST_MODE')=='1' else [('urllib',_urllib_json),('requests',_requests_json),('curl',_curl_json)]
    for name,fn in transports:
        try:
            data=fn(url,timeout)
            if not isinstance(data,dict): raise RuntimeError(f'{name}: JSON no es objeto')
            return data
        except Exception as ex:
            errors.append(f'{name}: {ex!r}')
    raise RuntimeError('provider request failed; '+' | '.join(errors))
