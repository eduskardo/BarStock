// ============================================================
//  main.js — Guard de sesión + navbar + utilidades
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

    // -------- GUARD GLOBAL --------
    // Si estamos en una página protegida y no hay sesión válida → login
    const paginaActual = window.location.pathname.split('/').pop() || 'index.html';
    const paginasPublicas = ['login.html'];

    if (!paginasPublicas.includes(paginaActual) && !Auth.estaAutenticado()) {
        window.location.href = 'login.html';
        return;
    }

    initNavbar();
    initLogout();
    aplicarPermisosUI();
});

/* ---------- Navbar hamburguesa ---------- */
function initNavbar() {
    const btn  = document.getElementById('hamburger');
    const menu = document.getElementById('navbarMenu');
    if (!btn || !menu) return;

    btn.addEventListener('click', () => {
        btn.classList.toggle('active');
        menu.classList.toggle('open');
    });

    menu.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', () => {
            btn.classList.remove('active');
            menu.classList.remove('open');
        });
    });
}

function initLogout() {
    const btn = document.getElementById('logoutBtn');
    if (!btn) return;
    btn.addEventListener('click', () => {
        if (confirm('¿Cerrar sesión?')) Auth.logout();
    });
}



/* ---------- Aplicar permisos a la UI ---------- */
function aplicarPermisosUI() {
    // Cualquier elemento con [data-permiso="codigo"] se oculta si no lo tiene
    document.querySelectorAll('[data-permiso]').forEach(el => {
        const codigos = el.dataset.permiso.split(',').map(s => s.trim());
        if (!Auth.tieneAlguno(codigos)) el.style.display = 'none';
    });
}

/* ---------- Utilidades globales ---------- */
const Utils = {
    formatearMoneda: (n) => {
        const num = Math.round(n || 0);
        return '₲ ' + num.toLocaleString('es-PY');
    },

    formatearHora: (iso) =>
        new Date(iso).toLocaleTimeString('es-CO', {
            hour: '2-digit', minute: '2-digit',
        }),

    mostrarToast: (msg, tipo = 'info') => {
        const toast = document.createElement('div');
        toast.className = `toast toast-${tipo}`;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },
};