document.addEventListener('DOMContentLoaded', () => {
    // Poner la fecha de hoy por defecto
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaCierre').value = hoy;

    cargarCierre(hoy);

    document.getElementById('btnBuscar').addEventListener('click', () => {
        const fecha = document.getElementById('fechaCierre').value;
        if (fecha) cargarCierre(fecha);
    });

    document.getElementById('btnImprimir').addEventListener('click', () => {
        window.print();
    });
});

async function cargarCierre(fecha) {
    try {
        const data = await API.get(`/reportes/cierre-caja?fecha=${fecha}`);
        renderCierre(data);
    } catch (e) {
        Utils.mostrarToast('Error al cargar cierre de caja', 'error');
    }
}

function renderCierre(data) {
    const { resumen, transacciones, fecha } = data;

    // Formatear fecha para el ticket impreso
    const fechaFormat = new Date(fecha + 'T12:00:00').toLocaleDateString('es-PY');
    document.getElementById('printFecha').textContent = fechaFormat;

    // Actualizar tarjetas
    document.getElementById('resEfectivo').textContent = Utils.formatearMoneda(resumen.efectivo);
    document.getElementById('resTarjeta').textContent = Utils.formatearMoneda(resumen.tarjeta);
    document.getElementById('resTransf').textContent = Utils.formatearMoneda(resumen.transferencia);
    document.getElementById('resTotal').textContent = Utils.formatearMoneda(resumen.total_general);
    document.getElementById('resCantidad').textContent = resumen.cantidad_pagos;

    // Actualizar tabla
    const tbody = document.getElementById('tablaCierre');
    if (transacciones.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">No hay movimientos en esta fecha.</td></tr>`;
        return;
    }

    tbody.innerHTML = transacciones.map(t => `
        <tr>
            <td>${t.hora}</td>
            <td>${t.factura}</td>
            <td>${t.mesa}</td>
            <td><span class="tag-tipo tag-${t.metodo.toLowerCase()}">${t.metodo}</span></td>
            <td class="num">${Utils.formatearMoneda(t.monto)}</td>
        </tr>
    `).join('');
}