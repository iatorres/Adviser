// ── Estado global ─────────────────────────────────────────────────────────────
const DIAS       = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"];
const DIAS_LABEL = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];

let state = {
  rutina:      {},
  diaVista:    "lunes",
  diaEditar:   "lunes",
  diaActual:   "lunes",
  horaActual:  0,
  asistente:   false,
  tema:        "dark",
};

// ── Inicialización ────────────────────────────────────────────────────────────
window.addEventListener('pywebviewready', async () => {
  const api = window.pywebview.api;
  const [estado, rutina] = await Promise.all([
    api.get_estado_inicial(),
    api.get_rutina(),
  ]);

  state.rutina     = rutina;
  state.diaVista   = estado.dia_actual;
  state.diaEditar  = estado.dia_actual;
  state.diaActual  = estado.dia_actual;
  state.horaActual = estado.hora_actual;
  state.asistente  = estado.asistente;
  if (estado.tema) state.tema = estado.tema;

  document.getElementById('fecha-str').textContent = estado.fecha_str;

  aplicarTema(state.tema);
  buildDaySelector();
  buildHoursList();
  buildEditList();
  updateAsistenteUI();
  startClock();

  setTimeout(() => {
    const l = document.getElementById('loading');
    l.classList.add('hidden');
    setTimeout(() => l.remove(), 300);
  }, 200);
});

window.addEventListener('DOMContentLoaded', () => {
  if (!window.pywebview) {
    const t = localStorage.getItem('adviser_tema') || 'dark';
    state.tema = t;
    aplicarTema(t);
    setTimeout(() => document.getElementById('loading')?.remove(), 500);
  }
});

// ── Tema ──────────────────────────────────────────────────────────────────────
function aplicarTema(tema) {
  state.tema = tema;
  if (tema === 'light') document.documentElement.setAttribute('data-theme', 'light');
  else                  document.documentElement.removeAttribute('data-theme');
  const toggle = document.getElementById('tema-toggle');
  const badge  = document.getElementById('tema-badge');
  if (toggle) toggle.checked = (tema === 'dark');
  if (badge)  badge.textContent = (tema === 'dark') ? 'Oscuro' : 'Claro';
}

function onTemaChange(isDark) {
  const nuevoTema = isDark ? 'dark' : 'light';
  aplicarTema(nuevoTema);
  if (window.pywebview) window.pywebview.api.guardar_tema(nuevoTema);
  else localStorage.setItem('adviser_tema', nuevoTema);
}

