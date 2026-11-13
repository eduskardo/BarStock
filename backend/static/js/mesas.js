// ============================================================
//  mesas.js — Gestión de mesas
// ============================================================

let mesasData = [];
let filtroActual = 'todas';
let busqueda = '';
let mesaSeleccionada = null;

document.addEventListener('DOMContentLoaded', () => {
    cargarMesas();
    initFiltros();
    initBuscador();
    initModal();
    // Refrescar cada 30 s para ver cambios de cocina
    setInterval(cargarMesas, 30000);
});

/* ---------- Cargar mesas desde la API ---------- */
async function cargarMesas() {
    try {
        mesasData = await API.get('/mesas');
        renderMesas();
        actualizarContadores();
    } catch (e) {
        console.error('Error al cargar mesas:', e);
        mesasData = [];
        renderMesas();
        actualizarContadores();
    }
}

/* ---------- Render del grid ---------- */
function renderMesas() {
    const grid = document.getElementById('mesasGrid');
    grid.innerHTML = '';

    const filtradas = mesasData.filter(m => {
        const matchFiltro = filtroActual === 'todas'
            || (filtroActual === 'abiertas' && m.estado === 'ocupada')
            || (filtroActual === 'pagadas' && m.estado === 'pagada')
            || (filtroActual === 'reservadas' && m.estado === 'reservada')
            || m.estado === filtroActual;

        const matchBusqueda = !busqueda
            || m.numero.toString().includes(busqueda);

        return matchFiltro && matchBusqueda;
    });

    if (!filtradas.length) {
        grid.innerHTML = `<p class="sin-resultados">No hay mesas que coincidan.</p>`;
        return;
    }

    filtradas.forEach(m => {
        const card = document.createElement('div');
        card.className = 'mesa-card';
        card.dataset.estado = m.estado;
        card.dataset.id = m.id;

        // Total desde pedidos abiertos (si el backend lo devuelve)
        const total = m.total || 0;

        card.innerHTML = `
            <div class="mesa-numero">
                <span>#${m.numero}</span>
                <span class="estado-tag">${m.estado}</span>
            </div>
            <div class="mesa-info">
                <span>👤 ${m.mesero_nombre || 'Libre'}</span>
                <span>${m.capacidad || 0} pax</span>
            </div>
            <div class="mesa-total">${Utils.formatearMoneda(total)}</div>
        `;

        card.addEventListener('click', () => abrirDetalleMesa(m.id));
        grid.appendChild(card);
    });
}

/* ---------- Filtros ---------- */
function initFiltros() {
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filtro-btn')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filtroActual = btn.dataset.filtro;
            renderMesas();
        });
    });
}

function initBuscador() {
    const input = document.getElementById('buscadorMesas');
    if (!input) return;
    input.addEventListener('input', e => {
        busqueda = e.target.value.trim();
        renderMesas();
    });
}

function actualizarContadores() {
    const c = {
        todas:      mesasData.length,
        abiertas:   mesasData.filter(m => m.estado === 'ocupada').length,
        pagadas:    mesasData.filter(m => m.estado === 'pagada').length,
        reservadas: mesasData.filter(m => m.estado === 'reservada').length,
    };
    const $ = id => document.getElementById(id);
    if ($('countTodas'))      $('countTodas').textContent      = c.todas;
    if ($('countAbiertas'))   $('countAbiertas').textContent   = c.abiertas;
    if ($('countPagadas'))    $('countPagadas').textContent    = c.pagadas;
    if ($('countReservadas')) $('countReservadas').textContent = c.reservadas;
}

/* ---------- Modal de detalle ---------- */
function initModal() {
    const modal = document.getElementById('modalDetalle');
    const cerrar = document.getElementById('cerrarModal');
    if (cerrar) {
        cerrar.addEventListener('click', () => modal.classList.remove('open'));
    }
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('open');
    });
}

