// ============================================================
//  cocina.js — Monitor de Producción
//  Kanban con WebSockets + cronómetros por comanda
// ============================================================

/* ------------------------------------------------------------
   ESTADO GLOBAL
   ------------------------------------------------------------ */
const COCINA = {
    comandas: [],           // lista completa
    filtro: 'activos',      // activos | todas | urgentes
    ordenar: 'hora',        // hora | mesa
    socket: null,
    timers: {},             // { comandaId: intervalId }
};

const UMBRALES_MIN = {
    media:   8,             // 8 min → ámbar
    alta:   12,             // 12 min → rojo
    critica: 18,            // 18 min → parpadea
};

/* ------------------------------------------------------------
   INICIALIZACIÓN
   ------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    initFiltros();
    initOrden();
    initModalComanda();
    cargarComandas();
    // Refresca contadores de tiempo cada 15 s (por si acaso)
    setInterval(actualizarCronometros, 15000);
    // Reconexión de respaldo por si el socket muere
    setInterval(() => {
        if (!COCINA.socket?.connected) cargarComandas();
    }, 30000);
});

/* ------------------------------------------------------------
   WEBSOCKET (Flask-SocketIO)
   ------------------------------------------------------------ */
function initSocket() {
    const elEstado = document.getElementById('estadoConexion');

    COCINA.socket = io('http://localhost:5000', {
        transports: ['websocket'],
        withCredentials: true,
    });

    COCINA.socket.on('connect', () => {
        console.log('🔌 Socket conectado');
        elEstado.classList.add('conectado');
        elEstado.innerHTML = '<span class="dot"></span> En vivo';
        COCINA.socket.emit('unirse_cocina');
    });

    COCINA.socket.on('disconnect', () => {
        console.warn('⚠️ Socket desconectado');
        elEstado.classList.remove('conectado');
        elEstado.innerHTML = '<span class="dot"></span> Reconectando...';
    });

    // Nueva comanda entrante
    COCINA.socket.on('nueva_comanda', (comanda) => {
        console.log('🆕 Nueva comanda:', comanda);
        COCINA.comandas.push(comanda);
        renderKanban();
        mostrarAlertaNuevaComanda(comanda);
        reproducirSonido();
    });

    // Comanda actualizada (estado modificado)
    COCINA.socket.on('comanda_actualizada', (comanda) => {
        const idx = COCINA.comandas.findIndex(c => c.id === comanda.id);
        if (idx !== -1) COCINA.comandas[idx] = comanda;
        else COCINA.comandas.push(comanda);
        renderKanban();
    });

    // Comanda eliminada
    COCINA.socket.on('comanda_eliminada', ({ id }) => {
        COCINA.comandas = COCINA.comandas.filter(c => c.id !== id);
        renderKanban();
    });
}

/* ------------------------------------------------------------
   CARGA INICIAL REST
   ------------------------------------------------------------ */
async function cargarComandas() {
    try {
        const data = await API.get('/cocina/comandas');
        COCINA.comandas = data;
    } catch (e) {
        COCINA.comandas = getComandasDemo();
    }
    renderKanban();
}

/* ------------------------------------------------------------
   FILTROS Y ORDEN
   ------------------------------------------------------------ */
function initFiltros() {
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filtro-btn')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            COCINA.filtro = btn.dataset.filtro;
            renderKanban();
        });
    });
}

function initOrden() {
    const sel = document.getElementById('ordenarPor');
    sel?.addEventListener('change', () => {
        COCINA.ordenar = sel.value;
        renderKanban();
    });
}

/* ------------------------------------------------------------
   RENDER PRINCIPAL
   ------------------------------------------------------------ */
function renderKanban() {
    const visibles = filtrarYOrdenar(COCINA.comandas);

    const grupos = {
        pendiente:      visibles.filter(c => c.estado === 'pendiente'),
        en_preparacion: visibles.filter(c => c.estado === 'en_preparacion'),
        listo:          visibles.filter(c => c.estado === 'listo'),
    };

    renderColumna('colPendientes', grupos.pendiente);
    renderColumna('colPreparando', grupos.en_preparacion);
    renderColumna('colListos',     grupos.listo);

    document.getElementById('badgePendientes').textContent = grupos.pendiente.length;
    document.getElementById('badgePreparando').textContent = grupos.en_preparacion.length;
    document.getElementById('badgeListos').textContent     = grupos.listo.length;

    actualizarStats();
    actualizarCronometros();
}

