from flask import session
from flask_jwt_extended import decode_token
from flask_socketio import SocketIO, emit, join_room
from models.usuario import Usuario


def sala(nombre, empresa_id):
    return f'{nombre}:{empresa_id}'


def _usuario_desde_token(auth):
    token = auth.get('token') if isinstance(auth, dict) else None
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get('type') != 'access':
            return None
        usuario = Usuario.query.get(int(payload['sub']))
    except Exception:
        return None
    return usuario if usuario and usuario.activo else None


def _usuario_actual():
    uid = session.get('user_id')
    if not uid:
        return None
    u = Usuario.query.get(uid)
    return u if u and u.activo else None


def register_socket_events(socketio: SocketIO):

    @socketio.on('connect')
    def on_connect(auth=None):
        usuario = _usuario_desde_token(auth)
        if not usuario:
            return False          # rechaza la conexión
        session['user_id'] = usuario.id
        emit('bienvenida', {'msg': 'Conectado al servidor'})

    @socketio.on('disconnect')
    def on_disconnect():
        pass

    def _unirse(nombre, permiso):
        usuario = _usuario_actual()
        if not usuario or not usuario.tiene_permiso(permiso):
            emit('error_permiso', {'sala': nombre})
            return
        join_room(sala(nombre, usuario.empresa_id))
        emit('unido', {'sala': nombre})

    @socketio.on('unirse_cocina')
    def on_unirse_cocina():
        _unirse('cocina', 'cocina.ver')

    @socketio.on('unirse_pos')
    def on_unirse_pos():
        _unirse('pos', 'pos.ver')

    @socketio.on('unirse_inventario')
    def on_unirse_inventario():
        _unirse('inventario', 'inventario.ver')


# ---------- Emisores (siempre por empresa) ----------
def emitir_nueva_comanda(socketio, comanda_dict, empresa_id):
    socketio.emit('nueva_comanda', comanda_dict, room=sala('cocina', empresa_id))


def emitir_comanda_actualizada(socketio, comanda_dict, empresa_id):
    socketio.emit('comanda_actualizada', comanda_dict, room=sala('cocina', empresa_id))


def emitir_comanda_eliminada(socketio, comanda_id, empresa_id):
    socketio.emit('comanda_eliminada', {'id': comanda_id}, room=sala('cocina', empresa_id))


def emitir_alerta_stock(socketio, alertas, empresa_id):
    socketio.emit('alerta_stock', {'alertas': alertas},
                  room=sala('inventario', empresa_id))