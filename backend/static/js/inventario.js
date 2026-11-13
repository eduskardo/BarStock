// ============================================================
//  inventario.js — Insumos, movimientos, alertas y WebSocket
// ============================================================

const INV = {
    insumos: [],
    movimientos: [],
    alertas: [],
    socket: null,
    filtros: {
        q: '', categoria: '', soloBajo: false,
        insumoMov: '', tipoMov: '', desde: '', hasta: '',
    },
};

document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.tienePermiso('inventario.ver')) {
        Utils.mostrarToast('Sin permiso para esta sección', 'error');
        setTimeout(() => window.location.href = 'index.html', 1500);
        return;
    }

    initTabs();
    initToolbar();
    initModales();
    initSocket();

    cargarResumen();
    cargarInsumos();
});

/* ------------------------------------------------------------
   TABS
   ------------------------------------------------------------ */
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.querySelectorAll('.inv-tab').forEach(sec => {
                sec.hidden = sec.dataset.tabContent !== btn.dataset.tab;
            });

            const tab = btn.dataset.tab;
            if (tab === 'movimientos') cargarMovimientos();
            if (tab === 'alertas')     cargarAlertas();
        });
    });
}

/* ------------------------------------------------------------
   TOOLBAR — FILTROS
   ------------------------------------------------------------ */
function initToolbar() {
    const inputQ = document.getElementById('buscarInsumo');
    let t;
    inputQ?.addEventListener('input', e => {
        clearTimeout(t);
        t = setTimeout(() => {
            INV.filtros.q = e.target.value.trim();
            cargarInsumos();
        }, 250);
    });

    document.getElementById('filtroCategoria')
        ?.addEventListener('change', e => {
            INV.filtros.categoria = e.target.value;
            cargarInsumos();
        });

    document.getElementById('soloBajo')
        ?.addEventListener('change', e => {
            INV.filtros.soloBajo = e.target.checked;
            cargarInsumos();
        });

    document.getElementById('btnNuevoInsumo')
        ?.addEventListener('click', abrirNuevoInsumo);

    // Filtros movimientos
    document.getElementById('filtroInsumoMov')
        ?.addEventListener('change', e => {
            INV.filtros.insumoMov = e.target.value;
            cargarMovimientos();
        });
    document.getElementById('filtroTipoMov')
        ?.addEventListener('change', e => {
            INV.filtros.tipoMov = e.target.value;
            cargarMovimientos();
        });
    document.getElementById('filtroDesde')
        ?.addEventListener('change', e => {
            INV.filtros.desde = e.target.value;
            cargarMovimientos();
        });
    document.getElementById('filtroHasta')
        ?.addEventListener('change', e => {
            INV.filtros.hasta = e.target.value;
            cargarMovimientos();
        });
    document.getElementById('btnRecargarMovs')
        ?.addEventListener('click', cargarMovimientos);
    document.getElementById('btnMovimiento')
        ?.addEventListener('click', abrirModalMovimiento);
}

/* ------------------------------------------------------------
   API — CARGA
   ------------------------------------------------------------ */
async function cargarResumen() {
    try {
        const r = await API.get('/inventario/resumen');
        document.getElementById('statTotal').textContent  = r.total_insumos;
        document.getElementById('statBajo').textContent   = r.bajo_minimo;
        document.getElementById('statValor').textContent  =
            Utils.formatearMoneda(r.valor_total);
        document.getElementById('statMovs').textContent   = r.movimientos_30d;
    } catch (e) { /* demo */ }
}

async function cargarInsumos() {
    const params = new URLSearchParams();
    if (INV.filtros.q)         params.set('q', INV.filtros.q);
    if (INV.filtros.categoria) params.set('categoria', INV.filtros.categoria);
    if (INV.filtros.soloBajo)  params.set('bajo_minimo', 'true');

    try {
        INV.insumos = await API.get(`/inventario/insumos?${params}`);
    } catch (e) {
        INV.insumos = getInsumosDemo();
    }

    renderTablaInsumos();
    llenarSelectCategorias();
    llenarSelectInsumosMov();
}

async function cargarMovimientos() {
    const params = new URLSearchParams();
    if (INV.filtros.insumoMov) params.set('insumo_id', INV.filtros.insumoMov);
    if (INV.filtros.tipoMov)   params.set('tipo', INV.filtros.tipoMov);
    if (INV.filtros.desde)     params.set('desde', INV.filtros.desde);
    if (INV.filtros.hasta)     params.set('hasta', INV.filtros.hasta);

    try {
        INV.movimientos = await API.get(`/inventario/movimientos?${params}`);
    } catch (e) {
        INV.movimientos = getMovimientosDemo();
    }
    renderTablaMovimientos();
}

