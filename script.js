// ── Estado global ─────────────────────────────────────────────────────────────
const DIAS  = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"];
const DIAS_LABEL = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];

let state = {
  rutina:       {},
  diaVista:     "lunes",
  diaEditar:    "lunes",
  diaActual:    "lunes",
  horaActual:   0,
  asistente:    false,
};

// ── Inicialización ────────────────────────────────────────────────────────────
window.addEventListener('pywebviewready', async () => {
  const api = window.pywebview.api;

  // Obtener estado inicial y rutina en paralelo
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

  document.getElementById('fecha-str').textContent = estado.fecha_str;

  // Construir UI
  buildDaySelector();
  buildHoursList();
  buildEditList();
  updateAsistenteUI();
  startClock();

  // Ocultar loading
  setTimeout(() => {
    const l = document.getElementById('loading');
    l.classList.add('hidden');
    setTimeout(() => l.remove(), 300);
  }, 200);
});

// Fallback si pywebview no está disponible (debug en browser)
window.addEventListener('DOMContentLoaded', () => {
  if (!window.pywebview) {
    setTimeout(() => {
      document.getElementById('loading')?.remove();
    }, 500);
  }
});

// ── Reloj en tiempo real ──────────────────────────────────────────────────────
function startClock() {
  function tick() {
    const now = new Date();
    const hh  = String(now.getHours()).padStart(2,'0');
    const mm  = String(now.getMinutes()).padStart(2,'0');
    document.getElementById('status-time').textContent = `${hh}:${mm}`;

    // Actualizar hora actual y resaltado "AHORA"
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

// ── Construcción de la lista de horas (vista) ─────────────────────────────────
// Se hace UNA sola vez — después solo se actualizan textos y clases.
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

  // Cargar datos del día actual
  renderDia(state.diaVista);
}

function renderDia(dia) {
  const lista = state.rutina[dia] || [];
  for (let h = 0; h < 24; h++) {
    const titulo = lista[h] ? lista[h][0] : '(Vacío)';
    const msg    = lista[h] ? lista[h][1] : 'Sin actividad asignada';
    document.getElementById(`hc-title-${h}`).textContent = titulo;
    document.getElementById(`hc-msg-${h}`).textContent   = msg;

    const card = document.getElementById(`hc-${h}`);
    const esAhora = (dia === state.diaActual && h === state.horaActual);
    card.classList.toggle('now', esAhora);
  }
}

function refreshHoraActual() {
  // Solo actualiza clases, sin re-render completo
  for (let h = 0; h < 24; h++) {
    const card    = document.getElementById(`hc-${h}`);
    if (!card) continue;
    const esAhora = (state.diaVista === state.diaActual && h === state.horaActual);
    card.classList.toggle('now', esAhora);
  }
}

// ── Selector de días (vista) ──────────────────────────────────────────────────
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
  document.querySelectorAll('.day-btn').forEach((btn, i) => {
    btn.classList.toggle('active', DIAS[i] === dia);
  });
  renderDia(dia);
}

// ── Panel edición ─────────────────────────────────────────────────────────────
// También construido una vez, luego solo se actualizan valores.
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

  if (window.pywebview) {
    await window.pywebview.api.guardar_dia(state.diaEditar, entradas);
  }

  // Si estamos viendo el mismo día, actualizar vista
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
  const dot    = document.getElementById('status-dot');
  const text   = document.getElementById('status-text');
  const btn    = document.getElementById('btn-toggle');

  if (state.asistente) {
    dot.classList.add('active');
    text.textContent = 'Activo';
    text.classList.add('active');
    btn.textContent = '■ Detener asistente';
    btn.classList.add('running');
  } else {
    dot.classList.remove('active');
    text.textContent = 'Detenido';
    text.classList.remove('active');
    btn.textContent = '▶ Iniciar asistente';
    btn.classList.remove('running');
  }
}

// Callback llamado desde Python cuando salta una notificación de hora
window._onAsistenteHora = (hora) => {
  state.horaActual = hora;
  refreshHoraActual();
};

// ── Navegación entre paneles ──────────────────────────────────────────────────
document.querySelectorAll('.nav-btn[data-panel]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.panel;

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${target}`).classList.add('active');
  });
});

// ── Configuración / Tema ──────────────────────────────────────────────────────
function onTemaChange(isDark) {
  const badge = document.getElementById('tema-badge');
  badge.textContent = isDark ? 'Oscuro' : 'Claro';
  // Por ahora solo guardamos la preferencia — cambiar variables CSS en runtime
  // requeriría un segundo set de variables; se puede extender fácilmente.
  if (window.pywebview) {
    window.pywebview.api.guardar_tema(isDark ? 'dark' : 'light');
  }
}

// ── Utilidades ────────────────────────────────────────────────────────────────
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

let toastTimer = null;
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}