function filtrarYOrdenar(lista) {
    let resultado = [...lista];

    // Filtro
    if (COCINA.filtro === 'activos') {
        resultado = resultado.filter(c => c.estado !== 'servido');
    } else if (COCINA.filtro === 'urgentes') {
        resultado = resultado.filter(c => {
            const min = minutosDesde(c.hora_pedido);
            return min >= UMBRALES_MIN.alta && c.estado !== 'servido';
        });
    }
    // 'todas' → sin filtro adicional

    // Orden
    resultado.sort((a, b) => {
        if (COCINA.ordenar === 'mesa') {
            return (a.mesa_numero || 0) - (b.mesa_numero || 0);
        }
        return new Date(a.hora_pedido) - new Date(b.hora_pedido);
    });

    return resultado;
}

function renderColumna(containerId, comandas) {
    const cont = document.getElementById(containerId);

    if (!comandas.length) {
        cont.innerHTML = '<p class="col-vacia">Sin comandas aquí</p>';
        return;
    }

    cont.innerHTML = comandas.map(c => renderComandaCard(c)).join('');

    // Listeners
    cont.querySelectorAll('[data-accion]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id     = Number(btn.dataset.id);
            const accion = btn.dataset.accion;
            ejecutarAccion(id, accion);
        });
    });

    // Click en la tarjeta → abre modal detalle
    cont.querySelectorAll('.comanda-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = Number(card.dataset.id);
            abrirModalComanda(id);
        });
    });
}

function renderComandaCard(c) {
    const min      = minutosDesde(c.hora_pedido);
    const urgencia = calcularUrgencia(min);
    const hora     = formatearHora(c.hora_pedido);

    const itemsHTML = (c.items || []).map(it => `
        <li>
            <span class="item-cant">${it.cantidad}×</span>
            <span class="item-nombre">
                ${it.nombre}
                ${it.notas
                    ? `<span class="item-notas">📝 ${it.notas}</span>`
                    : ''}
            </span>
        </li>
    `).join('');

    const acciones = renderAcciones(c);

    return `
        <article class="comanda-card ${urgencia === 'alta' || urgencia === 'critica' ? 'urgente' : ''}"
                 data-id="${c.id}"
                 data-urgencia="${urgencia}">
            <div class="comanda-header">
                <span class="comanda-mesa">Mesa #${c.mesa_numero}</span>
                <span class="comanda-timer" data-timer="${c.id}">
                    ⏱️ ${min} min
                </span>
            </div>
            <div class="comanda-info">
                <span>👤 ${c.mesero || 'Mesero'}</span>
                <span>🕐 ${hora}</span>
                <span>🧾 #${c.id}</span>
            </div>
            <ul class="comanda-items">${itemsHTML}</ul>
            <div class="comanda-acciones">${acciones}</div>
        </article>
    `;
}

function renderAcciones(c) {
    switch (c.estado) {
        case 'pendiente':
            return `
                <button class="btn-iniciar" data-id="${c.id}"
                        data-accion="iniciar">
                    🔥 Empezar
                </button>
            `;
        case 'en_preparacion':
            return `
                <button class="btn-terminar" data-id="${c.id}"
                        data-accion="terminar">
                    ✅ Terminar
                </button>
            `;
        case 'listo':
            return `
                <button class="btn-servir" data-id="${c.id}"
                        data-accion="servir">
                    🛎️ Servir
                </button>
            `;
        default:
            return '';
    }
}

/* ------------------------------------------------------------
   ACCIONES SOBRE COMANDAS
   ------------------------------------------------------------ */
async function ejecutarAccion(id, accion) {
    const comanda = COCINA.comandas.find(c => c.id === id);
    if (!comanda) return;

    const transiciones = {
        iniciar:  { estado: 'en_preparacion', msg: '🔥 Comanda en preparación' },
        terminar: { estado: 'listo',           msg: '✅ Comanda lista' },
        servir:   { estado: 'servido',         msg: '🛎️ Comanda servida' },
    };

    const t = transiciones[accion];
    if (!t) return;

    // Optimistic UI
    comanda.estado = t.estado;
    renderKanban();
    Utils.mostrarToast(t.msg, 'success');

    // Enviar al backend
    try {
        await API.post(`/cocina/comandas/${id}/estado`, { estado: t.estado });
    } catch (e) {
        console.warn('No se pudo actualizar en servidor:', e);
    }
}

