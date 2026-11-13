// ============================================================
//  reportes.js — Módulo de Reportes y Analítica Comercial
// ============================================================

const REP = {
    filtros: { desde: null, hasta: null, sucursal_id: null },
    charts: {},   // instancias de Chart.js
};

const COLORES = [
    '#C8102E', '#3B82F6', '#10B981', '#F59E0B',
    '#8B5CF6', '#EF4444', '#06B6D4', '#84CC16',
    '#EC4899', '#F97316',
];

document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.tienePermiso('reportes.ver')) {
        Utils.mostrarToast('Sin permiso para esta sección', 'error');
        setTimeout(() => window.location.href = 'index.html', 1500);
        return;
    }

    initPresets();
    initFiltros();
    initExportar();
    cargarSucursales();
    cargarTodo();

    window.addEventListener('resize', debounce(() => {
        Object.values(REP.charts).forEach(c => c.resize());
    }, 200));
});

/* ------------------------------------------------------------
   PRESETS DE FECHAS
   ------------------------------------------------------------ */
function initPresets() {
    document.querySelectorAll('.preset').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.preset')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const rango = calcularRango(btn.dataset.preset);
            document.getElementById('filtroDesde').value = rango.desde;
            document.getElementById('filtroHasta').value = rango.hasta;
            aplicarFiltros();
        });
    });
}

function calcularRango(preset) {
    const hoy = new Date();
    const iso = d => d.toISOString().split('T')[0];

    switch (preset) {
        case '7d': {
            const d = new Date(hoy); d.setDate(d.getDate() - 6);
            return { desde: iso(d), hasta: iso(hoy) };
        }
        case '30d': {
            const d = new Date(hoy); d.setDate(d.getDate() - 29);
            return { desde: iso(d), hasta: iso(hoy) };
        }
        case 'mes': {
            return {
                desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)),
                hasta: iso(hoy),
            };
        }
        case 'mes-ant': {
            const primero = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
            const ultimo  = new Date(hoy.getFullYear(), hoy.getMonth(), 0);
            return { desde: iso(primero), hasta: iso(ultimo) };
        }
        case 'year': {
            return {
                desde: iso(new Date(hoy.getFullYear(), 0, 1)),
                hasta: iso(hoy),
            };
        }
        default:
            return calcularRango('30d');
    }
}

/* ------------------------------------------------------------
   FILTROS
   ------------------------------------------------------------ */
function initFiltros() {
    const { desde, hasta } = calcularRango('30d');
    document.getElementById('filtroDesde').value = desde;
    document.getElementById('filtroHasta').value = hasta;

    document.getElementById('btnAplicar')
        .addEventListener('click', aplicarFiltros);
}

function aplicarFiltros() {
    REP.filtros.desde = document.getElementById('filtroDesde').value;
    REP.filtros.hasta = document.getElementById('filtroHasta').value;
    REP.filtros.sucursal_id =
        document.getElementById('filtroSucursal').value || null;

    cargarTodo();
}

async function cargarSucursales() {
    // Si el usuario tiene permiso financiero, carga sucursales para filtro
    if (!Auth.tienePermiso('reportes.financiero')) return;

    try {
        const sucs = await API.get('/sucursales');
        const sel = document.getElementById('filtroSucursal');
        sel.innerHTML = '<option value="">Todas las sucursales</option>' +
            sucs.map(s => `<option value="${s.id}">${s.nombre}</option>`).join('');
    } catch (e) { /* silencioso */ }
}

/* ------------------------------------------------------------
   CARGA PRINCIPAL
   ------------------------------------------------------------ */
async function cargarTodo() {
    cargarKPIs();
    cargarVentasPorDia();
    cargarVentasPorHora();
    cargarCategorias();
    cargarMetodosPago();
    cargarTopProductos();
    cargarFoodCost();
    cargarMeseros();
    if (Auth.tienePermiso('reportes.financiero')) cargarPorSucursal();
}

function qs() {
    const p = new URLSearchParams();
    if (REP.filtros.desde)       p.set('desde', REP.filtros.desde);
    if (REP.filtros.hasta)       p.set('hasta', REP.filtros.hasta);
    if (REP.filtros.sucursal_id) p.set('sucursal_id', REP.filtros.sucursal_id);
    return p.toString();
}