async function abrirDetalleMesa(id) {
    const modal  = document.getElementById('modalDetalle');
    const titulo = document.getElementById('modalTitulo');
    const body   = document.getElementById('modalBody');

    mesaSeleccionada = id;
    titulo.textContent = `Mesa #${id}`;
    body.innerHTML = '<p>Cargando...</p>';
    modal.classList.add('open');

    // Buscamos el estado actual de la mesa en la lista local
    const mesaLocal = mesasData.find(m => m.id === id);
    
    if (mesaLocal && mesaLocal.estado === 'libre') {
        body.innerHTML = '<p class="sin-resultados">Mesa disponible. No hay consumo.</p>';
        renderBotones('libre');
    } else {
        try {
            const consumo = await API.get(`/pedidos/mesa/${id}/consumo`);
            renderDetalle(consumo);
        } catch (e) {
            console.error('Error al cargar consumo:', e);
            body.innerHTML = `<p class="sin-resultados">Sin consumo registrado.</p>`;
            renderBotones(mesaLocal ? mesaLocal.estado : 'libre');
        }
    }
}

function renderDetalle(consumo) {
    const body = document.getElementById('modalBody');

    const itemsHTML = consumo.items.length
        ? consumo.items.map(it => `
            <div class="detalle-item">
                <span>${it.cantidad}× ${it.nombre}</span>
                <span>${Utils.formatearMoneda(it.precio * it.cantidad)}</span>
            </div>
        `).join('')
        : '<p class="sin-resultados">Sin productos pedidos.</p>';

    body.innerHTML = `
        ${itemsHTML}
        <div class="detalle-total">
            <span>TOTAL</span>
            <span>${Utils.formatearMoneda(consumo.total)}</span>
        </div>
    `;

    renderBotones(consumo.estado);
}

function renderBotones(estado) {
    // Buscamos el footer del modal de manera segura
    const footer = document.querySelector('#modalDetalle .modal-footer');
    if (!footer) return;
    
    footer.innerHTML = ''; // Limpiar botones anteriores

    if (estado === 'libre' || estado === 'reservada') {
        const btnAbrir = document.createElement('button');
        btnAbrir.className = 'btn btn-primary';
        btnAbrir.innerHTML = '🪑 Abrir mesa';
        btnAbrir.addEventListener('click', abrirMesa);
        footer.appendChild(btnAbrir);

    } else if (estado === 'ocupada') {
        const btnPOS = document.createElement('button');
        btnPOS.className = 'btn btn-secondary';
        btnPOS.innerHTML = '🧾 Tomar pedido';
        btnPOS.addEventListener('click', () => {
            window.location.href = `${window.APP_URLS.pos}?mesa=${mesaSeleccionada}`;
        });
        footer.appendChild(btnPOS);

        const btnCobrar = document.createElement('button');
        btnCobrar.className = 'btn btn-success';
        btnCobrar.innerHTML = '💰 Cobrar';
        btnCobrar.addEventListener('click', () => {
            window.location.href = `${window.APP_URLS.pos}?mesa=${mesaSeleccionada}&cobrar=1`;
        });
        footer.appendChild(btnCobrar);

    } else if (estado === 'pagada') {
        const btnLiberar = document.createElement('button');
        btnLiberar.className = 'btn btn-primary';
        btnLiberar.innerHTML = '🔄 Liberar mesa';
        btnLiberar.addEventListener('click', liberarMesa);
        footer.appendChild(btnLiberar);
    }
}

async function liberarMesa() {
    if (!mesaSeleccionada) return;
    try {
        await API.post(`/pedidos/mesa/${mesaSeleccionada}/liberar`, {});
        Utils.mostrarToast('Mesa liberada correctamente', 'success');
        document.getElementById('modalDetalle').classList.remove('open');
        cargarMesas();
    } catch (e) {
        Utils.mostrarToast(e.message || 'Error al liberar mesa', 'error');
    }
}