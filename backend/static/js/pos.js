// ============================================================
//  pos.js — Módulo de Punto de Venta
//  Carrito, categorías, productos, envío a cocina y cobro
// ============================================================

/* ------------------------------------------------------------
   ESTADO GLOBAL DEL POS
   ------------------------------------------------------------ */
const POS = {
    mesaActual: null,             // { id, numero }
    categoriaActual: 'todas',
    productos: [],                // carta completa
    carrito: [],                  // [{ id, nombre, precio, cantidad, notas }]
    productoEnEdicion: null,      // producto seleccionado en el modal
    metodoPago: 'efectivo',
    impuestoPct: 0.19,            // 19% configurable
};

document.addEventListener('DOMContentLoaded', () => {
    initCarritoFlotante();
    initCategorias();
    initBuscador();
    initModalProducto();
    initModalMesa();
    initModalCobro();
    initAccionesCarrito();

    cargarCarta();
    cargarMesaDesdeURL();
});

/* ------------------------------------------------------------
   CARGA DE DATOS
   ------------------------------------------------------------ */
async function cargarCarta() {
    try {
        // ✅ RUTA CORRECTA (incluye /pedidos/ porque así está el blueprint)
        POS.productos = await API.get('/pedidos/productos');
    } catch (e) {
        console.error("Error al cargar productos:", e);
        POS.productos = getCartaDemo(); // Fallback
    }
    renderCategorias();
    renderProductos();
}
async function cargarMesaDesdeURL() {
    const params = new URLSearchParams(window.location.search);
    const mesaId = params.get('mesa');
    const irACobrar = params.get('cobrar') === '1';

    if (mesaId) {
        POS.mesaActual = { id: Number(mesaId), numero: mesaId };
        actualizarMesaUI();

        // 🔥 NUEVO: Cargar los productos que ya están en la mesa
        try {
            const consumo = await API.get(`/pedidos/mesa/${mesaId}/consumo`);
            if (consumo.items && consumo.items.length > 0) {
                POS.carrito = consumo.items.map(it => ({
                    id: it.producto_id,
                    nombre: it.nombre,
                    precio: it.precio,
                    cantidad: it.cantidad,
                    notas: it.notas
                }));
                renderCarrito();
                actualizarBadgeCarrito();
                
                // Si venimos directo a cobrar, abrimos el modal automáticamente
                if (irACobrar) {
                    setTimeout(abrirModalCobro, 300);
                }
            }
        } catch (e) {
            console.error("Error al cargar consumo de la mesa:", e);
        }
    }
}

/* ------------------------------------------------------------
   CATEGORÍAS
   ------------------------------------------------------------ */
function initCategorias() {
    // Se recrean al renderizar
}

function renderCategorias() {
    const nav = document.getElementById('categoriasNav');
    const categorias = ['todas', ...new Set(POS.productos.map(p => p.categoria))];

    nav.innerHTML = categorias.map(cat => `
        <button class="cat-btn ${cat === POS.categoriaActual ? 'active' : ''}"
                data-cat="${cat}">
            ${cat === 'todas' ? '🍽️ Todas' : capitalizar(cat)}
        </button>
    `).join('');

    nav.querySelectorAll('.cat-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            POS.categoriaActual = btn.dataset.cat;
            renderCategorias();
            renderProductos();
        });
    });
}

/* ------------------------------------------------------------
   PRODUCTOS
   ------------------------------------------------------------ */
function renderProductos() {
    const grid = document.getElementById('productosGrid');
    const filtro = document.getElementById('buscarProducto')?.value
                    .toLowerCase().trim() || '';

    const filtrados = POS.productos.filter(p => {
        const matchCat = POS.categoriaActual === 'todas'
            || p.categoria === POS.categoriaActual;
        const matchBusq = !filtro
            || p.nombre.toLowerCase().includes(filtro);
        return matchCat && matchBusq && p.activo !== false;
    });

    if (!filtrados.length) {
        grid.innerHTML = '<p class="carrito-vacio">No se encontraron productos.</p>';
        return;
    }

    grid.innerHTML = filtrados.map(p => {
        // Si no está disponible, se renderiza diferente
        const agotado = p.disponible === false;
        
        return `
        <div class="producto-card ${agotado ? 'agotado' : ''}" data-id="${p.id}" ${agotado ? 'data-agotado="true"' : ''}>
            ${p.destacado && !agotado ? '<span class="prod-tag">Top</span>' : ''}
            ${agotado ? '<span class="prod-tag tag-agotado">AGOTADO</span>' : ''}
            <div class="prod-nombre">${p.nombre}</div>
            ${p.descripcion
                ? `<div class="prod-desc">${p.descripcion}</div>`
                : ''}
            <div class="prod-precio">${Utils.formatearMoneda(p.precio)}</div>
        </div>
        `;
    }).join('');

    grid.querySelectorAll('.producto-card').forEach(card => {
        // Si está agotado, no hacemos nada al hacer clic
        if (card.dataset.agotado === 'true') {
            card.addEventListener('click', (e) => {
                e.stopPropagation();
                Utils.mostrarToast('⚠️ Producto agotado por falta de insumos', 'error');
            });
            return;
        }

        card.addEventListener('click', () => {
            const id = Number(card.dataset.id);
            const prod = POS.productos.find(p => p.id === id);
            abrirModalProducto(prod);
        });
    });
}

