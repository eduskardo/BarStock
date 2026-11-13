from flask_socketio import SocketIO, emit, join_room


def register_socket_events(socketio: SocketIO):
    """Registra los eventos de WebSocket para cocina y POS."""

    @socketio.on('connect')
    def on_connect():
        print('🔌 Cliente conectado')
        emit('bienvenida', {'msg': 'Conectado al servidor'})

    @socketio.on('disconnect')
    def on_disconnect():
        print('❌ Cliente desconectado')

    @socketio.on('unirse_cocina')
    def on_unirse_cocina():
        join_room('cocina')
        print('👨‍🍳 Cliente unido a la sala COCINA')
        emit('unido', {'sala': 'cocina'})

    @socketio.on('unirse_pos')
    def on_unirse_pos():
        join_room('pos')
        print('🧾 Cliente unido a la sala POS')
        emit('unido', {'sala': 'pos'})

    @socketio.on('unirse_inventario')
    def on_unirse_inventario():
        join_room('inventario')
        print('📦 Cliente unido a la sala INVENTARIO')
        emit('unido', {'sala': 'inventario'})
# ------------------------------------------------------------
# Funciones para emitir desde las rutas
# ------------------------------------------------------------
def emitir_nueva_comanda(socketio, comanda_dict):
    """Notifica a todas las pantallas de cocina."""
    socketio.emit('nueva_comanda', comanda_dict, room='cocina')


def emitir_comanda_actualizada(socketio, comanda_dict):
    socketio.emit('comanda_actualizada', comanda_dict, room='cocina')


def emitir_comanda_eliminada(socketio, comanda_id):
    socketio.emit('comanda_eliminada', {'id': comanda_id}, room='cocina')