/* ------------------------------------------------------------
   KPIs
   ------------------------------------------------------------ */
async function cargarKPIs() {
    let data;
    try { data = await API.get(`/reportes/kpis?${qs()}`); }
    catch (e) { data = getKPIsDemo(); }

    const setVar = (el, pct) => {
        el.textContent = `${pct >= 0 ? '▲' : '▼'} ${Math.abs(pct).toFixed(1)}%`;
        el.classList.remove('positivo', 'negativo');
        el.classList.add(pct >= 0 ? 'positivo' : 'negativo');
    };

    document.getElementById('kpiVentas').textContent =
        Utils.formatearMoneda(data.ventas.total);
    setVar(document.getElementById('kpiVentasVar'), data.ventas.variacion_pct);

    document.getElementById('kpiPedidos').textContent = data.pedidos.total;
    setVar(document.getElementById('kpiPedidosVar'), data.pedidos.variacion_pct);

    document.getElementById('kpiTicket').textContent =
        Utils.formatearMoneda(data.ticket_promedio.valor);
    setVar(document.getElementById('kpiTicketVar'),
           data.ticket_promedio.variacion_pct);

    document.getElementById('kpiFC').textContent =
        `${data.food_cost.porcentaje}%`;
    document.getElementById('kpiFCSub').textContent =
        `${Utils.formatearMoneda(data.food_cost.total)} en insumos`;

    document.getElementById('kpiMargen').textContent =
        `${data.margen_bruto.porcentaje}%`;
    document.getElementById('kpiMargenSub').textContent =
        Utils.formatearMoneda(data.margen_bruto.total);
    setVar(document.getElementById('kpiMargenVar'),
           data.margen_bruto.variacion_pct);
}

/* ------------------------------------------------------------
   CHART: VENTAS POR DÍA
   ------------------------------------------------------------ */
async function cargarVentasPorDia() {
    let data;
    try { data = await API.get(`/reportes/ventas-por-dia?${qs()}`); }
    catch (e) { data = getVentasDiaDemo(); }

    const ctx = document.getElementById('chartVentas');
    destruir('ventas');

    REP.charts.ventas = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => formatearFechaCorta(d.fecha)),
            datasets: [{
                label: 'Ventas ($)',
                data: data.map(d => d.ventas),
                borderColor: '#C8102E',
                backgroundColor: 'rgba(200,16,46,.08)',
                tension: .35,
                fill: true,
                pointRadius: 3,
                pointHoverRadius: 6,
                borderWidth: 2.5,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => Utils.formatearMoneda(ctx.parsed.y),
                    },
                },
            },
            scales: {
                y: {
                    ticks: {
                        callback: v =>
                            '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
                    },
                    grid: { color: '#F3F4F6' },
                },
                x: { grid: { display: false } },
            },
        },
    });
}

/* ------------------------------------------------------------
   CHART: VENTAS POR HORA
   ------------------------------------------------------------ */
async function cargarVentasPorHora() {
    let data;
    try { data = await API.get(`/reportes/ventas-por-hora?${qs()}`); }
    catch (e) { data = getVentasHoraDemo(); }

    // Rellenar horas 0-23 sin datos con 0
    const horas = Array.from({ length: 24 }, (_, h) => h);
    const ventasPorHora = horas.map(h => {
        const d = data.find(x => x.hora === h);
        return d ? d.ventas : 0;
    });

    const ctx = document.getElementById('chartHoras');
    destruir('horas');

    REP.charts.horas = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: horas.map(h => `${h}:00`),
            datasets: [{
                label: 'Ventas',
                data: ventasPorHora,
                backgroundColor: horas.map(h =>
                    (h >= 12 && h <= 14) || (h >= 19 && h <= 22)
                        ? '#C8102E'    // horas pico
                        : '#FCA5A5'
                ),
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => Utils.formatearMoneda(ctx.parsed.y),
                    },
                },
            },
            scales: {
                y: {
                    ticks: {
                        callback: v =>
                            '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
                    },
                    grid: { color: '#F3F4F6' },
                },
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 0, autoSkip: true, font: { size: 10 } },
                },
            },
        },
    });
}

/* ------------------------------------------------------------
   CHART: CATEGORÍAS (dona)
   ------------------------------------------------------------ */