// ── Reloj ─────────────────────────────────────────────────────────────────────
function startClock() {
  function tick() {
    const now = new Date();
    document.getElementById('status-time').textContent =
      `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    const nuevaHora = now.getHours();
    const nuevoDia  = DIAS[now.getDay() === 0 ? 6 : now.getDay() - 1];
    if (nuevaHora !== state.horaActual || nuevoDia !== state.diaActual) {
      state.horaActual = nuevaHora;
      state.diaActual  = nuevoDia;
      refreshHoraActual();
    }
  }
  tick();
  setInterval(tick, 1000);
}

// ── Rutina (vista) ────────────────────────────────────────────────────────────
function buildHoursList() {
  const container = document.getElementById('hours-list');
  container.innerHTML = '';
  for (let h = 0; h < 24; h++) {
    const card = document.createElement('div');
    card.className = 'hour-card';
    card.id = `hc-${h}`;
    card.innerHTML = `
      <span class="card-time">${String(h).padStart(2,'0')}:00</span>
      <div class="card-divider"></div>
      <div class="card-content">
        <div class="card-title" id="hc-title-${h}"></div>
        <div class="card-msg"   id="hc-msg-${h}"></div>
      </div>
      <span class="card-badge">● AHORA</span>
    `;
    container.appendChild(card);
  }
  renderDia(state.diaVista);
}

function renderDia(dia) {
  const lista = state.rutina[dia] || [];
  for (let h = 0; h < 24; h++) {
    document.getElementById(`hc-title-${h}`).textContent = lista[h] ? lista[h][0] : '(Vacío)';
    document.getElementById(`hc-msg-${h}`).textContent   = lista[h] ? lista[h][1] : 'Sin actividad asignada';
    document.getElementById(`hc-${h}`).classList.toggle('now', dia === state.diaActual && h === state.horaActual);
  }
}

function refreshHoraActual() {
  for (let h = 0; h < 24; h++) {
    const card = document.getElementById(`hc-${h}`);
    if (card) card.classList.toggle('now', state.diaVista === state.diaActual && h === state.horaActual);
  }
}

function buildDaySelector() {
  const container = document.getElementById('day-selector');
  container.innerHTML = '';
  DIAS.forEach((dia, i) => {
    const btn = document.createElement('button');
    btn.className = 'day-btn' + (dia === state.diaVista ? ' active' : '');
    btn.textContent = DIAS_LABEL[i];
    btn.onclick = () => selectDia(dia);
    container.appendChild(btn);
  });
}

function selectDia(dia) {
  state.diaVista = dia;
  document.querySelectorAll('.day-btn').forEach((btn, i) => btn.classList.toggle('active', DIAS[i] === dia));
  renderDia(dia);
}

// ── Edición ───────────────────────────────────────────────────────────────────
function buildEditList() {
  const container = document.getElementById('edit-list');
  container.innerHTML = '';
  for (let h = 0; h < 24; h++) {
    const card = document.createElement('div');
    card.className = 'edit-card';
    card.innerHTML = `
      <span class="edit-time">${String(h).padStart(2,'0')}:00</span>
      <div class="edit-divider"></div>
      <div class="edit-fields">
        <input class="edit-input title-input" id="et-${h}" type="text" placeholder="Título...">
        <input class="edit-input msg-input"   id="em-${h}" type="text" placeholder="Mensaje...">
      </div>
    `;
    container.appendChild(card);
  }
  cargarEditDia(state.diaEditar);
}

function cargarEditDia(dia) {
  const lista = state.rutina[dia] || [];
  for (let h = 0; h < 24; h++) {
    document.getElementById(`et-${h}`).value = lista[h] ? lista[h][0] : '';
    document.getElementById(`em-${h}`).value = lista[h] ? lista[h][1] : '';
  }
}

function onEditDiaChange(val) {
  state.diaEditar = val;
  cargarEditDia(val);
}

async function guardarDia() {
  const entradas = [];
  for (let h = 0; h < 24; h++) {
    entradas.push([
      document.getElementById(`et-${h}`).value.trim() || '(Vacío)',
      document.getElementById(`em-${h}`).value.trim() || 'Sin actividad asignada',
    ]);
  }
  state.rutina[state.diaEditar] = entradas;
  if (window.pywebview) await window.pywebview.api.guardar_dia(state.diaEditar, entradas);
  if (state.diaEditar === state.diaVista) renderDia(state.diaVista);
  showToast(`Rutina del ${capitalize(state.diaEditar)} guardada ✓`);
}

// ── Asistente ─────────────────────────────────────────────────────────────────
async function toggleAsistente() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.toggle_asistente();
  state.asistente = res.estado;
  updateAsistenteUI();
}

function updateAsistenteUI() {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  const btn  = document.getElementById('btn-toggle');
  if (state.asistente) {
    dot.classList.add('active'); text.textContent = 'Activo'; text.classList.add('active');
    btn.textContent = '■ Detener asistente'; btn.classList.add('running');
  } else {
    dot.classList.remove('active'); text.textContent = 'Detenido'; text.classList.remove('active');
    btn.textContent = '▶ Iniciar asistente'; btn.classList.remove('running');
  }
}

window._onAsistenteHora = (hora) => { state.horaActual = hora; refreshHoraActual(); };

// ── Navegación ────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-btn[data-panel]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.panel;
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${target}`).classList.add('active');
  });
});


// ═════════════════════════════════════════════════════════════════════════════
//  CRONÓMETRO DE TAREAS
// ═════════════════════════════════════════════════════════════════════════════

const crono = {
  tiempoMin:     15,
  tareas:        [],
  timerID:       null,
  segsRestantes: 0,
  segsTotal:     0,
  iniciado:      false,
};

// ── Selector de tiempo ────────────────────────────────────────────────────────
document.querySelectorAll('.crono-time-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.crono-time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    crono.tiempoMin = parseInt(btn.dataset.min);
    document.getElementById('crono-custom-min').value = '';
    actualizarLabelTiempo();
  });
});

function setTiempoCustom() {
  const val = parseInt(document.getElementById('crono-custom-min').value);
  if (!val || val < 1) return;
  crono.tiempoMin = val;
  document.querySelectorAll('.crono-time-btn').forEach(b => b.classList.remove('active'));
  actualizarLabelTiempo();
}

function actualizarLabelTiempo() {
  const min = crono.tiempoMin;
  const h = Math.floor(min / 60), m = min % 60;
  document.getElementById('crono-tiempo-label').textContent =
    min < 60 ? `${min} minuto${min !== 1 ? 's' : ''}` :
    m ? `${h}h ${m}min` : `${h} hora${h !== 1 ? 's' : ''}`;
}

