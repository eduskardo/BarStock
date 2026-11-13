from flask import Blueprint, jsonify, request, g
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models import db
from models.mesa import Mesa
from models.pedido import Pedido
from utils.auth_decorators import requiere_permiso

mesas_bp = Blueprint('mesas', __name__)

FILTROS_ESTADO = {
    'abiertas': 'ocupada',
    'pagadas': 'pagada',
    'reservadas': 'reservada',
}


@mesas_bp.route('', methods=['GET'])
@requiere_permiso('mesas.ver')
def listar_mesas():
    empresa_id = g.usuario.empresa_id
    filtro = request.args.get('filtro', 'todas')
    # Por defecto, la sucursal del usuario
    sucursal_id = request.args.get('sucursal_id', type=int) or g.usuario.sucursal_id

    q = (Mesa.query
         .options(joinedload(Mesa.mesero))
         .filter(Mesa.empresa_id == empresa_id, Mesa.activa.is_(True)))

    if sucursal_id:
        q = q.filter(Mesa.sucursal_id == sucursal_id)
    if filtro in FILTROS_ESTADO:
        q = q.filter(Mesa.estado == FILTROS_ESTADO[filtro])

    mesas = q.order_by(Mesa.numero).all()

    # Total abierto por mesa en UNA sola consulta (el frontend usa m.total)
    totales = {}
    if mesas:
        filas = (db.session.query(
                    Pedido.mesa_id,
                    func.coalesce(func.sum(Pedido.total), 0))
                 .filter(Pedido.empresa_id == empresa_id,
                         Pedido.cerrado.is_(False),
                         Pedido.mesa_id.in_([m.id for m in mesas]))
                 .group_by(Pedido.mesa_id)
                 .all())
        totales = {mesa_id: float(total) for mesa_id, total in filas}

    resultado = []
    for m in mesas:
        d = m.to_dict()
        d['total'] = totales.get(m.id, 0.0)
        resultado.append(d)
    return jsonify(resultado)


@mesas_bp.route('/<int:mesa_id>/consumo', methods=['GET'])
@requiere_permiso('mesas.ver')
def consumo_mesa(mesa_id):
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    pedidos = Pedido.query.filter_by(
        mesa_id=mesa.id, empresa_id=g.usuario.empresa_id, cerrado=False
    ).all()
    items = [i.to_dict() for p in pedidos for i in p.items]
    total = sum(i['precio'] * i['cantidad'] for i in items)
    return jsonify({'mesa': mesa.id, 'items': items, 'total': total})