async function cargarCategorias() {
    let data;
    try { data = await API.get(`/reportes/ventas-por-categoria?${qs()}`); }
    catch (e) { data = getCategoriasDemo(); }

    const ctx = document.getElementById('chartCategorias');
    destruir('categorias');

    REP.charts.categorias = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.categoria),
            datasets: [{
                data: data.map(d => d.ingresos),
                backgroundColor: COLORES,
                borderWidth: 2,
                borderColor: '#fff',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, padding: 10 } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const v = ctx.parsed;
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total ? (v / total * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${Utils.formatearMoneda(v)} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

/* ------------------------------------------------------------
   CHART: MÉTODOS DE PAGO (dona)
   ------------------------------------------------------------ */
async function cargarMetodosPago() {
    let data;
    try { data = await API.get(`/reportes/ventas-por-metodo-pago?${qs()}`); }
    catch (e) { data = getPagosDemo(); }

    const ctx = document.getElementById('chartPagos');
    destruir('pagos');

    REP.charts.pagos = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => capitalizar(d.metodo)),
            datasets: [{
                data: data.map(d => d.total),
                backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#8B5CF6'],
                borderWidth: 2,
                borderColor: '#fff',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, padding: 10 } },
                tooltip: {
                    callbacks: {
                        label: ctx => Utils.formatearMoneda(ctx.parsed),
                    },
                },
            },
        },
    });
}

/* ------------------------------------------------------------
   TOP PRODUCTOS
   ------------------------------------------------------------ */
async function cargarTopProductos() {
    let data;
    try {
        data = await API.get(`/reportes/top-productos?limite=15&${qs()}`);
    } catch (e) {
        data = getTopProductosDemo();
    }

    const tbody = document.getElementById('tablaTopProductos');
    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="9"
            style="text-align:center;padding:2rem;color:#6B7280">
            Sin datos en el período</td></tr>`;
        return;
    }

    tbody.innerHTML = data.map((p, i) => {
        const costoU = p.unidades ? p.costo_total / p.unidades : 0;
        const margenU = p.unidades ? p.margen / p.unidades : 0;
        const fcClase = p.food_cost_pct <= 30 ? 'fc-bajo'
                      : p.food_cost_pct <= 45 ? 'fc-medio'
                      : 'fc-alto';
        return `
            <tr>
                <td><strong>${i + 1}</strong></td>
                <td><strong>${p.nombre}</strong></td>
                <td>${p.categoria || '—'}</td>
                <td class="num">${Utils.formatearMoneda(p.precio)}</td>
                <td class="num">${Utils.formatearMoneda(costoU)}</td>
                <td class="num">${Utils.formatearMoneda(margenU)}</td>
                <td class="num">
                    <span class="fc-badge ${fcClase}">${p.food_cost_pct}%</span>
                </td>
                <td class="num">${p.unidades}</td>
                <td class="num"><strong>${Utils.formatearMoneda(p.ingresos)}</strong></td>
            </tr>
        `;
    }).join('');
}

/* ------------------------------------------------------------
   FOOD COST / MATRIZ BCG
   ------------------------------------------------------------ */
async function cargarFoodCost() {
    let data;
    try {
        data = await API.get(`/reportes/food-cost-productos?limite=60&${qs()}`);
    } catch (e) {
        data = getFoodCostDemo();
    }

    const cuadrantes = {
        estrella:  [],
        vaca:      [],
        incognita: [],
        perro:     [],
    };

    data.forEach(p => cuadrantes[p.clasificacion]?.push(p));

    renderBCG('bcgGrid', cuadrantes);
}

function renderBCG(containerId, cuadrantes) {
    const cont = document.getElementById(containerId);

    const titulos = {
        estrella:  '★ Estrellas (alto margen · alto volumen)',
        vaca:      '🐄 Vacas lecheras (alto margen · bajo volumen)',
        incognita: '❓ Incógnitas (bajo margen · alto volumen)',
        perro:     '🐕 Perros (bajo margen · bajo volumen)',
    };

    const html = ['estrella', 'vaca', 'incognita', 'perro'].map(clave => {
        const items = cuadrantes[clave] || [];
        const lista = items.length
            ? items.slice(0, 8).map(p => `
                <div class="bcg-item">
                    <strong>${p.nombre}</strong>
                    <span class="meta">
                        ${p.margen_pct}% margen · ${p.unidades} uds
                    </span>
                </div>
            `).join('')
            : '<p class="bcg-vacio">Sin productos en este cuadrante</p>';

        return `
            <div class="bcg-cuadrante ${clave}">
                <h4>${titulos[clave]}</h4>
                ${lista}
            </div>
        `;
    }).join('');

    cont.innerHTML = html;
}

/* ------------------------------------------------------------
   RANKING DE MESEROS
   ------------------------------------------------------------ */
async function cargarMeseros() {
    let data;
    try { data = await API.get(`/reportes/ventas-por-mesero?${qs()}`); }
    catch (e) { data = getMeserosDemo(); }

    const tbody = document.getElementById('tablaMeseros');
    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="5"
            style="text-align:center;padding:2rem;color:#6B7280">
            Sin datos en el período</td></tr>`;
        return;
    }

    tbody.innerHTML = data.map((m, i) => `
        <tr>
            <td><strong>${i + 1}</strong></td>
            <td><strong>${m.nombre}</strong></td>
            <td class="num">${m.pedidos}</td>
            <td class="num">${Utils.formatearMoneda(m.ventas)}</td>
            <td class="num">${Utils.formatearMoneda(m.ticket_promedio)}</td>
        </tr>
    `).join('');
}