async function cargarAlertas() {
    try {
        INV.alertas = await API.get('/inventario/alertas');
    } catch (e) {
        INV.alertas = INV.insumos.filter(i => i.bajo_minimo);
    }
    renderAlertas();
}

/* ------------------------------------------------------------
   RENDER — TABLAS
   ------------------------------------------------------------ */
function renderTablaInsumos() {
    const tbody = document.getElementById('tablaInsumos');
    const puedeEditar = Auth.tienePermiso('inventario.ajuste');

    if (!INV.insumos.length) {
        tbody.innerHTML = `<tr><td colspan="8"
            style="text-align:center;padding:2rem;color:#6B7280">
            No hay insumos registrados</td></tr>`;
        return;
    }

    tbody.innerHTML = INV.insumos.map(i => `
        <tr class="${i.bajo_minimo ? 'fila-alerta' : ''}">
            <td>${i.codigo || '—'}</td>
            <td><strong>${i.nombre}</strong></td>
            <td>${i.categoria || '—'}</td>
            <td class="stock-cell ${i.bajo_minimo ? 'alerta' : 'ok'}">
                ${i.stock_actual} ${i.unidad}
            </td>
            <td>${i.stock_minimo} ${i.unidad}</td>
            <td>${Utils.formatearMoneda(i.costo_unitario)}</td>
            <td>${Utils.formatearMoneda(i.valor_stock)}</td>
            <td>
                ${puedeEditar ? `
                    <button title="Editar" onclick="abrirEditarInsumo(${i.id})">✏️</button>
                    <button title="Movimiento" onclick="abrirModalMovimiento(${i.id})">📥</button>
                ` : '—'}
            </td>
        </tr>
    `).join('');
}

function renderTablaMovimientos() {
    const tbody = document.getElementById('tablaMovimientos');
    if (!INV.movimientos.length) {
        tbody.innerHTML = `<tr><td colspan="9"
            style="text-align:center;padding:2rem;color:#6B7280">
            No hay movimientos registrados</td></tr>`;
        return;
    }

    const etiquetas = {
        ingreso: 'Ingreso', egreso: 'Venta',
        ajuste_pos: 'Ajuste (+)', ajuste_neg: 'Ajuste (−)',
        merma: 'Merma', devolucion: 'Devolución',
    };

    tbody.innerHTML = INV.movimientos.map(m => `
        <tr>
            <td>${new Date(m.fecha).toLocaleString('es-CO')}</td>
            <td><strong>${m.insumo_nombre}</strong></td>
            <td>
                <span class="tag-tipo tag-${m.tipo}">
                    ${etiquetas[m.tipo] || m.tipo}
                </span>
            </td>
            <td>${m.cantidad} ${m.unidad}</td>
            <td>${m.stock_antes}</td>
            <td>${m.stock_despues}</td>
            <td>${Utils.formatearMoneda(m.costo_total)}</td>
            <td>${m.motivo || '—'}</td>
            <td>${m.usuario || '—'}</td>
        </tr>
    `).join('');
}

function renderAlertas() {
    const grid = document.getElementById('alertasGrid');
    if (!INV.alertas.length) {
        grid.innerHTML = '<p style="padding:2rem;color:#6B7280">No hay alertas 🎉</p>';
        return;
    }
    grid.innerHTML = INV.alertas.map(a => `
        <div class="alerta-card">
            <div class="alerta-nombre">${a.nombre || a.insumo}</div>
            <div class="alerta-detalle">Stock bajo mínimo</div>
            <div class="alerta-nums">
                <span>Actual: ${a.stock_actual} ${a.unidad || ''}</span>
                <span>Mín: ${a.stock_minimo} ${a.unidad || ''}</span>
            </div>
        </div>
    `).join('');
}

/* ------------------------------------------------------------
   SELECTS
   ------------------------------------------------------------ */
function llenarSelectCategorias() {
    const cats = [...new Set(INV.insumos.map(i => i.categoria).filter(Boolean))];
    const sel = document.getElementById('filtroCategoria');
    if (!sel) return;
    sel.innerHTML = '<option value="">Todas las categorías</option>' +
        cats.map(c => `<option value="${c}">${c}</option>`).join('');
    sel.value = INV.filtros.categoria;
}

function llenarSelectInsumosMov() {
    const sel = document.getElementById('filtroInsumoMov');
    const sel2 = document.getElementById('mInsumo');
    const opts = INV.insumos.map(i =>
        `<option value="${i.id}">${i.nombre}</option>`).join('');

    if (sel) {
        sel.innerHTML = '<option value="">Todos los insumos</option>' + opts;
        sel.value = INV.filtros.insumoMov;
    }
    if (sel2) {
        sel2.innerHTML = '<option value="">Seleccionar insumo...</option>' + opts;
    }
}

