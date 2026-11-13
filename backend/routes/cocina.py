from flask import Blueprint, jsonify, request, g
from models import db
from models.pedido import Pedido
from models.mesa import Mesa
from services.inventario_service import descontar_por_pedido

cocina_bp = Blueprint('cocina', __name__)


# ============================================================
#  LISTAR COMANDAS ACTIVAS
# ============================================================
@cocina_bp.route('/comandas', methods=['GET'])
def listar_comandas():
    """
    Devuelve las comandas activas para el monitor de cocina.
    Filtra por estados que aún no han sido servidos.
    """
    estados_activos = ['pendiente', 'en_preparacion', 'listo']

    pedidos = Pedido.query.filter(
        Pedido.estado.in_(estados_activos)
    ).order_by(Pedido.created_at.asc()).all()

    return jsonify([p.to_dict_cocina() for p in pedidos])


# ============================================================
#  CAMBIAR ESTADO DE UNA COMANDA
# ============================================================
@cocina_bp.route('/comandas/<int:pedido_id>/estado', methods=['POST'])
def cambiar_estado(pedido_id):
    from app import socketio
    from socket_events import emitir_comanda_actualizada

    pedido = Pedido.query.get_or_404(pedido_id)
    data = request.get_json() or {}
    nuevo_estado = data.get('estado')

    estados_validos = ['pendiente', 'en_preparacion', 'listo', 'servido']
    if nuevo_estado not in estados_validos:
        return jsonify({'error': 'Estado inválido'}), 400

    estado_anterior = pedido.estado
    pedido.estado = nuevo_estado

    # 🔥 Si pasa a "servido" → descontar inventario
    if nuevo_estado == 'servido' and estado_anterior != 'servido':
        db.session.commit()

        # Descontar insumos por receta
        usuario_id = getattr(g, 'usuario', None)
        usuario_id = usuario_id.id if usuario_id else None

        try:
            resultado = descontar_por_pedido(
                pedido,
                usuario_id=usuario_id,
                socketio=socketio,
            )
            if not resultado['ok']:
                print(f'⚠️ No se pudo descontar inventario: '
                      f'{resultado.get("error")}')
        except Exception as e:
            print(f'❌ Error al descontar inventario: {e}')
    else:
        db.session.commit()

    # Notificar a las pantallas de cocina
    emitir_comanda_actualizada(socketio, pedido.to_dict_cocina())

    return jsonify(pedido.to_dict_cocina())