/* ------------------------------------------------------------
   CRONÓMETROS
   ------------------------------------------------------------ */
function actualizarCronometros() {
    document.querySelectorAll('[data-timer]').forEach(el => {
        const id = Number(el.dataset.timer);
        const c  = COCINA.comandas.find(x => x.id === id);
        if (!c) return;

        const min = minutosDesde(c.hora_pedido);
        el.textContent = `⏱️ ${min} min`;

        const card = el.closest('.comanda-card');
        if (!card) return;

        const urgencia = calcularUrgencia(min);
        card.dataset.urgencia = urgencia;
        card.classList.toggle(
            'urgente',
            urgencia === 'alta' || urgencia === 'critica'
        );
    });
}

function minutosDesde(fechaISO) {
    if (!fechaISO) return 0;
    let f = fechaISO;
    if (!f.endsWith('Z') && !f.includes('+')) {
        f += 'Z'; // Forzar UTC
    }
    const ahora = new Date().getTime();
    const inicio = new Date(f).getTime();
    const min = Math.floor((ahora - inicio) / 60000);
    return min < 0 ? 0 : min; // Nunca negativo
}

function calcularUrgencia(min) {
    if (min >= UMBRALES_MIN.critica) return 'critica';
    if (min >= UMBRALES_MIN.alta)    return 'alta';
    if (min >= UMBRALES_MIN.media)   return 'media';
    return 'baja';
}

function formatearHora(iso) {
    return new Date(iso).toLocaleTimeString('es-CO', {
        hour: '2-digit',
        minute: '2-digit',
    });
}

/* ------------------------------------------------------------
   ESTADÍSTICAS
   ------------------------------------------------------------ */
function actualizarStats() {
    const activas = COCINA.comandas.filter(c => c.estado !== 'servido');

    const pendientes     = activas.filter(c => c.estado === 'pendiente').length;
    const enPreparacion  = activas.filter(c => c.estado === 'en_preparacion').length;
    const listos         = activas.filter(c => c.estado === 'listo').length;

    document.getElementById('statPendientes').textContent  = pendientes;
    document.getElementById('statPreparando').textContent  = enPreparacion;
    document.getElementById('statListos').textContent      = listos;

    // Promedio de tiempo de preparación (para las ya servidas hoy)
    const servidas = COCINA.comandas.filter(c => c.estado === 'servido');
    if (servidas.length) {
        const suma = servidas.reduce((s, c) =>
            s + minutosDesde(c.hora_pedido), 0
        );
        document.getElementById('statPromedio').textContent =
            `${Math.round(suma / servidas.length)} min`;
    } else {
        document.getElementById('statPromedio').textContent = '— min';
    }
}

/* ------------------------------------------------------------
   MODAL DETALLE
   ------------------------------------------------------------ */
function initModalComanda() {
    const modal = document.getElementById('modalComanda');
    document.getElementById('cerrarModalComanda')
        .addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('open');
    });
}

