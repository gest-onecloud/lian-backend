"""Persistent Progol ticket generation and post-match result tracking."""
from __future__ import annotations
import json,random
from .calendar import matches
from .timezone import mexico_time

def init(repo):
    c=repo.connect()
    try:c.executescript('''CREATE TABLE IF NOT EXISTS progol_tickets(id INTEGER PRIMARY KEY AUTOINCREMENT,match_date TEXT NOT NULL,ticket_no INTEGER NOT NULL,model_version TEXT NOT NULL,selections_json TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(match_date,ticket_no));CREATE TABLE IF NOT EXISTS progol_match_results(match_id TEXT PRIMARY KEY,match_date TEXT NOT NULL,actual TEXT,status TEXT NOT NULL DEFAULT 'pending',source TEXT,source_url TEXT,verified_at TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
    finally:c.close()
def _result(m):
    if m.get('status')!='finished' or m.get('home_score') is None:return None
    return '1' if m['home_score']>m['away_score'] else 'X' if m['home_score']==m['away_score'] else '2'
def _sync_results(repo,ms):
    init(repo)
    for m in ms:
        a=_result(m); repo.execute('INSERT OR REPLACE INTO progol_match_results(match_id,match_date,actual,status,source,source_url,verified_at,updated_at) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(m['id'],m['date'],a,'finished' if a else 'pending',m.get('result_source'),m.get('result_source_url'),m.get('result_verified_at')))
def _ensure_tickets(repo,date,ms,model_version='60.0.0'):
    init(repo); existing=repo.rows('SELECT * FROM progol_tickets WHERE match_date=? ORDER BY ticket_no',(date,)); by_no={int(r['ticket_no']):r for r in existing}; rng=random.Random(56025+sum(ord(c) for c in date))
    for no in range(1,21):
        if no in by_no:continue
        sels=[]
        for m in ms:
            p=m.get('probabilities') or {}; vals=['1','X','2']; weights=[float(p.get(k,0)) for k in vals]; temp=1+((no-1)%5)*.12; w=[max(1e-9,x)**(1/temp) for x in weights]; total=sum(w); w=[x/total for x in w]; u=rng.random(); acc=0; pick='2'
            for k,ww in zip(vals,w):
                acc+=ww
                if u<=acc:pick=k;break
            sels.append(pick)
        if all(x=='1' for x in sels):
            idx=min(range(len(sels)),key=lambda j:(ms[j].get('probabilities') or {}).get('X',0)+(ms[j].get('probabilities') or {}).get('2',0)); p=ms[idx].get('probabilities') or {}; sels[idx]='X' if p.get('X',0)>=p.get('2',0) else '2'
        payload=json.dumps(sels,separators=(',',':'))
        dup=repo.one('SELECT id FROM progol_tickets WHERE match_date=? AND selections_json=?',(date,payload))
        if dup and sels:
            idx=(no-1)%len(sels); p=ms[idx].get('probabilities') or {}; sels[idx]='X' if p.get('X',0)>=p.get('2',0) else '2'; payload=json.dumps(sels,separators=(',',':'))
        repo.execute('INSERT INTO progol_tickets(match_date,ticket_no,model_version,selections_json) VALUES(?,?,?,?)',(date,no,model_version,payload))
    return repo.rows('SELECT * FROM progol_tickets WHERE match_date=? ORDER BY ticket_no',(date,))
def generate(repo,date):
    ms=matches(repo,date); init(repo)
    if not ms:return {'date':date,'tickets':[],'matches':[],'note':'Sin partidos'}
    _sync_results(repo,ms); tickets=_ensure_tickets(repo,date,ms); results={r['match_id']:r for r in repo.rows('SELECT * FROM progol_match_results WHERE match_date=?',(date,))}
    headers=[]
    for i,m in enumerate(ms,1):
        t=mexico_time(m); headers.append({'match_id':m['id'],'q':f'Q{i}','home':m['home'],'away':m['away'],'date_mx':t['date_mx'],'time_mx':t['time_mx'],'time_status':t['status'],'time_source':t['source'],'competition':m['competition']})
    out=[]
    for r in tickets:
        sels=json.loads(r['selections_json']); cells=[]; correct=wrong=pending=0
        for m,sel in zip(ms,sels):
            actual=results.get(m['id'],{}).get('actual'); state='pending' if not actual else 'correct' if sel==actual else 'wrong'; correct+=state=='correct'; wrong+=state=='wrong'; pending+=state=='pending'; cells.append({'selection':sel,'state':state,'actual':actual})
        out.append({'id':int(r['ticket_no']),'model_version':r['model_version'],'selections':sels,'cells':cells,'correct':correct,'wrong':wrong,'pending':pending,'complete':pending==0,'score':f'{correct}/{len(ms)}' if pending==0 else f'{correct}/{len(ms)}*'})
    finished=sum(1 for r in results.values() if r.get('actual')); return {'date':date,'tickets':out,'matches':headers,'match_count':len(ms),'finished_matches':finished,'completed_tickets':sum(t['complete'] for t in out),'all_correct_tickets':sum(t['complete'] and t['correct']==len(ms) for t in out),'result_summary':{'finished':finished,'pending':len(ms)-finished,'best_score':max((t['correct'] for t in out),default=0)},'note':'20 combinaciones persistentes. Verde=acierto, rojo=fallo, gris=pendiente. Un resultado no verificado nunca cuenta como error.'}

# --- Progol contest-specific presentation (isolated from the rest of LiAn) ---
CONTESTS = {
    '2349': {'kind':'fin_semana','label':'Progol fin de semana 2349',
        'matches':[
            ('2349-01','2026-09-04','21:00','MX-LIGA','FC Juárez','Pachuca'),
            ('2349-02','2026-09-06','19:15','LEAGUES-CUP','Toluca','Monterrey'),
            ('2349-03','2026-09-06','16:00','LEAGUES-CUP','América','León'),
            ('2349-04','2026-09-05','19:06','MX-LIGA-FEM','Tijuana Femenil','Pachuca Femenil'),
            ('2349-05','2026-09-06','11:00','ES-LALIGA','Athletic de Bilbao','Atlético de Madrid'),
            ('2349-06','2026-09-06','10:30','ES-LALIGA','Espanyol','Sevilla'),
            ('2349-07','2026-09-06','07:00','EN-PL','Fulham','Crystal Palace'),
            ('2349-08','2026-09-06','09:30','EN-PL','Nottingham Forest','Tottenham'),
            ('2349-09','2026-09-06','13:45','IT-SERIEA','Juventus','Milan'),
            ('2349-10','2026-09-06','07:30','NL-EREDIVISIE','Ajax','PSV'),
            ('2349-11','2026-09-06','09:45','NL-EREDIVISIE','Willem II','Excelsior'),
            ('2349-12','2026-09-06','09:45','NL-EREDIVISIE','Groningen','Twente'),
            ('2349-13','2026-09-06','18:00','MLS','Charlotte FC','Houston Dynamo'),
            ('2349-14','2026-09-06','18:30','MLS','Toronto FC','Chicago Fire'),
        ],
        'revancha': [
            ('2349-R01','2026-09-05','17:00','MX-LIGA','Atlético de San Luis','Guadalajara'),
            ('2349-R02','2026-09-06','15:00','MX-LIGA','Tigres UANL','Necaxa'),
            ('2349-R03','2026-09-06','17:00','MX-LIGA','Atlas','Atlante'),
            ('2349-R04','2026-09-06','11:30','EN-PL','Arsenal','Chelsea'),
            ('2349-R05','2026-09-05','13:00','IT-SERIEA','Inter','Napoli'),
            ('2349-R06','2026-09-05','15:45','IT-SERIEA','Roma','Atalanta'),
            ('2349-R07','2026-09-07','12:30','IT-SERIEA','Cagliari','Lecce'),
        ]},
    '2348': {'kind':'fin_semana','label':'Progol fin de semana 2348',
        'matches':[
            ('2348-01','2026-08-28','21:00','MX-LIGA','Tijuana','Pumas'),
            ('2348-02','2026-08-29','17:00','MX-LIGA','Pachuca','Guadalajara'),
            ('2348-03','2026-08-30','17:00','MX-LIGA-FEM','San Luis Femenil','Atlas Femenil'),
            ('2348-04','2026-08-30','11:30','ES-LALIGA','Deportivo La Coruña','Valencia'),
            ('2348-05','2026-08-30','13:30','ES-LALIGA','Celta','Athletic de Bilbao'),
            ('2348-06','2026-08-30','07:00','EN-PL','Leeds','Brentford'),
            ('2348-07','2026-08-30','07:00','EN-PL','Sunderland','Fulham'),
            ('2348-08','2026-08-29','10:30','IT-SERIEA','Sassuolo','Torino'),
            ('2348-09','2026-08-29','07:30','DE-BUND','Union Berlin','Eintracht Frankfurt'),
            ('2348-10','2026-08-29','12:45','FR-L1','Brest','Toulouse'),
            ('2348-11','2026-08-30','12:00','PT-PRIMEIRA','Casa Pia','Moreirense'),
            ('2348-12','2026-08-30','20:30','MLS','San Diego FC','LA Galaxy'),
            ('2348-13','2026-08-30','17:00','MLS','St. Louis City','FC Dallas'),
            ('2348-14','2026-08-30','18:30','AR-LIGA','Atlético Tucumán','Belgrano'),
        ],
        'revancha':[
            ('2348-R01','2026-08-30','17:00','MX-LIGA','Atlas','Querétaro'),
            ('2348-R02','2026-08-30','19:00','MX-LIGA','América','Puebla'),
            ('2348-R03','2026-08-30','21:00','MX-LIGA','Santos Laguna','Tigres'),
            ('2348-R04','2026-08-31','18:00','MX-LIGA','Monterrey','Atlético San Luis'),
            ('2348-R05','2026-08-29','13:30','ES-LALIGA','Sevilla','Atlético de Madrid'),
            ('2348-R06','2026-08-30','09:30','DE-BUND','Augsburgo','Schalke'),
            ('2348-R07','2026-08-30','12:45','FR-L1','Mónaco','Marsella'),
        ]},
    '810': {'kind':'media_semana','label':'Progol de media semana 810',
        'matches':[
            ('810-01','2026-08-25','18:30','MLS','Monterrey','Chicago Fire FC'),
            ('810-02','2026-08-25','20:30','MLS','Club León','Real Salt Lake'),
            ('810-03','2026-08-26','18:30','MLS','Toluca','Austin FC'),
            ('810-04','2026-08-26','20:45','MLS','América','Columbus Crew'),
            ('810-05','2026-08-26','13:00','UEFA-CL-Q','Viking','Dinamo Zagreb'),
            ('810-06','2026-08-26','13:00','UEFA-CL-Q','Celje','Slovan Bratislava'),
            ('810-07','2026-08-26','13:00','UEFA-CL-Q','Lyon','Fenerbahce'),
            ('810-08','2026-08-25','13:00','ES-LALIGA','Valencia','Real Betis'),
            ('810-09','2026-08-25','18:00','BR-CUP','Cruzeiro','Atlético Mineiro'),
        ]}
}

def _contest_match(repo, row):
    mid,date,time,comp,home,away=row
    m={'id':mid,'date':date,'time':time,'competition_id':comp,'competition':comp,'country':'','region':'','home':home,'away':away,'status':'scheduled','home_score':None,'away_score':None}
    from ..core.model import Model
    m.update(Model(repo).predict(m))
    m.update({'date_mx':date,'time_mx':time,'time_status':'VERIFICADA','time_source':'programación de concurso Progol'})
    return m

def _contest_init(repo):
    c=repo.connect()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS progol_contest_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, contest_id TEXT NOT NULL, ticket_no INTEGER NOT NULL, selections_json TEXT NOT NULL, model_version TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(contest_id,ticket_no))''')
    finally:c.close()