function initBuscador() {
    const input = document.getElementById('buscarProducto');
    if (!input) return;
    let timeout;
    input.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(renderProductos, 150);
    });
}

/* ------------------------------------------------------------
   MODAL DE PRODUCTO (cantidad + notas)
   ------------------------------------------------------------ */
function initModalProducto() {
    const modal = document.getElementById('modalProducto');
    const close = () => modal.classList.remove('open');

    document.getElementById('cerrarModalProducto').addEventListener('click', close);
    document.getElementById('cancelarProducto').addEventListener('click', close);
    modal.addEventListener('click', e => {
        if (e.target === modal) close();
    });

    // Controles +/- de cantidad
    document.querySelectorAll('.btn-cant').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.getElementById('modalCantidad');
            let v = parseInt(input.value) || 1;
            v = btn.dataset.action === 'mas' ? v + 1 : Math.max(1, v - 1);
            input.value = v;
        });
    });

    document.getElementById('agregarProducto').addEventListener('click', () => {
        const cant = parseInt(document.getElementById('modalCantidad').value) || 1;
        const notas = document.getElementById('modalNotas').value.trim();
        agregarAlCarrito(POS.productoEnEdicion, cant, notas);
        close();
    });
}

function abrirModalProducto(prod) {
    if (!prod) return;
    POS.productoEnEdicion = prod;

    document.getElementById('modalProdNombre').textContent = prod.nombre;
    document.getElementById('modalProdPrecio').textContent =
        Utils.formatearMoneda(prod.precio);
    document.getElementById('modalCantidad').value = 1;
    document.getElementById('modalNotas').value = '';

    document.getElementById('modalProducto').classList.add('open');
}

/* ------------------------------------------------------------
   CARRITO
   ------------------------------------------------------------ */
function agregarAlCarrito(prod, cantidad = 1, notas = '') {
    // Si mismo producto + mismas notas → sumar cantidad
    const existente = POS.carrito.find(i =>
        i.id === prod.id && i.notas === notas
    );

    if (existente) {
        existente.cantidad += cantidad;
    } else {
        POS.carrito.push({
            id: prod.id,
            nombre: prod.nombre,
            precio: prod.precio,
            cantidad,
            notas,
        });
    }

    renderCarrito();
    actualizarBadgeCarrito();
    Utils.mostrarToast(`${prod.nombre} agregado`, 'success');
}

function renderCarrito() {
    const cont = document.getElementById('carritoItems');

    if (!POS.carrito.length) {
        cont.innerHTML = '<p class="carrito-vacio">Aún no hay productos.</p>';
        actualizarTotales();
        return;
    }

    cont.innerHTML = POS.carrito.map((item, idx) => `
        <div class="carrito-item" data-idx="${idx}">
            <div class="ci-header">
                <div class="ci-nombre">${item.nombre}</div>
                <button class="ci-eliminar" data-idx="${idx}"
                        aria-label="Eliminar">🗑️</button>
            </div>
            ${item.notas
                ? `<div class="ci-notas">📝 ${item.notas}</div>`
                : ''}
            <div class="ci-controls">
                <div class="ci-cantidad">
                    <button data-accion="menos" data-idx="${idx}">−</button>
                    <span>${item.cantidad}</span>
                    <button data-accion="mas" data-idx="${idx}">+</button>
                </div>
                <div class="ci-precio">
                    ${Utils.formatearMoneda(item.precio * item.cantidad)}
                </div>
            </div>
        </div>
    `).join('');

    // Listeners
    cont.querySelectorAll('[data-accion]').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = Number(btn.dataset.idx);
            const delta = btn.dataset.accion === 'mas' ? 1 : -1;
            cambiarCantidad(idx, delta);
        });
    });

    cont.querySelectorAll('.ci-eliminar').forEach(btn => {
        btn.addEventListener('click', () => {
            eliminarDelCarrito(Number(btn.dataset.idx));
        });
    });

    actualizarTotales();
}