/* ------------------------------------------------------------
   SUCURSALES
   ------------------------------------------------------------ */
async function cargarPorSucursal() {
    let data;
    try {
        const p = new URLSearchParams();
        if (REP.filtros.desde) p.set('desde', REP.filtros.desde);
        if (REP.filtros.hasta) p.set('hasta', REP.filtros.hasta);
        data = await API.get(`/reportes/ventas-por-sucursal?${p}`);
    } catch (e) {
        data = getSucursalesDemo();
    }

    const cont = document.getElementById('sucursalesGrid');
    if (!data.length) {
        cont.innerHTML = '<p style="padding:1rem;color:#6B7280">Sin datos</p>';
        return;
    }

    const max = Math.max(...data.map(d => d.ventas), 1);
    cont.innerHTML = data.map(s => `
        <div class="sucursal-card">
            <div class="sucursal-nombre">${s.nombre}</div>
            <div class="sucursal-num">${Utils.formatearMoneda(s.ventas)}</div>
            <div class="sucursal-sub">${s.pedidos} pedidos</div>
            <div class="sucursal-sub">
                ${(s.ventas / max * 100).toFixed(0)}% del líder
            </div>
        </div>
    `).join('');
}

/* ------------------------------------------------------------
   EXPORTAR CSV
   ------------------------------------------------------------ */
function initExportar() {
    document.getElementById('btnExportar')
        ?.addEventListener('click', () => {
            const token = Auth.getToken();
            const url = `http://localhost:5000/api/reportes/exportar/top-productos.csv?${qs()}`;

            // Descarga con fetch para enviar el token
            fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                .then(r => r.blob())
                .then(blob => {
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = `top_productos_${REP.filtros.desde}_${REP.filtros.hasta}.csv`;
                    a.click();
                    URL.revokeObjectURL(a.href);
                })
                .catch(() => Utils.mostrarToast('Error al exportar', 'error'));
        });
}

/* ------------------------------------------------------------
   HELPERS
   ------------------------------------------------------------ */
function destruir(nombre) {
    if (REP.charts[nombre]) {
        REP.charts[nombre].destroy();
        delete REP.charts[nombre];
    }
}

function formatearFechaCorta(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
}

function capitalizar(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function debounce(fn, ms) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}

/* ------------------------------------------------------------
   DATOS DEMO
   ------------------------------------------------------------ */
function getKPIsDemo() {
    return {
        ventas:          { total: 4250000, variacion_pct: 12.5 },
        pedidos:         { total: 187,      variacion_pct: 8.2 },
        ticket_promedio: { valor: 22727,    variacion_pct: 4.0 },
        food_cost:       { total: 1450000,  porcentaje: 34.1 },
        margen_bruto:    { total: 2800000,  porcentaje: 65.9, variacion_pct: 1.8 },
    };
}