function abrirModalComanda(id) {
    const c = COCINA.comandas.find(x => x.id === id);
    if (!c) return;

    const modal = document.getElementById('modalComanda');
    document.getElementById('modalComandaTitulo').textContent =
        `Comanda #${c.id} · Mesa ${c.mesa_numero}`;

    const min = minutosDesde(c.hora_pedido);

    document.getElementById('modalComandaBody').innerHTML = `
        <div class="detalle-item">
            <span>👤 Mesero</span>
            <span>${c.mesero || '—'}</span>
        </div>
        <div class="detalle-item">
            <span>🕐 Hora del pedido</span>
            <span>${formatearHora(c.hora_pedido)}</span>
        </div>
        <div class="detalle-item">
            <span>⏱️ Transcurrido</span>
            <span>${min} min</span>
        </div>
        <div class="detalle-item">
            <span>📌 Estado</span>
            <span>${c.estado}</span>
        </div>
        <hr style="margin:1rem 0;border:none;border-top:1px solid #374151">
        <ul class="comanda-items">
            ${c.items.map(it => `
                <li>
                    <span class="item-cant">${it.cantidad}×</span>
                    <span class="item-nombre">
                        ${it.nombre}
                        ${it.notas
                            ? `<span class="item-notas">📝 ${it.notas}</span>`
                            : ''}
                    </span>
                </li>
            `).join('')}
        </ul>
    `;

    // Footer con la acción correspondiente
    const footer = document.getElementById('modalComandaFooter');
    const accionesHTML = renderAcciones(c);
    footer.innerHTML = `
        <button class="btn btn-secondary"
                onclick="document.getElementById('modalComanda').classList.remove('open')">
            Cerrar
        </button>
        ${accionesHTML}
    `;

    // Reasignar listeners de los botones del footer
    footer.querySelectorAll('[data-accion]').forEach(btn => {
        btn.addEventListener('click', () => {
            ejecutarAccion(Number(btn.dataset.id), btn.dataset.accion);
            modal.classList.remove('open');
        });
    });

    modal.classList.add('open');
}

/* ------------------------------------------------------------
   ALERTAS
   ------------------------------------------------------------ */
function mostrarAlertaNuevaComanda(comanda) {
    const alerta = document.getElementById('alertaNuevaComanda');
    alerta.textContent = `🔔 Nueva comanda · Mesa #${comanda.mesa_numero}`;
    alerta.classList.add('visible');
    setTimeout(() => alerta.classList.remove('visible'), 4000);
}

function reproducirSonido() {
    try {
        const ctx  = new (window.AudioContext || window.webkitAudioContext)();
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + .35);
        osc.start();
        osc.stop(ctx.currentTime + .35);
    } catch (e) {
        // Silencioso
    }
}

/* ------------------------------------------------------------
   DATOS DEMO
   ------------------------------------------------------------ */
function getComandasDemo() {
    const ahora = Date.now();
    return [
        {
            id: 101, mesa_numero: 3, mesero: 'Ana', estado: 'pendiente',
            hora_pedido: new Date(ahora - 3 * 60000).toISOString(),
            items: [
                { cantidad: 1, nombre: 'Lomo al trapo',      notas: 'Término medio' },
                { cantidad: 2, nombre: 'Limonada de coco',   notas: '' },
            ],
        },
        {
            id: 102, mesa_numero: 5, mesero: 'Luis', estado: 'pendiente',
            hora_pedido: new Date(ahora - 10 * 60000).toISOString(),
            items: [
                { cantidad: 2, nombre: 'Ceviche mixto',      notas: 'Sin ají' },
                { cantidad: 1, nombre: 'Pasta carbonara',    notas: '' },
            ],
        },
        {
            id: 103, mesa_numero: 7, mesero: 'Carla', estado: 'en_preparacion',
            hora_pedido: new Date(ahora - 14 * 60000).toISOString(),
            items: [
                { cantidad: 1, nombre: 'Salmón grillé',      notas: 'Poco cocido' },
                { cantidad: 3, nombre: 'Cerveza artesanal',  notas: '' },
            ],
        },
        {
            id: 104, mesa_numero: 2, mesero: 'Ana', estado: 'en_preparacion',
            hora_pedido: new Date(ahora - 6 * 60000).toISOString(),
            items: [
                { cantidad: 1, nombre: 'Punta de anca',      notas: 'Tres cuartos' },
                { cantidad: 1, nombre: 'Brownie con helado', notas: '' },
            ],
        },
        {
            id: 105, mesa_numero: 9, mesero: 'Luis', estado: 'listo',
            hora_pedido: new Date(ahora - 20 * 60000).toISOString(),
            items: [
                { cantidad: 1, nombre: 'Cazuela de mariscos', notas: '' },
            ],
        },
        {
            id: 106, mesa_numero: 1, mesero: 'Carla', estado: 'listo',
            hora_pedido: new Date(ahora - 4 * 60000).toISOString(),
            items: [
                { cantidad: 2, nombre: 'Carpaccio de res',    notas: '' },
                { cantidad: 2, nombre: 'Jugo natural',        notas: 'Sin azúcar' },
            ],
        },
    ];
}