function cambiarCantidad(idx, delta) {
    const item = POS.carrito[idx];
    if (!item) return;
    item.cantidad += delta;
    if (item.cantidad <= 0) {
        POS.carrito.splice(idx, 1);
    }
    renderCarrito();
    actualizarBadgeCarrito();
}

function eliminarDelCarrito(idx) {
    POS.carrito.splice(idx, 1);
    renderCarrito();
    actualizarBadgeCarrito();
    Utils.mostrarToast('Producto eliminado', 'info');
}

function actualizarTotales() {
    // El total ya incluye IVA
    const total = POS.carrito.reduce(
        (s, i) => s + i.precio * i.cantidad, 0
    );
    
    // En Paraguay el IVA es del 10%. 
    // Formula para extraer el IVA de un total: (Total / 1.10) * 0.10
    const subtotal = Math.round(total / 1.10);
    const impuesto = total - subtotal;

    document.getElementById('subtotal').textContent = Utils.formatearMoneda(subtotal);
    document.getElementById('impuesto').textContent = Utils.formatearMoneda(impuesto);
    document.getElementById('total').textContent    = Utils.formatearMoneda(total);
    document.getElementById('totalCobro').textContent = Utils.formatearMoneda(total);

    return { subtotal, impuesto, total };
}

function actualizarBadgeCarrito() {
    const totalItems = POS.carrito.reduce((s, i) => s + i.cantidad, 0);
    const badge = document.getElementById('badgeCarrito');
    if (badge) badge.textContent = totalItems;
}

/* ------------------------------------------------------------
   ACCIONES DEL CARRITO
   ------------------------------------------------------------ */
function initAccionesCarrito() {
    document.getElementById('btnLimpiarCarrito')
        .addEventListener('click', () => {
            if (!POS.carrito.length) return;
            if (confirm('¿Vaciar todo el pedido actual?')) {
                POS.carrito = [];
                renderCarrito();
                actualizarBadgeCarrito();
            }
        });

    document.getElementById('btnEnviarCocina')
        .addEventListener('click', enviarACocina);

    document.getElementById('btnCobrar')
        .addEventListener('click', abrirModalCobro);
}

/* ------------------------------------------------------------
   ENVÍO A COCINA
   ------------------------------------------------------------ */
async function enviarACocina() {
    if (!POS.carrito.length) {
        Utils.mostrarToast('El carrito está vacío', 'error');
        return;
    }

    if (!POS.mesaActual) {
        Utils.mostrarToast('Selecciona una mesa primero', 'error');
        abrirModalMesa();
        return;
    }

    const payload = {
        mesa_id: POS.mesaActual.id,
        items: POS.carrito.map(i => ({
            producto_id: i.id,
            cantidad: i.cantidad,
            notas: i.notas,
        })),
    };

    try {
        await PedidosAPI.crear(payload);
        Utils.mostrarToast('✅ Pedido enviado a cocina', 'success');
        POS.carrito = [];
        renderCarrito();
        actualizarBadgeCarrito();
    } catch (e) {
        Utils.mostrarToast(e.message || 'No se pudo enviar el pedido', 'error');
    }
}

/* ------------------------------------------------------------
   MODAL SELECCIÓN DE MESA
   ------------------------------------------------------------ */
function initModalMesa() {
    const modal = document.getElementById('modalMesa');
    document.getElementById('btnCambiarMesa')
        .addEventListener('click', abrirModalMesa);
    document.getElementById('cerrarModalMesa')
        .addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('open');
    });
}

async function abrirModalMesa() {
    const modal = document.getElementById('modalMesa');
    const body  = document.getElementById('modalMesaBody');
    body.innerHTML = '<p>Cargando mesas...</p>';
    modal.classList.add('open');

    let mesas;
    try {
        mesas = await MesasAPI.listar('todas');
    } catch (e) {
        mesas = getMesasDemo();
    }

    body.innerHTML = `
        <div class="mesas-modal-grid">
            ${mesas.map(m => `
                <button class="mesa-mini" data-id="${m.id}"
                        data-estado="${m.estado}">
                    #${m.numero}
                </button>
            `).join('')}
        </div>
    `;

    body.querySelectorAll('.mesa-mini').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = Number(btn.dataset.id);
            const numero = btn.textContent.replace('#', '').trim();
            POS.mesaActual = { id, numero };
            actualizarMesaUI();
            modal.classList.remove('open');
        });
    });
}

