from flask import Blueprint, jsonify, request, g
from models import db
from models.pedido import Pedido
from services.inventario_service import descontar_por_pedido
from utils.auth_decorators import requiere_permiso

cocina_bp = Blueprint('cocina', __name__)

ESTADOS_ACTIVOS = ['pendiente', 'en_preparacion', 'listo']

# Transiciones permitidas (evita saltos raros y doble descuento de stock)
TRANSICIONES = {
    'pendiente':      {'en_preparacion'},
    'en_preparacion': {'listo'},
    'listo':          {'servido'},
    'servido':        set(),
}


@cocina_bp.route('/comandas', methods=['GET'])
@requiere_permiso('cocina.ver')
def listar_comandas():
    q = Pedido.query.filter(
        Pedido.empresa_id == g.usuario.empresa_id,
        Pedido.estado.in_(ESTADOS_ACTIVOS),
    )
    if g.usuario.sucursal_id:
        q = q.filter(Pedido.sucursal_id == g.usuario.sucursal_id)

    pedidos = q.order_by(Pedido.created_at.asc()).all()
    return jsonify([p.to_dict_cocina() for p in pedidos])


@cocina_bp.route('/comandas/<int:pedido_id>/estado', methods=['POST'])
@requiere_permiso('cocina.estado')
def cambiar_estado(pedido_id):
    from app import socketio
    from socket_events import emitir_comanda_actualizada

    pedido = Pedido.query.filter_by(
        id=pedido_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    nuevo_estado = (request.get_json() or {}).get('estado')
    if nuevo_estado not in TRANSICIONES:
        return jsonify({'error': 'Estado inválido'}), 400

    estado_anterior = pedido.estado
    if nuevo_estado == estado_anterior:
        return jsonify(pedido.to_dict_cocina())   # idempotente
    if nuevo_estado not in TRANSICIONES.get(estado_anterior, set()):
        return jsonify({
            'error': f'No se puede pasar de {estado_anterior} a {nuevo_estado}'
        }), 409

    pedido.estado = nuevo_estado
    db.session.commit()

    if nuevo_estado == 'servido':
        try:
            resultado = descontar_por_pedido(
                pedido, usuario_id=g.usuario.id, socketio=socketio
            )
            if not resultado['ok']:
                print(f'⚠️ No se pudo descontar inventario: {resultado.get("error")}')
        except Exception as e:
            db.session.rollback()
            print(f'❌ Error al descontar inventario: {e}')

    emitir_comanda_actualizada(
        socketio, pedido.to_dict_cocina(), pedido.empresa_id
    )
    return jsonify(pedido.to_dict_cocina())