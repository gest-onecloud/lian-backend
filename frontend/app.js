const LIAN_VERSION = '64.6.0';
const $ = s => document.querySelector(s);
const out = $('#out');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));

let view = 'day';
let data = [];
let selected = new Set();
const BACKEND = "https://lian-backend.onrender.com";

async function api(u) {
  const full = u.startsWith('/api') ? BACKEND + u : u;
  const r = await fetch(full, { cache: 'no-store', mode: 'cors' });
  let x = {};
  try { x = await r.json(); } catch (_) { throw Error('Respuesta inválida del servidor'); }
  if (!r.ok) throw Error(x.error || `HTTP ${r.status}`);
  return x;
}
function pct(x) { return (Number(x || 0) * 100).toFixed(1) + '%'; }
function qclass(q) { return q === 'ALTA' ? 'high' : q === 'MEDIA' ? 'mid' : 'low'; }
function bar(v) { return `<div class="mini-bar"><i style="width:${Math.max(2, Math.min(100, Number(v || 0) * 100))}%"></i></div>`; }

function card(m) {
  const p = m.probabilities || {};
  const e = m.explainability || {};
  const f = m.features || {};
  const c = m.consensus || {};
  const st = m.stability || {};
  const cf = m.counterfactual || {};
  const status = e.status || (m.prediction_fast ? 'CARGANDO ANÁLISIS...' : 'ANÁLISIS NO DISPONIBLE');
  const favorite = e.favorite ? esc(e.favorite) : (m.prediction_fast ? 'Calculando...' : 'Sin selección');
  const analysis = esc(e.analysis || m.rationale || (m.prediction_fast ? 'Cargando análisis completo en segundo plano...' : 'Sin análisis disponible.'));
  const why = (e.why || []).map(x => `<div class="reason"><b>${esc(x.factor)}</b><span>${esc(x.effect)}</span></div>`).join('');
  const sig = (m.signals || []).slice(0, 8).map(x => `<div class="signal"><div><b>${esc(x.factor)}</b><small>${esc(x.direction)}</small></div><strong>${(Number(x.share || 0) * 100).toFixed(1)}%</strong>${bar(x.share)}</div>`).join('');
  const markets = m.markets || {};
  return `<article class="card ${m.prediction_fast ? 'card-fast' : ''}">
    <div class="meta">
      <span>${esc(m.competition)} · ${esc(m.time_mx || m.time || '')} MX</span>
      <span class="badge ${qclass(m.quality)}">${esc(m.quality || (m.prediction_fast ? 'CARGANDO' : 'SIN CALIDAD'))}</span>
      <span class="badge">${esc(m.display_status || 'PRÓXIMO')}</span>
      ${m.prediction_fast ? '<span class="badge low">FAST</span>' : ''}
    </div>
    <div class="teams"><span>${esc(m.home)}</span><span class="vs">VS</span><span>${esc(m.away)}</span></div>
    ${m.selection_eligible === false ? `<div class="detail" style="margin-top:8px"><b>PUERTA DE DATOS:</b> ${esc(m.data_sufficiency?.reason || 'evidencia insuficiente')}</div>` : ''}
    ${m.prediction_source === 'RETROSPECTIVE_RECONSTRUCTION' ? `<div class="detail" style="margin-top:8px"><b>AVISO:</b> no existe registro de predicción prepartido</div>` : ''}
    ${m.display_status === 'FINALIZADO' ? `<div class="final-box"><b>FINAL ${esc(m.display_result || m.result?.final || '')}</b><span class="badge ${m.result?.eligible_for_metrics ? (m.result?.correct ? 'high' : 'low') : 'mid'}">${m.result?.eligible_for_metrics ? (m.result?.correct ? 'ACIERTO' : 'FALLA') : 'SIN EVALUACIÓN'}</span><small>Fuente: ${esc(m.result?.source || 'verificada')}</small></div>` : ''}
    <div class="probs"><div class="prob"><small>LOCAL</small><b>${pct(p['1'])}</b></div><div class="prob"><small>EMPATE</small><b>${pct(p.X)}</b></div><div class="prob"><small>VISITA</small><b>${pct(p['2'])}</b></div></div>
    <div class="decision"><div><small>Lectura LiAn</small><strong>${esc(status)}</strong></div><div><small>Preferencia</small><strong>${favorite}</strong></div><div><small>Separación</small><strong>${Number(e.separation_points || 0).toFixed(1)} pp</strong></div></div>
    <div class="metrics-row"><span>Confianza <b>${pct(m.confidence)}</b></span><span>Evidencia <b>${pct(m.evidence)}</b></span><span>Riesgo <b>${esc(e.risk || '—')}</b></span><span>Estabilidad <b>${((Number(st.score || 0) * 100).toFixed(1))}%</b></span></div>
    ${m.error_fingerprint ? `<div class="risk-fingerprint"><b>Fingerprint:</b> <span class="badge ${m.error_fingerprint.level === 'RIESGO ELEVADO' ? 'low' : m.error_fingerprint.level === 'RIESGO MODERADO' ? 'mid' : 'high'}">${esc(m.error_fingerprint.level)}</span><small>${esc(m.error_fingerprint.message)}</small></div>` : ''}
    <div class="analysis-box"><b>Lectura general</b><p>${analysis}</p><div class="suggestion"><b>Sugerencia:</b> ${esc(e.recommendation || 'Sin sugerencia.')}</div><div class="suggestion"><b>Cobertura:</b> ${esc(e.coverage || 'No disponible.')}</div></div>
    <div class="detail venue-line">Sede: <b>${esc(e.venue?.venue || 'No verificada')}</b> · ${esc(e.venue?.status || 'SIN DATOS')}</div>
    <div class="detail"><b>xG:</b> ${m.expected_goals?.home ?? '-'} — ${m.expected_goals?.away ?? '-'} · total ${m.expected_goals?.total ?? '-'} · <b>GF/10:</b> ${f.gf10_home ?? '-'} — ${f.gf10_away ?? '-'} · <b>xG/10:</b> ${f.xg_home ?? '-'} — ${f.xg_away ?? '-'}</div>
    <div class="detail"><b>Ajustado rival GF/10:</b> ${f.adj_gf10_home ?? '-'} — ${f.adj_gf10_away ?? '-'} · <b>GA/10:</b> ${f.adj_ga10_home ?? '-'} — ${f.adj_ga10_away ?? '-'} · <b>Forma:</b> ${f.form_diff ?? '-'} · <b>Tendencia:</b> ${f.momentum_diff ?? '-'}</div>
    <details class="more" ${m.prediction_fast ? '' : 'open'}><summary>¿Por qué eligió este equipo?</summary><div class="detail">${why || 'Sin señales registradas.'}<div class="signal-list">${sig || ''}</div><div class="two-col"><div><b>Consenso:</b> ${pct(c.score)}<br>Poisson ${pct(c.poisson?.[e.top_result] || 0)} · ELO ${pct(c.strength?.[e.top_result] || 0)} · Forma ${pct(c.form?.[e.top_result] || 0)} · Monte ${pct(c.monte_carlo?.[e.top_result] || 0)}</div><div><b>Estabilidad:</b> ${pct(st.score)}<br>Sin sede cambia: <b>${cf.flip_without_venue ? 'SÍ' : 'NO'}</b><br>Sin forma cambia: <b>${cf.flip_without_form ? 'SÍ' : 'NO'}</b></div></div><div class="detail"><b>Qué podría cambiar:</b> ${esc((cf.what_changes_choice || []).join(' · '))}</div></div></details>
    <details class="more"><summary>Mercados derivados</summary><div class="detail">Over 1.5: ${pct(markets.over_1_5)} · Over 2.5: ${pct(markets.over_2_5)} · BTTS: ${pct(markets.btts_yes)}</div></details>
    <div class="detail">Histórico H/A ${f.home_history ?? 0}/${f.away_history ?? 0} · H2H ${f.h2h ?? 0} · consenso ${pct(c.score)}</div>
    <div class="evidence"><i style="width:${Math.max(3, Math.min(100, (m.evidence || 0) * 100))}%"></i></div>
  </article>`;
}
function renderDay(comps) {
  let ms = data.filter(m => !selected.size || selected.has(m.competition_id));
  const fastCount = ms.filter(m => m.prediction_fast).length;
  out.innerHTML = ms.length ? `<div class="hero"><h2>${ms.length} partidos encontrados ${fastCount ? `<small style="color:#f6c343">· ${fastCount} cargando análisis...</small>` : ''}</h2><div class="stats"><div class="stat"><small>Alta evidencia</small><b>${ms.filter(x => x.quality === 'ALTA').length}</b></div><div class="stat"><small>Media</small><b>${ms.filter(x => x.quality === 'MEDIA').length}</b></div><div class="stat"><small>Baja</small><b>${ms.filter(x => x.quality === 'BAJA').length}</b></div><div class="stat"><small>Plataforma</small><b>V64.6.0</b></div><div class="stat"><small>Motor</small><b>V64.0.0</b></div></div></div><div class="grid">${ms.map(card).join('')}</div>` : `<div class="empty">No hay partidos para los filtros seleccionados.</div>`;
}
function closeLeagueMenu() { const menu = $('#league-menu'); if (menu) { menu.classList.remove('open'); menu.setAttribute('aria-hidden', 'true'); const btn = $('#league-menu-toggle'); if (btn) btn.setAttribute('aria-expanded', 'false'); } }
function leagueLabel() { if (!selected.size) return 'Todas las ligas'; const names = [...selected].map(id => { const c = window.__lianComps.find(x => String(x.competition_id) === String(id)); return c?.competition || id; }); return names.length === 1 ? names[0] : `${names.length} ligas seleccionadas`; }
function filterBar(comps) {
  window.__lianComps = comps || [];
  const count = comps.reduce((n, c) => n + Number(c.n || 0), 0);
  const selectedLabel = leagueLabel();
  $('#filters').innerHTML = `<div class="league-filter"><button id="league-menu-toggle" class="league-filter-btn" type="button" aria-haspopup="dialog" aria-expanded="false"><span class="league-filter-icon">⚽</span><span><b>${esc(selectedLabel)}</b><small>${selected.size ? `${selected.size} seleccionada${selected.size === 1 ? '' : 's'}` : `${comps.length} ligas · ${count} partidos`}</small></span><span class="league-filter-chevron">⌄</span></button><div id="league-menu" class="league-menu" role="dialog" aria-hidden="true"><div class="league-menu-head"><div><b>Selecciona las ligas</b><small>${selected.size ? `${selected.size} seleccionada${selected.size === 1 ? '' : 's'}` : 'Todas las ligas'}</small></div><button id="league-menu-close" type="button" aria-label="Cerrar">×</button></div><div class="league-search-wrap"><span>⌕</span><input id="league-search" type="search" autocomplete="off" placeholder="Buscar liga…"></div><div class="league-options"><button type="button" class="league-option league-all ${!selected.size ? 'checked' : ''}" data-all><span class="check-box">${!selected.size ? '✓' : ''}</span><span><b>Todas</b><small>Mostrar todas</small></span></button>${comps.map(c => `<button type="button" class="league-option ${selected.has(c.competition_id) ? 'checked' : ''}" data-c="${esc(c.competition_id)}" data-name="${esc(c.competition).toLowerCase()}"><span class="check-box">${selected.has(c.competition_id) ? '✓' : ''}</span><span><b>${esc(c.competition)}</b><small>${Number(c.n || 0)} partido${Number(c.n || 0) === 1 ? '' : 's'}</small></span></button>`).join('')}</div><div class="league-menu-foot"><button id="league-clear" type="button" class="league-secondary">Limpiar</button><button id="league-done" type="button" class="league-primary">Aplicar</button></div></div></div>`;
  const toggle = $('#league-menu-toggle'), menu = $('#league-menu');
  toggle.onclick = () => { const open = menu.classList.toggle('open'); menu.setAttribute('aria-hidden', String(!open)); toggle.setAttribute('aria-expanded', String(open)); if (open) { const q = $('#league-search'); if (q) { q.value = ''; q.focus(); } } };
  $('#league-menu-close').onclick = closeLeagueMenu; $('#league-done').onclick = closeLeagueMenu; $('#league-clear').onclick = () => { selected.clear(); renderDay(comps); filterBar(comps); closeLeagueMenu(); };
  $('#filters [data-all]').onclick = () => { selected.clear(); renderDay(comps); filterBar(comps); closeLeagueMenu(); };
  document.querySelectorAll('#filters [data-c]').forEach(b => b.onclick = () => { const c = b.dataset.c; selected.has(c) ? selected.delete(c) : selected.add(c); renderDay(comps); filterBar(comps); closeLeagueMenu(); });
  const search = $('#league-search'); if (search) search.oninput = () => { const q = search.value.trim().toLowerCase(); document.querySelectorAll('#filters .league-option[data-c]').forEach(b => { b.hidden = !!q && !b.dataset.name.includes(q); }); };
}
document.addEventListener('click', e => { const host = $('.league-filter'); if (host && !host.contains(e.target)) closeLeagueMenu(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLeagueMenu(); });
function mxToday() { return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); }
function clampFutureDate(d) { const t = new Date(mxToday() + 'T00:00:00'); const x = new Date(d + 'T00:00:00'); const max = new Date(t); max.setDate(max.getDate() + 29); return x > max ? mxToday() : d; }