/* ------------------------------------------------------------
   MODALES
   ------------------------------------------------------------ */
function initModales() {
    // Insumo
    const mInsumo = document.getElementById('modalInsumo');
    document.getElementById('cerrarModalInsumo')
        .addEventListener('click', () => mInsumo.classList.remove('open'));
    document.getElementById('cancelarInsumo')
        .addEventListener('click', () => mInsumo.classList.remove('open'));
    document.getElementById('guardarInsumo')
        .addEventListener('click', guardarInsumo);
    mInsumo.addEventListener('click', e => {
        if (e.target === mInsumo) mInsumo.classList.remove('open');
    });

    // Movimiento
    const mMov = document.getElementById('modalMovimiento');
    document.getElementById('cerrarModalMov')
        .addEventListener('click', () => mMov.classList.remove('open'));
    document.getElementById('cancelarMov')
        .addEventListener('click', () => mMov.classList.remove('open'));
    document.getElementById('guardarMov')
        .addEventListener('click', guardarMovimiento);
    mMov.addEventListener('click', e => {
        if (e.target === mMov) mMov.classList.remove('open');
    });
}

function abrirNuevoInsumo() {
    document.getElementById('modalInsumoTitulo').textContent = 'Nuevo insumo';
    document.getElementById('formInsumo').reset();
    document.getElementById('insumoId').value = '';
    document.getElementById('modalInsumo').classList.add('open');
}

function abrirEditarInsumo(id) {
    const i = INV.insumos.find(x => x.id === id);
    if (!i) return;
    document.getElementById('modalInsumoTitulo').textContent = 'Editar insumo';
    document.getElementById('insumoId').value   = i.id;
    document.getElementById('iCodigo').value    = i.codigo || '';
    document.getElementById('iNombre').value    = i.nombre;
    document.getElementById('iCategoria').value = i.categoria || '';
    document.getElementById('iUnidad').value    = i.unidad;
    document.getElementById('iCosto').value     = i.costo_unitario;
    document.getElementById('iMinimo').value    = i.stock_minimo;
    document.getElementById('iMaximo').value    = i.stock_maximo;
    document.getElementById('iPerecedero').checked = i.perecedero;
    document.getElementById('modalInsumo').classList.add('open');
}

function abrirModalMovimiento(insumoId = null) {
    const m = document.getElementById('modalMovimiento');
    document.getElementById('formMovimiento').reset();
    if (insumoId) document.getElementById('mInsumo').value = insumoId;
    m.classList.add('open');
}

/* ------------------------------------------------------------
   GUARDAR
   ------------------------------------------------------------ */
async function guardarInsumo() {
    const id = document.getElementById('insumoId').value;
    const payload = {
        codigo:        document.getElementById('iCodigo').value.trim(),
        nombre:        document.getElementById('iNombre').value.trim(),
        categoria:     document.getElementById('iCategoria').value.trim(),
        unidad:        document.getElementById('iUnidad').value,
        costo_unitario:Number(document.getElementById('iCosto').value) || 0,
        stock_minimo:  Number(document.getElementById('iMinimo').value) || 0,
        stock_maximo:  Number(document.getElementById('iMaximo').value) || 0,
        perecedero:    document.getElementById('iPerecedero').checked,
    };

    if (!payload.nombre || !payload.unidad) {
        Utils.mostrarToast('Nombre y unidad son obligatorios', 'error');
        return;
    }

    try {
        if (id) await API.put(`/inventario/insumos/${id}`, payload);
        else    await API.post('/inventario/insumos', payload);

        Utils.mostrarToast(id ? 'Insumo actualizado' : 'Insumo creado', 'success');
        document.getElementById('modalInsumo').classList.remove('open');
        cargarInsumos();
        cargarResumen();
    } catch (e) {
        Utils.mostrarToast(e.message || 'Error al guardar', 'error');
    }
}

