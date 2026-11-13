// ============================================================
//  api.js — Cliente API + manejo global de 401
// ============================================================

const API_BASE = '/api';

const API = {
    async request(endpoint, options = {}) {
        const headers = { 'Content-Type': 'application/json' };

        const token = Auth.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const config = {
            ...options,
            headers: { ...headers, ...(options.headers || {}) },
        };

        let res;
        try {
            res = await fetch(`${API_BASE}${endpoint}`, config);
        } catch (networkError) {
            throw new Error('No se puede conectar con el servidor');
        }

        // Si el token expiró → intenta refresh (una vez)
        if (res.status === 401 && !options._retry) {
            const refreshed = await Auth.intentarRefresh();
            if (refreshed) {
                return API.request(endpoint, { ...options, _retry: true });
            } else {
                Auth.forzarLogout();
                throw new Error('Sesión expirada');
            }
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Error ${res.status}`);
        }

        // Para DELETE y similares sin body
        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) return {};

        return res.json();
    },

    get:    (url)       => API.request(url, { method: 'GET' }),
    post:   (url, data) => API.request(url, { method: 'POST',   body: JSON.stringify(data || {}) }),
    put:    (url, data) => API.request(url, { method: 'PUT',    body: JSON.stringify(data || {}) }),
    delete: (url)       => API.request(url, { method: 'DELETE' }),
};

/* ------------------------------------------------------------
   Endpoints por módulo
   ------------------------------------------------------------ */
const MesasAPI = {
    listar:  (filtro = 'todas') => API.get(`/mesas?filtro=${filtro}`),
    detalle: (id)               => API.get(`/mesas/${id}/consumo`),
    abrir:   (id)               => API.post(`/mesas/${id}/abrir`),
    cerrar:  (id, pago)         => API.post(`/mesas/${id}/cerrar`, pago),
};

const PedidosAPI = {
    crear:        (data) => API.post('/pedidos', data),
    agregar:      (id, item) => API.post(`/pedidos/${id}/items`, item),
    enviarCocina: (id) => API.post(`/pedidos/${id}/enviar-cocina`),
};

const CocinaAPI = {
    listar:      () => API.get('/cocina/comandas'),
    cambiarEstado: (id, estado) =>
        API.post(`/cocina/comandas/${id}/estado`, { estado }),
};

const UsuariosAPI = {
    listar:   ()         => API.get('/usuarios'),
    obtener:  (id)       => API.get(`/usuarios/${id}`),
    crear:    (data)     => API.post('/usuarios', data),
    editar:   (id, data) => API.put(`/usuarios/${id}`, data),
    eliminar: (id)       => API.delete(`/usuarios/${id}`),
    roles:    ()         => API.get('/usuarios/roles'),
    permisos: ()         => API.get('/usuarios/permisos'),
};