// ── Tareas en setup ───────────────────────────────────────────────────────────
function agregarTareaSetup() {
  const input = document.getElementById('crono-nueva-tarea');
  const texto = input.value.trim();
  if (!texto) return;
  crono.tareas.push({ texto, done: false });
  input.value = '';
  renderSetupLista();
  input.focus();
}

function eliminarTareaSetup(idx) {
  crono.tareas.splice(idx, 1);
  renderSetupLista();
}

function renderSetupLista() {
  const lista = document.getElementById('crono-setup-lista');
  if (crono.tareas.length === 0) {
    lista.innerHTML = '<div class="crono-empty-hint">Aún no hay tareas. Agregá al menos una para comenzar.</div>';
    document.getElementById('btn-crono-start').disabled = true;
    return;
  }
  lista.innerHTML = crono.tareas.map((t, i) => `
    <div class="crono-setup-item">
      <span class="crono-setup-item-num">${i + 1}.</span>
      <span class="crono-setup-item-text">${escapeHtml(t.texto)}</span>
      <button class="crono-setup-item-del" onclick="eliminarTareaSetup(${i})">✕</button>
    </div>
  `).join('');
  document.getElementById('btn-crono-start').disabled = false;
}

// ── Iniciar sesión ────────────────────────────────────────────────────────────
async function iniciarCronometro() {
  if (crono.tareas.length === 0) return;

  crono.segsTotal     = crono.tiempoMin * 60;
  crono.segsRestantes = crono.segsTotal;
  crono.iniciado      = true;

  if (window.pywebview) {
    await window.pywebview.api.crono_iniciar(JSON.stringify(crono.tareas), crono.segsTotal);
  } else {
    crono.timerID = setInterval(_tickJS, 1000);
  }

  document.getElementById('crono-setup').style.display   = 'none';
  document.getElementById('crono-running').style.display = 'flex';
  document.getElementById('crono-resumen').style.display = 'none';
  document.getElementById('crono-total-count').textContent = crono.tareas.length;
  renderRunningLista();
  actualizarDisplay();
}

// ── Callbacks desde Python ────────────────────────────────────────────────────

// Tick cada segundo (Python lleva el tiempo real)
window._cronoPythonTick = function(segsRestantes) {
  crono.segsRestantes = segsRestantes;
  actualizarDisplay();
};

// Tiempo agotado
window._cronoTiempoAgotado = function() {
  crono.segsRestantes = 0;
  if (crono.timerID) { clearInterval(crono.timerID); crono.timerID = null; }
  actualizarDisplay();
  const hechas = crono.tareas.filter(t => t.done).length;
  const total  = crono.tareas.length;
  if (hechas < total) document.getElementById('alarm-overlay').style.display = 'flex';
  mostrarResumen({
    icono:  '⏰',
    titulo: 'Tiempo agotado',
    sub:    `Completaste ${hechas} de ${total} tareas antes de que se acabara el tiempo.`,
    chips: [
      { label: `${hechas}/${total} completadas`, clase: hechas === total ? 'green' : 'orange' },
      { label: `${crono.tiempoMin}min límite`,   clase: 'accent' },
    ],
  });
};

// Fallback tick JS (browser sin pywebview)
function _tickJS() {
  crono.segsRestantes--;
  if (crono.segsRestantes <= 0) {
    crono.segsRestantes = 0;
    clearInterval(crono.timerID);
    crono.timerID = null;
    window._cronoTiempoAgotado();
    return;
  }
  actualizarDisplay();
}

// ── Display running ───────────────────────────────────────────────────────────
function actualizarDisplay() {
  const segs = crono.segsRestantes;
  const mm   = String(Math.floor(segs / 60)).padStart(2, '0');
  const ss   = String(segs % 60).padStart(2, '0');
  document.getElementById('crono-time-display').textContent = `${mm}:${ss}`;

  const CIRC   = 326.7;
  const prog   = crono.segsTotal > 0 ? segs / crono.segsTotal : 0;
  const ring   = document.getElementById('crono-ring-fill');
  ring.style.strokeDashoffset = CIRC * (1 - prog);
  ring.classList.remove('warning', 'danger');
  if (prog <= 0.15)      ring.classList.add('danger');
  else if (prog <= 0.35) ring.classList.add('warning');

  const hechas = crono.tareas.filter(t => t.done).length;
  const total  = crono.tareas.length;
  document.getElementById('crono-progress-bar').style.width = (total ? hechas / total * 100 : 0) + '%';
  document.getElementById('btn-crono-finish').disabled = (hechas < total);
}