async function loadDay() {
  view = 'day'; selected.clear();
  const d = clampFutureDate($('#date').value || mxToday());
  $('#date').value = d;
  $('#title').textContent = 'Partidos del día';
  $('#subtitle').textContent = `${d} · hora de México · carga rápida`;
  
  // FASE 1: Carga ultra-rápida desde /fast (sin sync, sin modelo pesado) - <200ms
  try {
    $('#status').textContent = `Cargando rápido ${d}...`;
    $('.dot').style.background = '#f6c343';
    const cacheKey = `lian_${d}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        data = (parsed.matches || []).filter(m => m.date === d);
        if (data.length) { filterBar(parsed.competitions || []); renderDay(parsed.competitions || []); }
      } catch {}
    }
    const fast = await api('/api/calendar/fast?date=' + encodeURIComponent(d));
    data = (fast.matches || []).filter(m => m.date === d).map(m => ({ ...m, prediction_fast: true }));
    filterBar(fast.competitions || []);
    renderDay(fast.competitions || []);
    $('#status').textContent = `API ${LIAN_VERSION} · ${fast.count || fast.matches?.length || 0} partidos (rápido)`;
    $('.dot').style.background = '#32d583';
    localStorage.setItem(cacheKey, JSON.stringify(fast));
  } catch (e) {
    console.warn('Fast load failed', e);
  }

  // FASE 2: Carga completa en segundo plano (sin refresh, usa cache de 5 min) - 1-2s
  try {
    $('#status').textContent = `Calculando predicciones ${d}...`;
    $('.dot').style.background = '#f6c343';
    const x = await api('/api/calendar?date=' + encodeURIComponent(d));
    if (x.date !== d) throw new Error(`API devolvió ${x.date} para ${d}`);
    data = (x.matches || []).filter(m => m.date === d);
    filterBar(x.competitions || []);
    renderDay(x.competitions || []);
    const ci = x.calendar_integrity || {}; const fs = x.fixture_sync || {}; const status = fs.coverage_status || 'unknown';
    const note = status === 'complete' || status === 'complete-empty' ? 'Calendario verificado.' : status === 'partial' ? 'Cobertura parcial.' : 'Cobertura no verificada.';
    const sc = fs.source_counts || {};
    const hero = document.querySelector('#out .hero');
    if (hero) {
      hero.insertAdjacentHTML('beforeend', `<div class="detail calendar-status"><b>Estado:</b> ${esc(status)} · ${esc(note)} · Integridad: <b>${ci.date_exact ? 'OK' : 'ERROR'}</b> · duplicados: <b>${ci.unique_pairs ? '0' : 'DETECTADOS'}</b> · fuentes: ESPN ${Number(sc.ESPN_ALL || 0)} · Sofa ${Number(sc.SOFASCORE || 0)} · FotMob ${Number(sc.FOTMOB || 0)}</div>`);
    }
    $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos · análisis completo`;
    $('.dot').style.background = '#32d583';
    localStorage.setItem(`lian_${d}`, JSON.stringify(x));
  } catch (e) {
    $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos (rápido)`;
  }
}

async function loadTop() {
  view = 'top'; $('#title').textContent = 'Top Picks'; $('#subtitle').textContent = 'Ranking por probabilidad, evidencia, consenso'; $('#filters').innerHTML = '';
  const x = await api('/api/top-picks?date=' + ($('#date').value || mxToday()));
  const items = Array.isArray(x.items) ? x.items : [];
  out.innerHTML = items.length ? '<div class="grid">' + items.map(card).join('') + '</div>' : '<div class="empty">No hay selecciones elegibles. Faltan partidos con evidencia suficiente.</div>';
}
function comboBlock(level) {
  return `<section class="combo-level"><div class="level-head"><div><h2>${esc(level.level)}</h2><small>2 combinadas · evidencia y estabilidad</small></div></div><div class="grid">${level.combinations.map(c => `<article class="card"><div class="meta"><span>${esc(c.name)}</span><span class="badge ${c.status === 'RECOMENDADA' ? 'high' : c.status === 'CONDICIONAL' ? 'mid' : 'low'}">${esc(c.status)}</span></div>${c.selections.length ? c.selections.map((s, i) => `<div class="combo-row"><b>${i + 1}</b><span>${esc(s.home)} — ${esc(s.away)}</span><strong>${esc(s.pick)}</strong><small>${pct(s.probability)}</small></div>`).join('') : '<div class="empty">No hay suficientes selecciones con evidencia.</div>'}<div class="detail">Prob mínima conjunta: ${pct(c.estimated_min_probability)} · evidencia media ${pct(c.average_evidence)}</div></article>`).join('')}</div></section>`;
}
async function loadCombo() {
  view = 'combo'; $('#title').textContent = 'Combinadas'; $('#subtitle').textContent = '5 niveles · 2 combinadas por nivel'; $('#filters').innerHTML = '';
  const x = await api('/api/combinations?date=' + $('#date').value);
  out.innerHTML = `<div class="hero"><h2>${x.investigated} partidos investigados · ${x.eligible} elegibles</h2><p>${esc(x.note)}</p></div>${x.levels.map(comboBlock).join('')}`;
}
function progolCell(c) { const cls = c.state === 'correct' ? 'progol-correct' : c.state === 'wrong' ? 'progol-wrong' : 'progol-pending'; return `<td class="progol-cell ${cls}"><b>${esc(c.selection)}</b>${c.state === 'correct' ? '<span>✓</span>' : c.state === 'wrong' ? '<span>✕</span>' : '<span>•</span>'}</td>`; }
async function loadProgol() {
  view = 'progol'; $('#title').textContent = 'Progol'; $('#subtitle').textContent = 'Concursos independientes · 20 quinielas'; $('#filters').innerHTML = '';
  out.innerHTML = `<div class="progol-menu"><button class="progol-menu-btn active" data-pg="2349">Progol fin de semana<br><small>14 partidos + Revancha 7 · actual</small></button><button class="progol-menu-btn" data-pg="2348">Histórico 2348<br><small>Benchmark</small></button><button class="progol-menu-btn" data-pg="810">Progol media semana<br><small>9 partidos</small></button></div><div id="progol-content"></div>`;
  document.querySelectorAll('[data-pg]').forEach(b => b.onclick = () => { document.querySelectorAll('[data-pg]').forEach(x => x.classList.remove('active')); b.classList.add('active'); loadProgolContest(b.dataset.pg); });
  await loadProgolContest('2349');
}
async function loadProgolContest(id) {
  const host = $('#progol-content'); host.innerHTML = '<div class="empty">Cargando concurso Progol…</div>';
  try {
    const x = await api('/api/progol?contest=' + encodeURIComponent(id));
    const groups = x.groups || [];
    host.innerHTML = `<div class="hero"><h2>${esc(x.label)}</h2><p>${esc(x.note)}</p><div class="stats"><div class="stat"><small>Quinielas</small><b>${x.ticket_count}</b></div><div class="stat"><small>Bloques</small><b>${groups.length}</b></div><div class="stat"><small>Motor</small><b>V64.6.0</b></div></div></div>${groups.map((g, idx) => renderProgolGroup(g, idx > 0)).join('')}`;
  } catch (e) { host.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}
function renderProgolGroup(g, separated) {
  const tickets = g.tickets || [];
  const head = tickets.map(t => `<th class="progol-ticket-head">Q${t.id}</th>`).join('');
  const rows = (g.matches || []).map((m, i) => `<tr><th class="progol-match-id">${i + 1}</th><td class="progol-match"><b>${esc(m.home)}</b><span>vs</span><b>${esc(m.away)}</b><small>${esc(m.date_mx)} · ${esc(m.time_mx)} MX</small></td>${tickets.map(t => `<td class="progol-pick"><b>${esc(t.selections[i] || '—')}</b></td>`).join('')}<td class="progol-result"><b>—</b><small>PENDIENTE</small></td></tr>`).join('');
  return `<section class="progol-section ${separated ? 'progol-section-separator' : ''}"><div class="progol-section-title"><div><h2>${esc(g.label)}</h2><small>${g.count} partidos · máximo ${g.max} aciertos · 20 quinielas</small></div><span class="badge high">20 GENERADAS</span></div><div class="progol-wrap"><table class="table progol-table progol-grid"><thead><tr><th class="progol-match-id">#</th><th class="progol-match-head">PARTIDO · DÍA · HORA MX</th>${head}<th class="progol-result-head">RESULTADO</th></tr></thead><tbody>${rows}</tbody></table></div><div class="detail progol-legend">Las 20 quinielas quedan persistentes para este concurso.</div></section>`;
}
async function loadIntel() {
  view = 'intel'; $('#title').textContent = 'Match Search & Intelligence'; $('#subtitle').textContent = 'Busca cualquier partido'; $('#filters').innerHTML = '';
  out.innerHTML = `<div class="hero search-hero"><h2>🔎 Buscar partido</h2><p>Escribe equipos o partido. LiAn consulta índice local + descubrimiento multi-fuente ventana 30 días.</p><div class="search-row"><input id="search" class="search search-main" autocomplete="off" placeholder="Ej. Cruz Azul vs América"><button id="go" class="primary">Buscar</button></div><div id="search-hint" class="detail">Ventana: hoy → +29 días · hora México.</div></div><div id="search-results"></div>`;
  const input = $('#search'), res = $('#search-results');
  function renderCandidates(x, q) {
    const cs = x.candidates || []; const start = x.calendar_context?.window_start || x.calendar_context?.today_mx || ''; const end = x.calendar_context?.window_end || '';
    const header = `<div class="hero"><h3>Ventana inteligencia · 30 días</h3><p>${esc(start)} → ${esc(end)} · <b>${cs.length}</b> fixture(s).</p></div>`;
    const cards = cs.map(c => `<article class="card search-result"><div class="meta"><span>${esc(c.date)}${c.time ? ' · ' + esc(c.time) : ''} · ${esc(c.competition || '')}</span><span>${esc(c.display_status || (c.status === 'finished' ? 'FINALIZADO' : 'PRÓXIMO'))}</span></div><div class="teams"><span>${esc(c.home)}</span><span class="vs">VS</span><span>${esc(c.away)}</span></div><div class="detail">${c.search_score != null ? `Coincidencia ${Number(c.search_score || 0)} · ` : ''}${c.time ? esc(c.time) : 'hora no disponible'}</div><button class="primary choose-match" data-id="${esc(c.id)}">Analizar</button></article>`).join('');
    res.innerHTML = header + `<div class="grid">${cards}</div>`;
    document.querySelectorAll('.choose-match').forEach(b => b.onclick = () => analyzeId(b.dataset.id));
  }
  async function run() {
    const q = input.value.trim(); if (!q) { res.innerHTML = '<div class="empty">Escribe un partido o equipo.</div>'; return; }
    res.innerHTML = '<div class="empty">Buscando en LiAn: índice local + fuentes online…</div>';
    try {
      const x = await api('/api/universal-match?q=' + encodeURIComponent(q));
      if (x.ambiguous) { renderCandidates(x, q); return; }
      if (!x.found) {
        const hist = (x.historical_candidates || []).slice(0, 6).map(c => `<article class="card"><div class="meta"><span>${esc(c.date)} · ${esc(c.competition || '')}</span><span>HISTÓRICO</span></div><div class="teams"><span>${esc(c.home)}</span><span class="vs">VS</span><span>${esc(c.away)}</span></div></article>`).join('');
        res.innerHTML = `<div class="empty"><b>${esc(x.reason)}</b></div>${hist ? `<div class="hero" style="margin-top:14px"><h3>Histórico</h3><div class="grid">${hist}</div></div>` : ''}`;
        return;
      }
      renderCandidates(x, q);
    } catch (e) { res.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  async function analyzeId(id) {
    try { const x = await api('/api/intelligence?match_id=' + encodeURIComponent(id)); if (x.found) renderSearchMatch(x.match); else res.innerHTML = `<div class="empty">No se pudo resolver fixture ${esc(id)}.</div>`; } catch (e) { res.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  async function loadWindow() {
    try {
      const w = await api('/api/calendar-window?refresh=0');
      const days = (w.days || []); const fixtures = days.reduce((n, d) => n + Number(d.matches || 0), 0);
      const rows = days.map(d => `<div class="detail" style="display:flex;justify-content:space-between;gap:12px"><span>${esc(d.date)}</span><b>${d.matches} partido(s)</b></div>`).join('');
      const box = document.createElement('div'); box.className = 'hero'; box.style.marginTop = '14px'; box.innerHTML = `<h3>Ventana operativa · 30 días</h3><p>${esc(w.start)} → ${esc(w.end)} · <b>${fixtures}</b> fixtures.</p><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:4px">${rows}</div>`;
      res.before(box);
    } catch (e) { const box = document.createElement('div'); box.className = 'detail'; box.style.marginTop = '12px'; box.textContent = 'Ventana 30 días: no se pudo actualizar; se conserva índice local.'; res.before(box); }
  }
  function renderSearchMatch(m) { res.innerHTML = `<div class="hero"><div class="meta"><span>${esc(m.date)} · ${esc(m.competition || '')}</span><span>${m.display_status || (m.status === 'finished' ? 'PARTIDO FINALIZADO' : 'ANÁLISIS PREPARTIDO')}</span></div><h2>${esc(m.home)} vs ${esc(m.away)}</h2><div class="detail"><b>Resolución:</b> ${esc(m.resolution || 'CANONICAL_MATCH_ID')}</div></div>${card(m)}`; }
  $('#go').onclick = run; input.onkeydown = e => { if (e.key === 'Enter') run(); }; loadWindow(); input.focus();
}
async function loadLearning() {
  view = 'learning'; $('#title').textContent = 'Autoaprendizaje'; $('#subtitle').textContent = 'Walk-forward · errores · estabilidad'; $('#filters').innerHTML = '';
  const [x, d, e, b, cal, audit] = await Promise.all([api('/api/learning'), api('/api/data-status'), api('/api/error-learning'), api('/api/backtest?limit=200'), api('/api/calibration'), api('/api/system-audit')]);
  const perf = Object.entries(b.feature_directional_performance || {}).sort((a, z) => (z[1].correct_direction / Math.max(1, z[1].samples)) - (a[1].correct_direction / Math.max(1, a[1].samples))).slice(0, 12);
  out.innerHTML = `<div class="hero"><h2>Adaptive Learning Core · V64.6.0 · Motor V64.0.0</h2><p>${esc(x.policy)}</p><div class="detail"><b>Estado:</b> ${esc(audit.readiness)} · ${esc(audit.checks.probability_calibration_status)} · ${audit.data.verified_reviews} revisiones.</div></div><div class="stats"><div class="stat"><small>Backtest</small><b>${b.samples}</b></div><div class="stat"><small>Accuracy</small><b>${b.accuracy == null ? '—' : pct(b.accuracy)}</b></div><div class="stat"><small>Brier</small><b>${b.brier == null ? '—' : Number(b.brier).toFixed(3)}</b></div><div class="stat"><small>Log Loss</small><b>${b.log_loss == null ? '—' : Number(b.log_loss).toFixed(3)}</b></div><div class="stat"><small>Revisiones</small><b>${e.reviews}</b></div><div class="stat"><small>Histórico</small><b>${d.finished_matches}</b></div></div><div class="hero" style="margin-top:14px"><h3>Adaptive Calibration</h3><p>${esc(cal.policy)}</p></div><div class="grid" style="margin-top:14px"><article class="card"><h3>Rendimiento señales</h3>${perf.length ? perf.map(([k, v]) => `<div class="signal"><div><b>${esc(k)}</b><small>${v.samples} muestras</small></div><strong>${pct(v.correct_direction / Math.max(1, v.samples))}</strong>${bar(v.correct_direction / Math.max(1, v.samples))}</div>`).join('') : '<div class="detail">Sin muestra.</div>'}</article></div>`;
}
async function loadData() {
  view = 'data'; $('#title').textContent = 'Centro de datos'; $('#subtitle').textContent = 'Fuentes, histórico, cobertura'; $('#filters').innerHTML = '';
  const [x, d, cal, audit] = await Promise.all([api('/api/data-engine'), api('/api/data-status'), api('/api/calibration'), api('/api/system-audit')]);
  out.innerHTML = `<div class="hero"><h2>Historical Orchestrator</h2><p>Local-first → fuentes → normalización.</p><div class="detail"><b>Auditoría:</b> ${esc(audit.readiness)} · ${esc(audit.checks.probability_calibration_status)}</div></div><div class="stats"><div class="stat"><small>Terminados</small><b>${x.finished_matches}</b></div><div class="stat"><small>Competencias</small><b>${x.competitions.length}</b></div><div class="stat"><small>Fuentes</small><b>${x.sources.length}</b></div><div class="stat"><small>Snapshots</small><b>${d.feature_snapshots}</b></div></div><div class="grid" style="margin-top:14px">${x.sources.map(s => `<article class="card"><div class="meta"><span>${esc(s.source)}</span><span class="badge ${s.enabled ? 'high' : 'low'}">${s.enabled ? 'ACTIVA' : 'DESACTIVADA'}</span></div><div class="detail">Tipo: ${esc(s.kind)} · Prioridad: ${s.priority}<br>Fallos: ${s.failures || 0}</div></article>`).join('')}</div>`;
}
async function loadErrors() {
  view = 'errors'; $('#title').textContent = 'Inteligencia de errores'; $('#subtitle').textContent = 'Sesgos por liga, equipo, resultado'; $('#filters').innerHTML = '';
  const x = await api('/api/error-intelligence'); const g = x.global || {}; const fmt = v => v == null ? '—' : Number(v).toFixed(3); const pp = v => v == null ? '—' : (Number(v) * 100).toFixed(1) + ' pp';
  const rows = (x.worst_leagues || []).map(r => `<tr><td>${esc(r.entity)}</td><td>${r.samples}</td><td>${pct(r.accuracy)}</td><td>${fmt(r.brier)}</td><td>${pp(r.pick_local_rate - r.actual_local_rate)}</td><td>${pp(r.pick_away_rate - r.actual_away_rate)}</td></tr>`).join('');
  const teamRows = (x.worst_teams || []).map(r => `<tr><td>${esc(r.entity)}</td><td>${r.samples}</td><td>${pct(r.accuracy)}</td><td>${fmt(r.brier)}</td><td>${pp(r.pick_local_rate - r.actual_local_rate)}</td><td>${pp(r.pick_away_rate - r.actual_away_rate)}</td></tr>`).join('');
  const seg = (x.segments || []).map(r => `<div class="signal"><div><b>${esc(r.entity)}</b><small>${r.samples} muestras · ${esc((r.diagnosis || []).join(' · ') || 'sin sesgo')}</small></div><strong>${pct(r.accuracy)}</strong>${bar(r.accuracy)}</div>`).join('');
  const diag = (x.diagnoses || []).slice(0, 8).map(d => `<div class="reason"><b>${esc(d.diagnosis)}</b><span>${d.count} casos · ${(d.rate * 100).toFixed(1)}%</span></div>`).join('');
  out.innerHTML = `<div class="hero"><h2>Post-Match Error Intelligence</h2><p>${esc(x.policy)}</p><div class="stats"><div class="stat"><small>Revisados</small><b>${g.samples || 0}</b></div><div class="stat"><small>Accuracy</small><b>${g.accuracy == null ? '—' : pct(g.accuracy)}</b></div><div class="stat"><small>Brier</small><b>${fmt(g.brier)}</b></div><div class="stat"><small>Log Loss</small><b>${fmt(g.log_loss)}</b></div></div></div><div class="grid" style="margin-top:14px"><article class="card"><h3>Sesgo global</h3><div class="detail">Local pronosticado: ${pct(g.pick_local_rate)} · real: ${pct(g.actual_local_rate)}</div><div class="detail">Empate pronosticado: ${pct(g.pick_draw_rate)} · real: ${pct(g.actual_draw_rate)}</div><div class="detail">Visitante pronosticado: ${pct(g.pick_away_rate)} · real: ${pct(g.actual_away_rate)}</div></article><article class="card"><h3>Diagnósticos repetidos</h3>${diag || '<div class="detail">Sin muestra suficiente.</div>'}</article></div><div class="grid" style="margin-top:14px"><article class="card"><h3>Segmentos evidencia/confianza</h3>${seg || '<div class="detail">Se necesitan 5 observaciones por segmento.</div>'}</article></div><div class="hero" style="margin-top:14px"><h3>Competiciones peor rendimiento</h3>${rows ? `<table class="table"><thead><tr><th>Liga</th><th>N</th><th>Accuracy</th><th>Brier</th><th>Sesgo local</th><th>Sesgo visitante</th></tr></thead><tbody>${rows}</tbody></table>` : '<div class="detail">Ninguna liga con 5 revisiones.</div>'}</div><div class="hero" style="margin-top:14px"><h3>Equipos mayor error</h3>${teamRows ? `<table class="table"><thead><tr><th>Equipo</th><th>N</th><th>Accuracy</th><th>Brier</th><th>Sesgo local</th><th>Sesgo visitante</th></tr></thead><tbody>${teamRows}</tbody></table>` : '<div class="detail">Ningún equipo con 5 revisiones.</div>'}</div>`;
}
async function load() {
  let healthy = false;
  try {
    const h = await api('/api/health');
    healthy = true; $('#status').textContent = `API ${h.version} · ${h.records} registros`; $('.dot').style.background = '#32d583';
  } catch (e) { $('#status').textContent = 'API con error'; $('.dot').style.background = '#ff6b7a'; out.innerHTML = `<div class="empty">No se pudo conectar: ${esc(e.message)}</div>`; return; }
  try {
    if (view === 'day') await loadDay(); else if (view === 'top') await loadTop(); else if (view === 'combo') await loadCombo(); else if (view === 'progol') await loadProgol(); else if (view === 'intel') await loadIntel(); else if (view === 'learning') await loadLearning(); else if (view === 'errors') await loadErrors(); else await loadData();
  } catch (e) {
    out.innerHTML = `<div class="empty"><b>No se pudo cargar esta vista.</b><br>${esc(e.message)}<br><small>Prueba Actualizar o selecciona otra fecha.</small></div>`;
    if (healthy) { $('#status').textContent = 'API activa · error de vista'; $('.dot').style.background = '#f6c343'; }
  }
}
if (!$('#date').value) $('#date').value = mxToday();
document.querySelectorAll('.nav button').forEach(b => b.onclick = () => { document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active')); b.classList.add('active'); ({ day: loadDay, top: loadTop, combo: loadCombo, progol: loadProgol, intel: loadIntel, learning: loadLearning, data: loadData, errors: loadErrors })[b.dataset.view](); });
$('#refresh').onclick = async () => {
  // Refresh con fuerza real: pide al backend que re-sincronice todo
  const d = $('#date').value || mxToday();
  $('#status').textContent = `Forzando actualización completa ${d}...`;
  $('.dot').style.background = '#f6c343';
  out.innerHTML = '<div class="empty">🔄 Forzando sincronización completa (puede tardar 2-3 min)...</div>';
  try {
    const x = await api('/api/calendar?date=' + encodeURIComponent(d) + '&refresh=1');
    data = (x.matches || []).filter(m => m.date === d);
    filterBar(x.competitions || []); renderDay(x.competitions || []);
    $('#status').textContent = `API ${LIAN_VERSION} · ${data.length} partidos · actualizado`;
    $('.dot').style.background = '#32d583';
    localStorage.setItem(`lian_${d}`, JSON.stringify(x));
  } catch (e) {
    out.innerHTML = `<div class="empty">Error al forzar actualización: ${esc(e.message)}</div>`;
  }
};
$('#date').onchange = () => loadDay();
load();