function actualizarMesaUI() {
    const el = document.getElementById('mesaActiva');
    el.textContent = POS.mesaActual
        ? `Mesa #${POS.mesaActual.numero}`
        : '— Sin asignar —';
}

/* ------------------------------------------------------------
   MODAL DE COBRO
   ------------------------------------------------------------ */
function initModalCobro() {
    const modal = document.getElementById('modalCobro');
    document.getElementById('cerrarModalCobro')
        .addEventListener('click', () => modal.classList.remove('open'));
    document.getElementById('cancelarCobro')
        .addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('open');
    });

    // Métodos de pago
    document.querySelectorAll('.metodo').forEach(m => {
        m.addEventListener('click', () => {
            document.querySelectorAll('.metodo')
                .forEach(x => x.classList.remove('active'));
            m.classList.add('active');
            POS.metodoPago = m.dataset.metodo;
            calcularCambio();
        });
    });

    document.getElementById('montoRecibido')
        .addEventListener('input', calcularCambio);

    document.getElementById('confirmarCobro')
        .addEventListener('click', confirmarCobro);
}

function abrirModalCobro() {
    if (!POS.carrito.length) {
        Utils.mostrarToast('No hay productos para cobrar', 'error');
        return;
    }
    const { total } = actualizarTotales();
    document.getElementById('montoRecibido').value = '';
    document.getElementById('cambioCobro').textContent = '$0';
    document.getElementById('modalCobro').classList.add('open');
}

function calcularCambio() {
    const { total } = actualizarTotales();
    const recibido = Number(document.getElementById('montoRecibido').value) || 0;
    const cambio = Math.max(0, recibido - total);
    document.getElementById('cambioCobro').textContent =
        Utils.formatearMoneda(cambio);
}

async function confirmarCobro() {
    if (!POS.mesaActual) return;

    const { total } = actualizarTotales();
    const recibido = Number(document.getElementById('montoRecibido').value) || 0;

    if (POS.metodoPago === 'efectivo' && recibido < total) {
        Utils.mostrarToast('Monto recibido insuficiente', 'error');
        return;
    }

    try {
        const res = await API.post(`/pedidos/mesa/${POS.mesaActual.id}/cobrar`, {
            metodo: POS.metodoPago,
            monto: POS.metodoPago === 'efectivo' ? recibido : total
        });
        
        Utils.mostrarToast('💰 Cobro registrado con éxito', 'success');
        
        // 🔥 PREPARAR LA IMPRESIÓN
        generarEImprimirTicket(res.factura);

    } catch (e) {
        console.error(e);
        Utils.mostrarToast(e.message || 'Error al cobrar', 'error');
        return;
    }

    // Limpiar estado
    POS.carrito = [];
    POS.mesaActual = null;
    renderCarrito();
    actualizarBadgeCarrito();
    actualizarMesaUI();
    document.getElementById('modalCobro').classList.remove('open');
}

/* ------------------------------------------------------------
   IMPRESIÓN DE TICKET
   ------------------------------------------------------------ */
