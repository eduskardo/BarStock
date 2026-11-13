// ============================================================
//  usuarios.js — CRUD de usuarios (panel admin)
// ============================================================

const USUARIOS = {
    lista: [],
    roles: [],
    editando: null,
};

document.addEventListener('DOMContentLoaded', () => {
    // Solo usuarios con permiso pueden entrar aquí
    if (!Auth.tienePermiso('usuarios.ver')) {
        Utils.mostrarToast('Sin permiso para esta sección', 'error');
        setTimeout(() => window.location.href = 'index.html', 1500);
        return;
    }

    initModal();
    cargarRoles();
    cargarUsuarios();
});

/* ------------------------------------------------------------
   CARGA DE DATOS
   ------------------------------------------------------------ */
async function cargarRoles() {
    try {
        USUARIOS.roles = await UsuariosAPI.roles();
    } catch (e) {
        USUARIOS.roles = [
            { nombre: 'admin' },   { nombre: 'gerente' },
            { nombre: 'cajero' },  { nombre: 'mesero'  },
            { nombre: 'cocina' },  { nombre: 'bodega'  },
        ];
    }
    renderRolesCheckbox();
}

async function cargarUsuarios() {
    try {
        USUARIOS.lista = await UsuariosAPI.listar();
    } catch (e) {
        USUARIOS.lista = getUsuariosDemo();
    }
    renderTabla();
}

/* ------------------------------------------------------------
   TABLA
   ------------------------------------------------------------ */
function renderTabla() {
    const tbody = document.getElementById('tablaUsuariosBody');
    const puedeEditar   = Auth.tienePermiso('usuarios.editar');
    const puedeEliminar = Auth.tienePermiso('usuarios.eliminar');

    if (!USUARIOS.lista.length) {
        tbody.innerHTML = `
            <tr><td colspan="7" style="text-align:center;padding:2rem;color:#6B7280">
                No hay usuarios registrados
            </td></tr>`;
        return;
    }

    tbody.innerHTML = USUARIOS.lista.map(u => `
        <tr>
            <td><strong>${u.nombre}</strong></td>
            <td>${u.username}</td>
            <td>${u.email}</td>
            <td>${(u.roles || []).map(r =>
                `<span class="tag-rol">${r}</span>`).join('')}</td>
            <td>
                <span class="estado-pill ${u.activo ? 'activo' : 'inactivo'}">
                    ${u.activo ? 'Activo' : 'Inactivo'}
                </span>
            </td>
            <td>${u.ultimo_login
                ? new Date(u.ultimo_login).toLocaleString('es-CO')
                : '—'}</td>
            <td class="acciones-col">
                ${puedeEditar
                    ? `<button title="Editar" onclick="abrirEditar(${u.id})">✏️</button>`
                    : ''}
                ${puedeEliminar
                    ? `<button title="Desactivar" onclick="desactivarUsuario(${u.id})">🗑️</button>`
                    : ''}
            </td>
        </tr>
    `).join('');
}

/* ------------------------------------------------------------
   MODAL
   ------------------------------------------------------------ */
function initModal() {
    const modal = document.getElementById('modalUsuario');

    document.getElementById('btnNuevoUsuario')
        .addEventListener('click', abrirNuevo);

    document.getElementById('cerrarModalUsuario')
        .addEventListener('click', () => modal.classList.remove('open'));
    document.getElementById('cancelarUsuario')
        .addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('open');
    });

    document.getElementById('guardarUsuario')
        .addEventListener('click', guardarUsuario);
}

function renderRolesCheckbox() {
    const cont = document.getElementById('rolesCheckbox');
    cont.innerHTML = USUARIOS.roles.map(r => `
        <label class="rol-chip" data-rol="${r.nombre}">
            <input type="checkbox" value="${r.nombre}" hidden>
            ${r.nombre}
        </label>
    `).join('');

    cont.querySelectorAll('.rol-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('activo');
        });
    });
}

/* ------------------------------------------------------------
   ABRIR MODAL
   ------------------------------------------------------------ */
function abrirNuevo() {
    USUARIOS.editando = null;
    document.getElementById('modalUsuarioTitulo').textContent = 'Nuevo usuario';
    document.getElementById('formUsuario').reset();
    document.getElementById('userId').value = '';
    document.getElementById('uActivo').checked = true;
    document.getElementById('uPassword').placeholder = 'Mínimo 8 caracteres';
    limpiarRoles();
    document.getElementById('modalUsuario').classList.add('open');
}

