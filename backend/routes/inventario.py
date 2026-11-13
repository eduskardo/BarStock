from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func, or_
from models import db
from models.insumo import Insumo
from models.movimiento import Movimiento
from models.inventario import InventarioSucursal
from utils.auth_decorators import requiere_permiso
from services import inventario_service

inventario_bp = Blueprint('inventario', __name__)


# ============================================================
#  INSUMOS
# ============================================================
@inventario_bp.route('/insumos', methods=['GET'])
@requiere_permiso('inventario.ver')
def listar_insumos():
    q = Insumo.query.filter_by(
        empresa_id=g.usuario.empresa_id, activo=True
    )

    # Filtros
    categoria = request.args.get('categoria')
    if categoria: q = q.filter(Insumo.categoria == categoria)

    busqueda = request.args.get('q')
    if busqueda:
        like = f'%{busqueda}%'
        q = q.filter(or_(Insumo.nombre.ilike(like),
                         Insumo.codigo.ilike(like)))

    solo_bajo = request.args.get('bajo_minimo')
    if solo_bajo == 'true':
        q = q.filter(Insumo.stock_actual < Insumo.stock_minimo)

    insumos = q.order_by(Insumo.nombre).all()
    return jsonify([i.to_dict() for i in insumos])


@inventario_bp.route('/insumos', methods=['POST'])
@requiere_permiso('inventario.ajuste')
def crear_insumo():
    data = request.get_json() or {}
    if not data.get('nombre') or not data.get('unidad'):
        return jsonify({'error': 'Nombre y unidad son obligatorios'}), 400

    insumo = Insumo(
        empresa_id=g.usuario.empresa_id,
        codigo=data.get('codigo'),
        nombre=data['nombre'],
        categoria=data.get('categoria'),
        unidad=data['unidad'],
        costo_unitario=data.get('costo_unitario', 0),
        stock_minimo=data.get('stock_minimo', 0),
        stock_maximo=data.get('stock_maximo', 0),
        perecedero=data.get('perecedero', False),
    )
    db.session.add(insumo)
    db.session.commit()
    return jsonify(insumo.to_dict()), 201


@inventario_bp.route('/insumos/<int:iid>', methods=['PUT'])
@requiere_permiso('inventario.ajuste')
def editar_insumo(iid):
    insumo = Insumo.query.filter_by(
        id=iid, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    data = request.get_json() or {}
    for campo in ['codigo', 'nombre', 'categoria', 'unidad',
                  'costo_unitario', 'stock_minimo', 'stock_maximo',
                  'perecedero', 'activo']:
        if campo in data:
            setattr(insumo, campo, data[campo])

    db.session.commit()
    return jsonify(insumo.to_dict())


@inventario_bp.route('/insumos/<int:iid>', methods=['DELETE'])
@requiere_permiso('inventario.ajuste')
def eliminar_insumo(iid):
    insumo = Insumo.query.filter_by(
        id=iid, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    insumo.activo = False
    db.session.commit()
    return jsonify({'ok': True})


# ============================================================
#  MOVIMIENTOS (KARDEX)
# ============================================================
@inventario_bp.route('/movimientos', methods=['GET'])
@requiere_permiso('inventario.ver')
def listar_movimientos():
    q = Movimiento.query.filter_by(empresa_id=g.usuario.empresa_id)

    insumo_id = request.args.get('insumo_id')
    if insumo_id: q = q.filter(Movimiento.insumo_id == insumo_id)

    tipo = request.args.get('tipo')
    if tipo: q = q.filter(Movimiento.tipo == tipo)

    desde = request.args.get('desde')
    if desde:
        try:
            q = q.filter(Movimiento.fecha >= datetime.fromisoformat(desde))
        except: pass

    hasta = request.args.get('hasta')
    if hasta:
        try:
            q = q.filter(Movimiento.fecha <= datetime.fromisoformat(hasta))
        except: pass

    movs = q.order_by(Movimiento.fecha.desc()).limit(500).all()
    return jsonify([m.to_dict() for m in movs])


@inventario_bp.route('/movimientos/ingreso', methods=['POST'])
@requiere_permiso('inventario.movimiento')
def ingreso():
    data = request.get_json() or {}
    requeridos = ['insumo_id', 'sucursal_id', 'cantidad']
    for r in requeridos:
        if not data.get(r):
            return jsonify({'error': f'Campo {r} obligatorio'}), 400

    mov = inventario_service.registrar_ingreso(
        insumo_id=data['insumo_id'],
        sucursal_id=data['sucursal_id'],
        cantidad=data['cantidad'],
        costo_unitario=data.get('costo_unitario', 0),
        factura=data.get('factura'),
        proveedor_id=data.get('proveedor_id'),
        motivo=data.get('motivo', 'Compra'),
        usuario_id=g.usuario.id,
    )
    return jsonify(mov.to_dict()), 201


@inventario_bp.route('/movimientos/ajuste', methods=['POST'])
@requiere_permiso('inventario.ajuste')
def ajuste():
    data = request.get_json() or {}
    requeridos = ['insumo_id', 'sucursal_id', 'cantidad', 'tipo']
    for r in requeridos:
        if not data.get(r):
            return jsonify({'error': f'Campo {r} obligatorio'}), 400

    tipos_validos = ['ajuste_pos', 'ajuste_neg', 'merma']
    if data['tipo'] not in tipos_validos:
        return jsonify({'error': 'Tipo de ajuste inválido'}), 400

    mov = inventario_service.registrar_ajuste(
        insumo_id=data['insumo_id'],
        sucursal_id=data['sucursal_id'],
        cantidad=data['cantidad'],
        tipo=data['tipo'],
        motivo=data.get('motivo', ''),
        usuario_id=g.usuario.id,
    )
    return jsonify(mov.to_dict()), 201


# ============================================================
#  ALERTAS Y DASHBOARD
# ============================================================
@inventario_bp.route('/alertas', methods=['GET'])
@requiere_permiso('inventario.ver')
def alertas():
    insumos = Insumo.query.filter(
        Insumo.empresa_id == g.usuario.empresa_id,
        Insumo.activo == True,
        Insumo.stock_actual < Insumo.stock_minimo,
    ).order_by(Insumo.nombre).all()

    return jsonify([i.to_dict() for i in insumos])


@inventario_bp.route('/resumen', methods=['GET'])
@requiere_permiso('inventario.ver')
def resumen():
    empresa_id = g.usuario.empresa_id

    total_insumos = Insumo.query.filter_by(
        empresa_id=empresa_id, activo=True
    ).count()

    bajo_minimo = Insumo.query.filter(
        Insumo.empresa_id == empresa_id,
        Insumo.activo == True,
        Insumo.stock_actual < Insumo.stock_minimo,
    ).count()

    valor_total = db.session.query(
        func.coalesce(
            func.sum(Insumo.stock_actual * Insumo.costo_unitario), 0
        )
    ).filter(
        Insumo.empresa_id == empresa_id, Insumo.activo == True
    ).scalar()

    # Movimientos últimos 30 días
    hace_30 = datetime.utcnow() - timedelta(days=30)
    movs_30 = Movimiento.query.filter(
        Movimiento.empresa_id == empresa_id,
        Movimiento.fecha >= hace_30,
    ).count()

    return jsonify({
        'total_insumos': total_insumos,
        'bajo_minimo': bajo_minimo,
        'valor_total': float(valor_total or 0),
        'movimientos_30d': movs_30,
    })