function generarEImprimirTicket(fact) {
    const ticketDiv = document.getElementById('ticket-print');
    
    // Calcular el IVA (10% incluido)
    const total = fact.total;
    const subtotal = Math.round(total / 1.10);
    const iva = total - subtotal;

    // Generar filas de productos
    let itemsHtml = '';
    fact.items.forEach(it => {
        itemsHtml += `
            <tr>
                <td style="width: 15%">${it.cantidad}x</td>
                <td style="width: 55%; padding-right: 5px;">${it.nombre}</td>
                <td class="text-right" style="width: 30%">₲ ${it.subtotal.toLocaleString('es-PY')}</td>
            </tr>
        `;
    });

    // Formatear montos
    const fTotal = total.toLocaleString('es-PY');
    const fSubtotal = subtotal.toLocaleString('es-PY');
    const fIva = iva.toLocaleString('es-PY');
    const fRecibido = fact.monto_recibido.toLocaleString('es-PY');
    const fCambio = fact.cambio.toLocaleString('es-PY');

    // Plantilla del ticket
    ticketDiv.innerHTML = `
        <div class="text-center bold">
            <h2 style="margin:0; font-size: 16px;">${fact.empresa_nombre}</h2>
            <p style="margin:2px 0;">RUC: ${fact.empresa_ruc}</p>
            <p style="margin:2px 0;">${fact.empresa_dir}</p>
        </div>
        
        <div class="divider"></div>
        
        <div class="text-left" style="font-size: 11px;">
            <p style="margin:2px 0;"><b>FACTURA:</b> ${fact.factura_num}</p>
            <p style="margin:2px 0;"><b>FECHA:</b> ${fact.fecha}</p>
            <p style="margin:2px 0;"><b>MESA:</b> ${fact.mesa}</p>
            <p style="margin:2px 0;"><b>MESERO:</b> ${fact.mesero}</p>
        </div>
        
        <div class="divider"></div>
        
        <table class="table-items">
            <thead>
                <tr>
                    <th class="text-left" colspan="2">PRODUCTO</th>
                    <th class="text-right">TOTAL</th>
                </tr>
            </thead>
            <tbody>
                ${itemsHtml}
            </tbody>
        </table>
        
        <div class="divider"></div>
        
        <div class="text-right">
            <p style="margin:2px 0;"><b>Subtotal:</b> ₲ ${fSubtotal}</p>
            <p style="margin:2px 0;"><b>IVA (10%):</b> ₲ ${fIva}</p>
            <p style="margin:2px 0; font-size: 14px;"><b>TOTAL:</b> ₲ ${fTotal}</p>
        </div>
        
        <div class="divider"></div>
        
        <div class="text-left" style="font-size: 11px;">
            <p style="margin:2px 0;"><b>Método:</b> ${fact.metodo_pago}</p>
            ${fact.metodo_pago === 'EFECTIVO' ? `
                <p style="margin:2px 0;"><b>Recibido:</b> ₲ ${fRecibido}</p>
                <p style="margin:2px 0;"><b>Cambio:</b> ₲ ${fCambio}</p>
            ` : ''}
        </div>
        
        <div class="divider"></div>
        
        <div class="text-center" style="margin-top: 10px; font-size: 10px;">
            <p>¡Gracias por su visita!</p>
            <p>www.barstock.com.py</p>
        </div>
    `;

    // Lanzar la ventana de impresión del navegador
    setTimeout(() => {
        window.print();
    }, 200);
}

/* ------------------------------------------------------------
   CARRITO FLOTANTE (móvil)
   ------------------------------------------------------------ */
function initCarritoFlotante() {
    const btnFlotante = document.getElementById('btnCarritoFlotante');
    const carrito     = document.getElementById('posCarrito');
    const btnCerrar   = document.getElementById('btnCerrarCarrito');

    btnFlotante?.addEventListener('click', () => {
        carrito.classList.add('open');
    });
    btnCerrar?.addEventListener('click', () => {
        carrito.classList.remove('open');
    });
}

/* ------------------------------------------------------------
   UTILIDADES
   ------------------------------------------------------------ */
function capitalizar(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

/* ------------------------------------------------------------
   DATOS DEMO (eliminar cuando el backend esté listo)
   ------------------------------------------------------------ */
function getCartaDemo() {
    return [
        { id: 1,  nombre: 'Ceviche mixto',       precio: 32000, categoria: 'entradas',  descripcion: 'Pescado y camarón', destacado: true },
        { id: 2,  nombre: 'Carpaccio de res',    precio: 28000, categoria: 'entradas',  descripcion: 'Láminas finas con parmesano' },
        { id: 3,  nombre: 'Lomo al trapo',       precio: 45000, categoria: 'carnes',    descripcion: 'Con sal parrillera', destacado: true },
        { id: 4,  nombre: 'Punta de anca',       precio: 42000, categoria: 'carnes',    descripcion: 'Término al gusto' },
        { id: 5,  nombre: 'Salmón grillé',       precio: 48000, categoria: 'pescados',  descripcion: 'Con vegetales al vapor' },
        { id: 6,  nombre: 'Cazuela de mariscos', precio: 52000, categoria: 'pescados',  descripcion: 'Con coco y hierbas' },
        { id: 7,  nombre: 'Pasta carbonara',     precio: 34000, categoria: 'pastas' },
        { id: 8,  nombre: 'Lasaña boloñesa',     precio: 32000, categoria: 'pastas' },
        { id: 9,  nombre: 'Limonada de coco',    precio: 12000, categoria: 'bebidas',   destacado: true },
        { id: 10, nombre: 'Jugo natural',        precio:  9000, categoria: 'bebidas' },
        { id: 11, nombre: 'Cerveza artesanal',   precio: 15000, categoria: 'bebidas' },
        { id: 12, nombre: 'Postre tres leches',  precio: 15000, categoria: 'postres' },
        { id: 13, nombre: 'Brownie con helado',  precio: 16000, categoria: 'postres' },
    ];
}

function getMesasDemo() {
    const estados = ['ocupada', 'pagada', 'reservada', 'libre'];
    return Array.from({ length: 12 }, (_, i) => ({
        id: i + 1,
        numero: i + 1,
        estado: estados[i % 4],
    }));
}