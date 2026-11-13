const RECETAS = {
    platoActual: null,
    insumos: [],
    platos: []
};

document.addEventListener('DOMContentLoaded', async () => {
    await cargarInsumos();
    await cargarPlatos();

    document.getElementById('buscarPlato').addEventListener('input', (e) => {
        filtrarPlatos(e.target.value.toLowerCase());
    });

    // Al cambiar el select de insumo, mostrar su unidad (g, ml, etc.)
    document.getElementById('selectInsumo').addEventListener('change', (e) => {
        const id = Number(e.target.value);
        const insumo = RECETAS.insumos.find(i => i.id === id);
        document.getElementById('unidadInsumo').textContent = insumo ? insumo.unidad : '-';
    });

    document.getElementById('formInsumo').addEventListener('submit', agregarInsumo);
});

// --- CARGA DE DATOS ---
async function cargarInsumos() {
    try {
        RECETAS.insumos = await API.get('/inventario/insumos');
        const select = document.getElementById('selectInsumo');
        select.innerHTML = '<option value="">Seleccionar insumo...</option>' + 
            RECETAS.insumos.map(i => `<option value="${i.id}">${i.nombre} (${i.unidad})</option>`).join('');
    } catch (e) {
        Utils.mostrarToast('Error al cargar insumos', 'error');
    }
}

async function cargarPlatos() {
    try {
        RECETAS.platos = await API.get('/pedidos/productos');
        renderListaPlatos(RECETAS.platos);
    } catch (e) {
        Utils.mostrarToast('Error al cargar platos', 'error');
    }
}

function renderListaPlatos(platos) {
    const lista = document.getElementById('listaPlatos');
    if (!platos.length) {
        lista.innerHTML = '<li>No hay platos</li>';
        return;
    }

    lista.innerHTML = platos.map(p => `
        <li data-id="${p.id}" class="${RECETAS.platoActual === p.id ? 'active' : ''}">
            <div><strong>${p.nombre}</strong></div>
            <div style="font-size: 0.8rem; color: #666;">${p.categoria}</div>
        </li>
    `).join('');

    lista.querySelectorAll('li').forEach(li => {
        li.addEventListener('click', () => seleccionarPlato(Number(li.dataset.id)));
    });
}

function filtrarPlatos(texto) {
    const filtrados = RECETAS.platos.filter(p => p.nombre.toLowerCase().includes(texto));
    renderListaPlatos(filtrados);
}

// --- SELECCIÓN Y EDICIÓN ---
async function seleccionarPlato(id) {
    RECETAS.platoActual = id;
    const plato = RECETAS.platos.find(p => p.id === id);
    
    // Actualizar UI
    renderListaPlatos(RECETAS.platos); // Re-render para pintar el activo
    document.getElementById('editorVacio').style.display = 'none';
    document.getElementById('editorContenido').style.display = 'block';
    document.getElementById('tituloPlato').textContent = plato.nombre;
    document.getElementById('categoriaPlato').textContent = plato.categoria;

    await cargarReceta(id);
}

async function cargarReceta(platoId) {
    const tbody = document.getElementById('tablaIngredientes');
    tbody.innerHTML = '<tr><td colspan="5">Cargando...</td></tr>';

    try {
        const recetas = await API.get(`/recetas/producto/${platoId}`);
        
        if (!recetas.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#666;">Este plato no tiene receta asignada.</td></tr>';
            document.getElementById('costoTotalReceta').textContent = '₲ 0';
            return;
        }

        let costoTotal = 0;
        tbody.innerHTML = recetas.map(r => {
            const costoUnit = r.insumo.costo_unitario || 0;
            const costoTotalInsumo = r.cantidad_neta * costoUnit;
            costoTotal += costoTotalInsumo;

            return `
                <tr>
                    <td><strong>${r.insumo_nombre}</strong></td>
                    <td>${r.cantidad_neta} ${r.unidad}</td>
                    <td>${Utils.formatearMoneda(costoUnit)}</td>
                    <td>${Utils.formatearMoneda(costoTotalInsumo)}</td>
                    <td>
                        <button class="btn-eliminar" onclick="eliminarIngrediente(${r.id})">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');

        document.getElementById('costoTotalReceta').textContent = Utils.formatearMoneda(costoTotal);

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5">Error al cargar</td></tr>';
    }
}

// --- ACCIONES ---
async function agregarInsumo(e) {
    e.preventDefault();
    const insumoId = Number(document.getElementById('selectInsumo').value);
    const cantidad = Number(document.getElementById('inputCantidad').value);

    if (!insumoId || cantidad <= 0) return;

    try {
        await API.post(`/recetas/producto/${RECETAS.platoActual}`, {
            insumo_id: insumoId,
            cantidad: cantidad
        });
        Utils.mostrarToast('Insumo agregado', 'success');
        
        // Limpiar form
        document.getElementById('selectInsumo').value = '';
        document.getElementById('inputCantidad').value = '';
        document.getElementById('unidadInsumo').textContent = '-';
        
        // Recargar tabla
        await cargarReceta(RECETAS.platoActual);
    } catch (error) {
        Utils.mostrarToast('Error al guardar', 'error');
    }
}

async function eliminarIngrediente(recetaId) {
    if (!confirm('¿Quitar este insumo de la receta?')) return;
    try {
        await API.delete(`/recetas/${recetaId}`);
        Utils.toast('Insumo eliminado', 'info');
        await cargarReceta(RECETAS.platoActual);
    } catch (e) {
        Utils.mostrarToast('Error al eliminar', 'error');
    }
}