function abrirEditar(id) {
    const u = USUARIOS.lista.find(x => x.id === id);
    if (!u) return;
    USUARIOS.editando = u;

    document.getElementById('modalUsuarioTitulo').textContent = 'Editar usuario';
    document.getElementById('userId').value     = u.id;
    document.getElementById('uNombre').value    = u.nombre;
    document.getElementById('uUsername').value  = u.username;
    document.getElementById('uEmail').value     = u.email;
    document.getElementById('uTelefono').value  = u.telefono || '';
    document.getElementById('uPassword').value  = '';
    document.getElementById('uPassword').placeholder =
        'Dejar vacío para no cambiar';
    document.getElementById('uActivo').checked  = u.activo;

    limpiarRoles();
    (u.roles || []).forEach(rol => {
        const chip = document.querySelector(`.rol-chip[data-rol="${rol}"]`);
        chip?.classList.add('activo');
    });

    document.getElementById('modalUsuario').classList.add('open');
}

function limpiarRoles() {
    document.querySelectorAll('.rol-chip').forEach(c =>
        c.classList.remove('activo'));
}

function obtenerRolesSeleccionados() {
    return Array.from(document.querySelectorAll('.rol-chip.activo'))
        .map(c => c.dataset.rol);
}

/* ------------------------------------------------------------
   GUARDAR
   ------------------------------------------------------------ */
async function guardarUsuario() {
    const id       = document.getElementById('userId').value;
    const nombre   = document.getElementById('uNombre').value.trim();
    const username = document.getElementById('uUsername').value.trim();
    const email    = document.getElementById('uEmail').value.trim();
    const telefono = document.getElementById('uTelefono').value.trim();
    const password = document.getElementById('uPassword').value;
    const activo   = document.getElementById('uActivo').checked;
    const roles    = obtenerRolesSeleccionados();

    if (!nombre || !username || !email) {
        Utils.mostrarToast('Completa los campos obligatorios', 'error');
        return;
    }

    if (!id && password.length < 8) {
        Utils.mostrarToast('La contraseña debe tener al menos 8 caracteres', 'error');
        return;
    }

    const payload = { nombre, username, email, telefono, activo, roles };
    if (password) payload.password = password;

    try {
        if (id) {
            await UsuariosAPI.editar(id, payload);
            Utils.mostrarToast('Usuario actualizado', 'success');
        } else {
            await UsuariosAPI.crear(payload);
            Utils.mostrarToast('Usuario creado', 'success');
        }

        document.getElementById('modalUsuario').classList.remove('open');
        cargarUsuarios();
    } catch (e) {
        Utils.mostrarToast(e.message || 'Error al guardar', 'error');
    }
}

/* ------------------------------------------------------------
   DESACTIVAR
   ------------------------------------------------------------ */
async function desactivarUsuario(id) {
    if (!confirm('¿Desactivar este usuario?')) return;
    try {
        await UsuariosAPI.eliminar(id);
        Utils.mostrarToast('Usuario desactivado', 'success');
        cargarUsuarios();
    } catch (e) {
        Utils.mostrarToast(e.message || 'Error', 'error');
    }
}

/* ------------------------------------------------------------
   DATOS DEMO
   ------------------------------------------------------------ */
function getUsuariosDemo() {
    return [
        { id: 1, nombre: 'Administrador', username: 'admin',
          email: 'admin@rest.com', roles: ['admin'], activo: true,
          ultimo_login: new Date().toISOString() },
        { id: 2, nombre: 'Ana Gómez', username: 'ana',
          email: 'ana@rest.com', roles: ['mesero'], activo: true },
        { id: 3, nombre: 'Luis Pérez', username: 'luis',
          email: 'luis@rest.com', roles: ['cajero'], activo: true },
        { id: 4, nombre: 'Chef Carlos', username: 'carlos',
          email: 'carlos@rest.com', roles: ['cocina'], activo: true },
        { id: 5, nombre: 'Ex-empleado', username: 'juan',
          email: 'juan@rest.com', roles: ['mesero'], activo: false },
    ];
}