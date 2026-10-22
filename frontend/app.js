const LIAN_VERSION = '64.6.0 FINAL FAST';
const $ = s => document.querySelector(s);
const out = $('#out');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let view = 'day'; let data = []; let selected = new Set();
const BACKEND = "https://lian-backend.onrender.com";
async function api(u) {
  const full = u.startsWith('/api') ? BACKEND + u : u;
  const r = await fetch(full, { cache: 'no-store', mode: 'cors' });
  let x = {}; try { x = await r.json(); } catch (_) { throw Error('Respuesta inválida del servidor'); }
  if (!r.ok) throw Error(x.error || `HTTP ${r.status}`); return x;
}
function pct(x) { return (Number(x || 0) * 100).toFixed(1) + '%'; }
function qclass(q) { return q === 'ALTA' ? 'high' : q === 'MEDIA' ? 'mid' : 'low'; }
function bar(v) { return `<div class="mini-bar"><i style="width:${Math.max(2, Math.min(100, Number(v || 0) * 100))}%"></i></div>`; }
function card(m) {
  const p = m.probabilities || {}; const e = m.explainability || {}; const f = m.features || {}; const c = m.consensus || {}; const st = m.stability || {};
  const status = e.status || (m.prediction_fast ? 'CARGANDO...' : 'SIN ANÁLISIS');
  const favorite = e.favorite ? esc(e.favorite) : (m.prediction_fast ? 'Calculando...' : 'Sin selección');
  const analysis = esc(e.analysis || m.rationale || (m.prediction_fast ? 'Cargando análisis completo...' : 'Sin análisis.'));
  return `<article class="card ${m.prediction_fast ? 'card-fast' : ''}"><div class="meta"><span>${esc(m.competition)} · ${esc(m.time_mx || m.time || '')} MX</span><span class="badge ${qclass(m.quality)}">${esc(m.quality || (m.prediction_fast ? 'FAST' : '—'))}</span><span class="badge">${esc(m.display_status || 'PRÓXIMO')}</span>${m.prediction_fast ? '<span class="badge low">FAST</span>' : ''}</div><div class="teams"><span>${esc(m.home)}</span><span class="vs">VS</span><span>${esc(m.away)}</span></div><div class="probs"><div class="prob"><small>LOCAL</small><b>${pct(p['1'])}</b></div><div class="prob"><small>EMPATE</small><b>${pct(p.X)}</b></div><div class="prob"><small>VISITA</small><b>${pct(p['2'])}</b></div></div><div class="decision"><div><small>Lectura</small><strong>${esc(status)}</strong></div><div><small>Preferencia</small><strong>${favorite}</strong></div></div><div class="analysis-box"><b>Análisis</b><p>${analysis}</p></div><div class="detail">xG: ${m.expected_goals?.home ?? '-'} — ${m.expected_goals?.away ?? '-'} · total ${m.expected_goals?.total ?? '-'}</div><div class="evidence"><i style="width:${Math.max(3, Math.min(100, (m.evidence || 0) * 100))}%"></i></div></article>`;
}
function renderDay(comps) {
  let ms = data.filter(m => !selected.size || selected.has(m.competition_id));
  const fastCount = ms.filter(m => m.prediction_fast).length;
  out.innerHTML = ms.length ? `<div class="hero"><h2>${ms.length} partidos ${fastCount ? `<small style="color:#f6c343">· ${fastCount} en FAST</small>` : ''}</h2><div class="stats"><div class="stat"><small>Alta</small><b>${ms.filter(x => x.quality === 'ALTA').length}</b></div><div class="stat"><small>Media</small><b>${ms.filter(x => x.quality === 'MEDIA').length}</b></div><div class="stat"><small>Baja</small><b>${ms.filter(x => x.quality === 'BAJA').length}</b></div><div class="stat"><small>Versión</small><b>${LIAN_VERSION}</b></div></div></div><div class="grid">${ms.map(card).join('')}</div>` : `<div class="empty">No hay partidos para filtros.</div>`;
}
function closeLeagueMenu() { const menu = $('#league-menu'); if (menu) { menu.classList.remove('open'); menu.setAttribute('aria-hidden', 'true'); } }
function leagueLabel() { if (!selected.size) return 'Todas las ligas'; return `${selected.size} ligas seleccionadas`; }
function filterBar(comps) {
  window.__lianComps = comps || []; const count = comps.reduce((n, c) => n + Number(c.n || 0), 0);
  $('#filters').innerHTML = `<div class="league-filter"><button id="league-menu-toggle" class="league-filter-btn" type="button"><span><b>${esc(leagueLabel())}</b><small>${comps.length} ligas · ${count} partidos</small></span></button><div id="league-menu" class="league-menu"><div class="league-options"><button type="button" class="league-option league-all ${!selected.size ? 'checked' : ''}" data-all><span><b>Todas</b></span></button>${comps.map(c => `<button type="button" class="league-option ${selected.has(c.competition_id) ? 'checked' : ''}" data-c="${esc(c.competition_id)}"><span><b>${esc(c.competition)}</b><small>${Number(c.n || 0)} partidos</small></span></button>`).join('')}</div><div class="league-menu-foot"><button id="league-clear" type="button">Limpiar</button><button id="league-done" type="button">Aplicar</button></div></div></div>`;
  const toggle = $('#league-menu-toggle'), menu = $('#league-menu');
  toggle.onclick = () => menu.classList.toggle('open');
  $('#league-menu-close')?.addEventListener && ($('#league-menu-close').onclick = closeLeagueMenu);
  document.getElementById('league-done') && (document.getElementById('league-done').onclick = closeLeagueMenu);
  document.getElementById('league-clear') && (document.getElementById('league-clear').onclick = () => { selected.clear(); renderDay(comps); filterBar(comps); closeLeagueMenu(); });
  document.querySelector('[data-all]') && (document.querySelector('[data-all]').onclick = () => { selected.clear(); renderDay(comps); filterBar(comps); closeLeagueMenu(); });
  document.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { const c = b.dataset.c; selected.has(c) ? selected.delete(c) : selected.add(c); renderDay(comps); filterBar(comps); closeLeagueMenu(); });
}
function mxToday() { return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); }
function clampFutureDate(d) { const t = new Date(mxToday() + 'T00:00:00'); const x = new Date(d + 'T00:00:00'); const max = new Date(t); max.setDate(max.getDate() + 29); return x > max ? mxToday() : d; }