def generate_contest(repo, contest_id):
    from ..core.model import Model
    from ..services.calendar_clock import mexico_today_iso
    if contest_id not in CONTESTS: return {'error':'Concurso Progol no disponible','contest_id':contest_id}
    cfg=CONTESTS[contest_id]; _contest_init(repo)
    main=[_contest_match(repo,r) for r in cfg['matches']]
    rev=[_contest_match(repo,r) for r in cfg.get('revancha',[])]
    groups={'main':main,'revancha':rev} if cfg['kind']=='fin_semana' else {'main':main}
    outgroups=[]
    for gname,ms in groups.items():
        cid=f'{contest_id}:{gname}'
        existing=repo.rows('SELECT * FROM progol_contest_tickets WHERE contest_id=? ORDER BY ticket_no',(cid,)); by={int(x['ticket_no']):x for x in existing}
        # Future/current contests must always use the current prediction core. Historical
        # contests are immutable so their original pre-match tickets remain valid
        # benchmarks and can feed Adaptive Learning without leakage.
        latest_date=max((m['date'] for m in ms), default='0000-00-00')
        future_or_current=latest_date >= mexico_today_iso()
        if future_or_current and any(str(x.get('model_version')) != Model.VERSION for x in existing):
            repo.execute('DELETE FROM progol_contest_tickets WHERE contest_id=?',(cid,)); by={}
        rng=random.Random(56025+sum(ord(c) for c in cid))
        for no in range(1,21):
            if no in by: continue
            sels=[]
            for m in ms:
                # Exactly the same LiAn Model.predict probabilities used by the normal
                # Match Intelligence flow. Progol is only a portfolio layer on top.
                p=m.get('probabilities') or {}; vals=['1','X','2']; weights=[max(1e-9,float(p.get(k,0))) for k in vals]
                temp=1+((no-1)%5)*.10
                weights=[w**(1/temp) for w in weights]; total=sum(weights); weights=[w/total for w in weights]
                u=rng.random(); acc=0; pick='2'
                for k,w in zip(vals,weights):
                    acc+=w
                    if u<=acc: pick=k; break
                sels.append(pick)
            # Portfolio diversity without overriding a strong model edge.
            if len(set(sels))==1 and len(sels)>1:
                idx=(no-1)%len(sels); p=ms[idx].get('probabilities') or {}
                ordered=sorted(('1','X','2'),key=lambda k:p.get(k,0),reverse=True)
                sels[idx]=ordered[1]
            payload=json.dumps(sels,separators=(',',':'))
            repo.execute('INSERT INTO progol_contest_tickets(contest_id,ticket_no,selections_json,model_version) VALUES(?,?,?,?)',(cid,no,payload,Model.VERSION))
        rows=repo.rows('SELECT * FROM progol_contest_tickets WHERE contest_id=? ORDER BY ticket_no',(cid,))
        tickets=[{'id':int(r['ticket_no']),'selections':json.loads(r['selections_json']),'model_version':r['model_version']} for r in rows]
        outgroups.append({'key':gname,'label':'Progol · 14 partidos' if gname=='main' and cfg['kind']=='fin_semana' else 'Revancha · 7 partidos' if gname=='revancha' else 'Media semana · 9 partidos','matches':[{'id':m['id'],'q':f"Q{i}",'home':m['home'],'away':m['away'],'date_mx':m['date_mx'],'time_mx':m['time_mx'],'time_status':m['time_status']} for i,m in enumerate(ms,1)],'tickets':tickets,'count':len(ms),'max':len(ms)})
    return {'contest_id':contest_id,'label':cfg['label'],'kind':cfg['kind'],'groups':outgroups,'ticket_count':20,'note':'Progol utiliza exactamente las probabilidades del LiAn Prediction Core vigente; las 20 quinielas son una capa de diversificación sobre ese mismo motor. Los concursos históricos permanecen congelados para evitar fuga de información.'}