function getVentasDiaDemo() {
    const hoy = new Date();
    return Array.from({ length: 30 }, (_, i) => {
        const d = new Date(hoy); d.setDate(d.getDate() - (29 - i));
        return {
            fecha: d.toISOString().split('T')[0],
            pedidos: 5 + Math.floor(Math.random() * 10),
            ventas: 100000 + Math.floor(Math.random() * 250000),
        };
    });
}

function getVentasHoraDemo() {
    return [
        { hora: 12, ventas: 320000 }, { hora: 13, ventas: 480000 },
        { hora: 14, ventas: 290000 }, { hora: 19, ventas: 420000 },
        { hora: 20, ventas: 610000 }, { hora: 21, ventas: 540000 },
        { hora: 22, ventas: 250000 },
    ];
}

function getCategoriasDemo() {
    return [
        { categoria: 'Carnes',   ingresos: 1800000 },
        { categoria: 'Pescados', ingresos: 950000 },
        { categoria: 'Entradas', ingresos: 620000 },
        { categoria: 'Bebidas',  ingresos: 540000 },
        { categoria: 'Postres',  ingresos: 340000 },
    ];
}

function getPagosDemo() {
    return [
        { metodo: 'efectivo',      total: 1850000, transacciones: 82 },
        { metodo: 'tarjeta',       total: 1620000, transacciones: 68 },
        { metodo: 'transferencia', total:  780000, transacciones: 37 },
    ];
}

function getTopProductosDemo() {
    return [
        { producto_id: 1, nombre: 'Lomo al trapo', categoria: 'Carnes',
          precio: 45000, costo_total: 135000, margen: 315000,
          food_cost_pct: 30, unidades: 10, ingresos: 450000 },
        { producto_id: 2, nombre: 'Ceviche mixto', categoria: 'Pescados',
          precio: 32000, costo_total: 80000,  margen: 240000,
          food_cost_pct: 25, unidades: 10, ingresos: 320000 },
        { producto_id: 3, nombre: 'Pasta carbonara', categoria: 'Pastas',
          precio: 34000, costo_total: 119000, margen: 221000,
          food_cost_pct: 35, unidades: 10, ingresos: 340000 },
        { producto_id: 4, nombre: 'Limonada de coco', categoria: 'Bebidas',
          precio: 12000, costo_total: 24000,  margen: 96000,
          food_cost_pct: 20, unidades: 10, ingresos: 120000 },
    ];
}

function getFoodCostDemo() {
    return [
        { nombre: 'Lomo al trapo',    margen_pct: 70, unidades: 45, clasificacion: 'estrella' },
        { nombre: 'Ceviche mixto',    margen_pct: 75, unidades: 38, clasificacion: 'estrella' },
        { nombre: 'Salmón grillé',    margen_pct: 68, unidades: 22, clasificacion: 'estrella' },
        { nombre: 'Trucha al ajillo', margen_pct: 72, unidades: 12, clasificacion: 'vaca' },
        { nombre: 'Carpaccio de res', margen_pct: 65, unidades: 10, clasificacion: 'vaca' },
        { nombre: 'Pasta carbonara',  margen_pct: 45, unidades: 30, clasificacion: 'incognita' },
        { nombre: 'Hamburguesa',      margen_pct: 50, unidades: 28, clasificacion: 'incognita' },
        { nombre: 'Ensalada César',   margen_pct: 30, unidades: 8,  clasificacion: 'perro' },
        { nombre: 'Sopa del día',     margen_pct: 25, unidades: 5,  clasificacion: 'perro' },
    ];
}

function getMeserosDemo() {
    return [
        { nombre: 'Ana Gómez',   pedidos: 62, ventas: 1420000, ticket_promedio: 22903 },
        { nombre: 'Luis Pérez',  pedidos: 55, ventas: 1180000, ticket_promedio: 21454 },
        { nombre: 'Carla Ruiz',  pedidos: 48, ventas:  980000, ticket_promedio: 20416 },
        { nombre: 'Diego Mora',  pedidos: 22, ventas:  670000, ticket_promedio: 30454 },
    ];
}

function getSucursalesDemo() {
    return [
        { sucursal_id: 1, nombre: 'Sede Centro',   pedidos: 120, ventas: 2450000 },
        { sucursal_id: 2, nombre: 'Sede Norte',    pedidos:  67, ventas: 1400000 },
        { sucursal_id: 3, nombre: 'Sede Chapinero',pedidos:  40, ventas:  900000 },
    ];
}