async function loadDay() {
  view = 'day'; selected.clear();
  const d = clampFutureDate($('#date').value || mxToday());
  $('#date').value = d;
  $('#title').textContent = 'Partidos del día';
  $('#subtitle').textContent = `${d} · hora de México · carga rápida FINAL`;
  try {
    $('#status').textContent = `Cargando rápido ${d}...`;
    const fast = await api('/api/calendar/fast?date=' + encodeURIComponent(d));
    data = (fast.matches || []).filter(m => m.date === d).map(m => ({ ...m, prediction_fast: true }));
    filterBar(fast.competitions || []); renderDay(fast.competitions || []);
    $('#status').textContent = `API ${LIAN_VERSION} · ${fast.count || 0} partidos (FAST <1s)`;
    $('.dot').style.background = '#32d583';
  } catch (e) { console.warn('Fast fail', e); }
  try {
    $('#status').textContent = `Calculando predicciones ${d}...`;
    const x = await api('/api/calendar?date=' + encodeURIComponent(d));
    data = (x.matches || []).filter(m => m.date === d);
    filterBar(x.competitions || []); renderDay(x.competitions || []);
    $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos · completo`;
    $('.dot').style.background = '#32d583';
    localStorage.setItem(`lian_${d}`, JSON.stringify(x));
  } catch (e) { $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos (FAST)`; }
}
async function loadTop() { view='top'; $('#title').textContent='Top Picks'; $('#subtitle').textContent='Ranking por probabilidad'; $('#filters').innerHTML=''; const x=await api('/api/top-picks?date='+($('#date').value||mxToday())); const items=Array.isArray(x.items)?x.items:[]; out.innerHTML=items.length?'<div class="grid">'+items.map(card).join('')+'</div>':'<div class="empty">No hay selecciones.</div>'; }
async function load() {
  try { const h=await api('/api/health'); $('#status').textContent=`API ${h.version} · ${h.records} registros`; $('.dot').style.background='#32d583'; } catch(e){ $('#status').textContent='API con error'; $('.dot').style.background='#ff6b7a'; out.innerHTML=`<div class="empty">No se pudo conectar: ${esc(e.message)}</div>`; return; }
  try { if(view==='day') await loadDay(); else if(view==='top') await loadTop(); else await loadDay(); } catch(e){ out.innerHTML=`<div class="empty"><b>Error vista:</b> ${esc(e.message)}</div>`; }
}
if (!$('#date').value) $('#date').value = mxToday();
document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>{ document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active')); b.classList.add('active'); ({day:loadDay,top:loadTop}[b.dataset.view]||loadDay)(); });
$('#refresh').onclick = async () => {
  const d = $('#date').value || mxToday();
  $('#status').textContent = `🔄 Sincronización en segundo plano ${d} (10-15s)...`;
  $('.dot').style.background = '#f6c343';
  out.innerHTML = '<div class="empty">🔄 Sincronización iniciada en background... La página seguirá mostrando los partidos actuales mientras se actualiza. En 10-15s dale de nuevo a Partidos del día.</div>';
  try {
    const x = await api('/api/calendar?date=' + encodeURIComponent(d) + '&refresh=1');
    $('#status').textContent = `Sincronización iniciada · ${x.fixture_sync?.message || 'background'}`;
    // Poll cada 3s
    let tries=0;
    const poll = setInterval(async ()=>{
      tries++;
      try {
        const s = await api('/api/sync-status');
        if(!s.running || tries>6){
          clearInterval(poll);
          const y = await api('/api/calendar?date=' + encodeURIComponent(d));
          data = (y.matches||[]).filter(m=>m.date===d);
          filterBar(y.competitions||[]); renderDay(y.competitions||[]);
          $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos · actualizado`;
          $('.dot').style.background='#32d583';
        } else {
          $('#status').textContent = `🔄 Sincronizando... ${tries*3}s`;
        }
      } catch(e){ clearInterval(poll); }
    }, 3000);
  } catch(e){ out.innerHTML=`<div class="empty">Error: ${esc(e.message)}</div>`; }
};
$('#date').onchange = () => loadDay();
load();
