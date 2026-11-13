// ============================================================
//  auth.js — Login, logout y manejo de sesión
// ============================================================

const Auth = (() => {

    const CLAVES = {
        TOKEN:   'pb_access_token',
        REFRESH: 'pb_refresh_token',
        USER:    'pb_usuario',
    };

    // ---------- Almacenamiento ----------
    function _storage(persistente = false) {
        return persistente ? localStorage : sessionStorage;
    }

    function guardarSesion({ access_token, refresh_token, usuario }, recordar = false) {
        const s = _storage(recordar);
        s.setItem(CLAVES.TOKEN,   access_token);
        s.setItem(CLAVES.REFRESH, refresh_token);
        s.setItem(CLAVES.USER,    JSON.stringify(usuario));
    }

    function actualizarToken(nuevoToken) {
        const s = localStorage.getItem(CLAVES.TOKEN) ? localStorage : sessionStorage;
        s.setItem(CLAVES.TOKEN, nuevoToken);
    }

    function getToken() {
        return localStorage.getItem(CLAVES.TOKEN)
            || sessionStorage.getItem(CLAVES.TOKEN);
    }

    function getRefreshToken() {
        return localStorage.getItem(CLAVES.REFRESH)
            || sessionStorage.getItem(CLAVES.REFRESH);
    }

    function getUsuario() {
        try {
            const raw = localStorage.getItem(CLAVES.USER)
                     || sessionStorage.getItem(CLAVES.USER);
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    }

    function limpiarSesion() {
        [localStorage, sessionStorage].forEach(s => {
            s.removeItem(CLAVES.TOKEN);
            s.removeItem(CLAVES.REFRESH);
            s.removeItem(CLAVES.USER);
        });
    }

    // ---------- Estado ----------
    function estaAutenticado() {
        const token = getToken();
        if (!token) return false;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.exp && payload.exp * 1000 < Date.now()) {
                limpiarSesion();
                return false;
            }
            return true;
        } catch {
            return false;
        }
    }

    // ---------- Permisos ----------
    function tienePermiso(codigo) {
        const u = getUsuario();
        if (!u) return false;
        if (u.roles?.includes('admin')) return true;
        return Array.isArray(u.permisos) && u.permisos.includes(codigo);
    }

    function tieneAlguno(codigos = []) {
        return codigos.some(tienePermiso);
    }

    function tieneRol(nombre) {
        const u = getUsuario();
        return u?.roles?.includes(nombre) || false;
    }

    // ---------- Refresh ----------
    async function intentarRefresh() {
        const refresh = getRefreshToken();
        if (!refresh) return false;

        try {
            const res = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refresh}`,
                },
            });
            if (!res.ok) return false;
            const data = await res.json();
            actualizarToken(data.access_token);
            return true;
        } catch {
            return false;
        }
    }

    // ---------- Logout ----------
    async function logout() {
        try { await API.post('/auth/logout', {}); } catch (_) {}
        limpiarSesion();
        window.location.href = window.APP_URLS.login;
    }

    function forzarLogout() {
        limpiarSesion();
        window.location.href = window.APP_URLS.login;
    }

    // ---------- API pública ----------
    return {
        guardarSesion,
        actualizarToken,
        getToken,
        getRefreshToken,
        getUsuario,
        limpiarSesion,
        estaAutenticado,
        tienePermiso,
        tieneAlguno,
        tieneRol,
        intentarRefresh,
        logout,
        forzarLogout,
    };
})();


// ============================================================
//  INICIALIZACIÓN DEL FORMULARIO DE LOGIN
//  Se ejecuta solo si estamos en la página de login
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;   // No estamos en login → no hacer nada

    // Si ya hay sesión → redirigir directo
    if (Auth.estaAutenticado()) {
        window.location.href = window.APP_URLS.index;
        return;
    }

    initLoginForm();
    initTogglePassword();
});

function initLoginForm() {
    const form = document.getElementById('loginForm');
    const btn  = document.getElementById('btnLogin');
    const err  = document.getElementById('authError');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        err.classList.remove('visible');
        err.textContent = '';

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const recordar = document.getElementById('recordarme')?.checked || false;

        if (!username || !password) return;

        btn.disabled = true;
        btn.classList.add('cargando');
        btn.textContent = 'Ingresando...';

        try {
            const data = await API.post('/auth/login', { username, password });

            console.log('✅ Login OK:', data.usuario.nombre);
            Auth.guardarSesion(data, recordar);

            // 👇 REDIRECT — aquí está la clave
            console.log('🔄 Redirigiendo a:', window.APP_URLS.index);
            window.location.href = window.APP_URLS.index;

        } catch (error) {
            console.error('❌ Error login:', error);
            err.textContent = error.message || 'No se pudo iniciar sesión';
            err.classList.add('visible');
            btn.disabled = false;
            btn.classList.remove('cargando');
            btn.textContent = 'Ingresar';
        }
    });
}

function initTogglePassword() {
    const btn   = document.getElementById('togglePassword');
    const input = document.getElementById('password');
    if (!btn || !input) return;

    btn.addEventListener('click', () => {
        const esPassword = input.type === 'password';
        input.type = esPassword ? 'text' : 'password';
        btn.textContent = esPassword ? '🙈' : '👁️';
    });
}