async function guardarMovimiento() {
    const insumoId = document.getElementById('mInsumo').value;
    const tipo     = document.getElementById('mTipo').value;
    const cantidad = Number(document.getElementById('mCantidad').value);
    const costo    = Number(document.getElementById('mCosto').value) || 0;
    const factura  = document.getElementById('mFactura').value.trim();
    const motivo   = document.getElementById('mMotivo').value.trim();

    if (!insumoId || !cantidad) {
        Utils.mostrarToast('Insumo y cantidad son obligatorios', 'error');
        return;
    }

    const sucursalId = Auth.getUsuario()?.sucursal_id;
    if (!sucursalId) {
        Utils.mostrarToast('Usuario sin sucursal asignada', 'error');
        return;
    }

    try {
        if (tipo === 'ingreso') {
            await API.post('/inventario/movimientos/ingreso', {
                insumo_id: Number(insumoId),
                sucursal_id: sucursalId,
                cantidad, costo_unitario: costo,
                factura, motivo: motivo || 'Compra',
            });
        } else {
            await API.post('/inventario/movimientos/ajuste', {
                insumo_id: Number(insumoId),
                sucursal_id: sucursalId,
                cantidad, tipo, motivo,
            });
        }

        Utils.mostrarToast('Movimiento registrado', 'success');
        document.getElementById('modalMovimiento').classList.remove('open');
        cargarInsumos();
        cargarResumen();
        cargarMovimientos();
    } catch (e) {
        Utils.mostrarToast(e.message || 'Error al registrar', 'error');
    }
}

/* ------------------------------------------------------------
   WEBSOCKET — ALERTAS EN TIEMPO REAL
   ------------------------------------------------------------ */
function initSocket() {
    const elEstado = document.getElementById('estadoConexion');

    INV.socket = io('http://localhost:5000', {
        transports: ['websocket'],
    });

    INV.socket.on('connect', () => {
        elEstado?.classList.add('conectado');
        if (elEstado) elEstado.innerHTML = '<span class="dot"></span> En vivo';
        INV.socket.emit('unirse_inventario');
    });

    INV.socket.on('disconnect', () => {
        elEstado?.classList.remove('conectado');
        if (elEstado) elEstado.innerHTML = '<span class="dot"></span> Reconectando...';
    });

    INV.socket.on('alerta_stock', (data) => {
        const alertas = data.alertas || [];
        if (!alertas.length) return;

        alertas.forEach(a => {
            Utils.mostrarToast(
                `⚠️ ${a.insumo}: stock ${a.stock_actual} ${a.unidad} ` +
                `(mín ${a.stock_minimo})`,
                'error'
            );
        });

        // Refrescar tablas
        cargarInsumos();
        cargarResumen();
        // Si el usuario está en la pestaña de alertas, recargarla
        if (!document.querySelector('[data-tab-content="alertas"]')?.hidden) {
            cargarAlertas();
        }
    });
}

/* ------------------------------------------------------------
   DATOS DEMO
   ------------------------------------------------------------ */
function getInsumosDemo() {
    return [
        { id: 1, codigo: 'CAR-001', nombre: 'Lomo de res',    categoria: 'Carnes',
          unidad: 'g', stock_actual: 4500, stock_minimo: 3000,
          costo_unitario: 45, valor_stock: 202500, bajo_minimo: false },
        { id: 2, codigo: 'VER-010', nombre: 'Papa criolla',   categoria: 'Verduras',
          unidad: 'g', stock_actual: 1200, stock_minimo: 2500,
          costo_unitario: 4,  valor_stock: 4800,   bajo_minimo: true },
        { id: 3, codigo: 'BEB-100', nombre: 'Cerveza artesanal', categoria: 'Bebidas',
          unidad: 'und', stock_actual: 24, stock_minimo: 12,
          costo_unitario: 6500, valor_stock: 156000, bajo_minimo: false },
        { id: 4, codigo: 'ABR-050', nombre: 'Arroz',          categoria: 'Abarrotes',
          unidad: 'g', stock_actual: 800, stock_minimo: 5000,
          costo_unitario: 3,  valor_stock: 2400,   bajo_minimo: true },
    ];
}

function getMovimientosDemo() {
    return [
        { id: 1, insumo_nombre: 'Lomo de res', unidad: 'g',
          tipo: 'egreso', cantidad: 600, stock_antes: 5100,
          stock_despues: 4500, costo_total: 27000,
          motivo: 'Venta: Lomo al trapo (x2)', usuario: 'Sistema',
          fecha: new Date().toISOString() },
        { id: 2, insumo_nombre: 'Papa criolla', unidad: 'g',
          tipo: 'egreso', cantidad: 400, stock_antes: 1600,
          stock_despues: 1200, costo_total: 1600,
          motivo: 'Venta: Lomo al trapo (x2)', usuario: 'Sistema',
          fecha: new Date().toISOString() },
        { id: 3, insumo_nombre: 'Cerveza artesanal', unidad: 'und',
          tipo: 'ingreso', cantidad: 24, stock_antes: 0,
          stock_despues: 24, costo_total: 156000,
          motivo: 'Compra · Factura F-1234', usuario: 'admin',
          fecha: new Date(Date.now() - 3600000).toISOString() },
    ];
}