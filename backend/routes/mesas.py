from flask import Blueprint, jsonify, request
from models import db
from models.mesa import Mesa
from models.pedido import Pedido

mesas_bp = Blueprint('mesas', __name__)

@mesas_bp.route('', methods=['GET'])
def listar_mesas():
    filtro = request.args.get('filtro', 'todas')
    query = Mesa.query
    if filtro == 'abiertas':
        query = query.filter(Mesa.estado == 'ocupada')
    elif filtro == 'pagadas':
        query = query.filter(Mesa.estado == 'pagada')
    elif filtro == 'reservadas':
        query = query.filter(Mesa.estado == 'reservada')
    return jsonify([m.to_dict() for m in query.all()])


@mesas_bp.route('/<int:mesa_id>/consumo', methods=['GET'])
def consumo_mesa(mesa_id):
    pedidos = Pedido.query.filter_by(mesa_id=mesa_id, cerrado=False).all()
    items = [i.to_dict() for p in pedidos for i in p.items]
    total = sum(i['precio'] * i['cantidad'] for i in items)
    return jsonify({'mesa': mesa_id, 'items': items, 'total': total})