function renderRunningLista() {
  const lista  = document.getElementById('crono-running-lista');
  const hechas = crono.tareas.filter(t => t.done).length;
  document.getElementById('crono-done-count').textContent = hechas;
  lista.innerHTML = crono.tareas.map((t, i) => `
    <div class="crono-run-item ${t.done ? 'done' : ''}" onclick="toggleTarea(${i})">
      <div class="crono-run-item-check">${t.done ? '✓' : ''}</div>
      <span class="crono-run-item-text">${escapeHtml(t.texto)}</span>
    </div>
  `).join('');
}

async function toggleTarea(idx) {
  crono.tareas[idx].done = !crono.tareas[idx].done;
  renderRunningLista();
  actualizarDisplay();
  if (window.pywebview) {
    await window.pywebview.api.crono_toggle_tarea(idx, crono.tareas[idx].done);
  }
}

function agregarTareaRunning() {
  const input = document.getElementById('crono-nueva-tarea-running');
  const texto = input.value.trim();
  if (!texto) return;
  crono.tareas.push({ texto, done: false });
  input.value = '';
  document.getElementById('crono-total-count').textContent = crono.tareas.length;
  renderRunningLista();
  actualizarDisplay();
  if (window.pywebview) {
    window.pywebview.api.crono_toggle_tarea(crono.tareas.length - 1, false);
  }
  input.focus();
}

// ── Finalizar / Cancelar ──────────────────────────────────────────────────────
async function finalizarSesion() {
  if (window.pywebview) await window.pywebview.api.crono_finalizar();
  else if (crono.timerID) { clearInterval(crono.timerID); crono.timerID = null; }
  _mostrarResumenFinal();
}

function _mostrarResumenFinal() {
  const total     = crono.tareas.length;
  const hechas    = crono.tareas.filter(t => t.done).length;
  const segsUsados = crono.segsTotal - crono.segsRestantes;
  const min = Math.floor(segsUsados / 60), seg = segsUsados % 60;
  const tiempoStr = min > 0 ? `${min}min ${String(seg).padStart(2,'0')}s` : `${seg}s`;
  mostrarResumen({
    icono:  '✓',
    titulo: '¡Sesión completada!',
    sub:    hechas === total ? 'Completaste todas las tareas en tiempo.' : `Completaste ${hechas} de ${total} tareas.`,
    chips: [
      { label: `${hechas}/${total} tareas`, clase: 'green'  },
      { label: `en ${tiempoStr}`,           clase: 'accent' },
    ],
  });
}

async function cancelarSesion() {
  if (!confirm('¿Cancelar la sesión actual? Se perderán las tareas.')) return;
  if (window.pywebview) await window.pywebview.api.crono_cancelar();
  else if (crono.timerID) { clearInterval(crono.timerID); crono.timerID = null; }
  resetCrono();
}

function cerrarAlarma() {
  document.getElementById('alarm-overlay').style.display = 'none';
}

// ── Resumen ───────────────────────────────────────────────────────────────────
function mostrarResumen({ icono, titulo, sub, chips }) {
  document.getElementById('crono-setup').style.display   = 'none';
  document.getElementById('crono-running').style.display = 'none';
  document.getElementById('crono-resumen').style.display = 'flex';
  document.getElementById('crono-resumen-icon').textContent  = icono;
  document.getElementById('crono-resumen-titulo').textContent = titulo;
  document.getElementById('crono-resumen-sub').textContent    = sub;
  document.getElementById('crono-resumen-stats').innerHTML = chips.map(c =>
    `<div class="crono-stat-chip ${c.clase}">${c.label}</div>`
  ).join('');
}

function nuevaSesion() { resetCrono(); }

function resetCrono() {
  crono.tareas = []; crono.tiempoMin = 15;
  crono.segsRestantes = 0; crono.segsTotal = 0; crono.iniciado = false;
  if (crono.timerID) { clearInterval(crono.timerID); crono.timerID = null; }

  document.getElementById('crono-setup').style.display   = 'block';
  document.getElementById('crono-running').style.display = 'none';
  document.getElementById('crono-resumen').style.display = 'none';
  document.getElementById('crono-nueva-tarea').value = '';
  document.getElementById('crono-custom-min').value  = '';
  document.getElementById('crono-tiempo-label').textContent = '15 minutos';
  document.querySelectorAll('.crono-time-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
  renderSetupLista();
  const ring = document.getElementById('crono-ring-fill');
  if (ring) { ring.style.strokeDashoffset = '0'; ring.classList.remove('warning','danger'); }
}

// ── Utilidades ────────────────────────────────────────────────────────────────
function capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }

function escapeHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let toastTimer = null;
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}
