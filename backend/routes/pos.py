from flask import Blueprint, jsonify, request, g
from models import db
from models.pedido import Pedido, PedidoItem
from models.mesa import Mesa
from models.producto import Producto
from models.pago import Pago
from models.receta import Receta
from models.inventario import InventarioSucursal
from utils.auth_decorators import login_required, requiere_permiso
from datetime import datetime, timezone
import random

pos_bp = Blueprint('pos', __name__)
METODOS_PAGO = {'efectivo', 'tarjeta', 'transferencia'}


# ============================================================
#  LISTAR PRODUCTOS
# ============================================================

@pos_bp.route('/productos', methods=['GET'])
@login_required
def lista_productos():
    """Carta de la empresa con disponibilidad según stock de la sucursal."""
    empresa_id = g.usuario.empresa_id
    sucursal_id = g.usuario.sucursal_id

    prods = (Producto.query
             .filter_by(empresa_id=empresa_id, activo=True)
             .order_by(Producto.categoria, Producto.nombre).all())
    if not prods:
        return jsonify([])

    # 2 consultas en total en vez de N+1
    recetas_por_prod = {}
    for r in Receta.query.filter(
            Receta.producto_id.in_([p.id for p in prods])).all():
        recetas_por_prod.setdefault(r.producto_id, []).append(r)

    stock_suc = {}
    if sucursal_id:
        stock_suc = {
            reg.insumo_id: float(reg.stock_actual or 0)
            for reg in InventarioSucursal.query.filter_by(sucursal_id=sucursal_id)
        }

    def stock_de(insumo):
        if sucursal_id:
            return stock_suc.get(insumo.id, 0.0)
        return float(insumo.stock_actual or 0)

    resultado = []
    for prod in prods:
        faltante = []
        for r in recetas_por_prod.get(prod.id, []):
            if r.opcional or not r.insumo:
                continue
            necesita = float(r.cantidad_con_merma())
            tiene = stock_de(r.insumo)
            if tiene < necesita:
                faltante.append({
                    'insumo': r.insumo.nombre,
                    'necesita': necesita,
                    'tiene': tiene,
                    'unidad': r.insumo.unidad,
                })
        d = prod.to_dict()
        d['disponible'] = not faltante
        d['faltante'] = faltante
        resultado.append(d)

    return jsonify(resultado)
# ============================================================
#  CREAR PEDIDO
# ============================================================
@pos_bp.route('', methods=['POST'])
@requiere_permiso('pos.pedido.crear')
def crear_pedido():
    from app import socketio
    from socket_events import emitir_nueva_comanda

    data = request.get_json() or {}
    mesa_id = data.get('mesa_id')
    items = data.get('items') or []
    if not mesa_id or not items:
        return jsonify({'error': 'mesa_id e items son obligatorios'}), 400

    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first()
    if not mesa:
        return jsonify({'error': 'Mesa no encontrada'}), 404

    pedido = Pedido(
        empresa_id=g.usuario.empresa_id,
        sucursal_id=mesa.sucursal_id,
        mesa_id=mesa.id,
        usuario_id=g.usuario.id,
        estado='pendiente',
        cerrado=False,
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0
    n_items = 0
    for item in items:
        try:
            cantidad = int(item.get('cantidad', 0))
        except (TypeError, ValueError):
            cantidad = 0
        if cantidad <= 0:
            continue

        # El producto DEBE ser de la misma empresa y estar activo
        prod = Producto.query.filter_by(
            id=item.get('producto_id'),
            empresa_id=g.usuario.empresa_id,
            activo=True,
        ).first()
        if not prod:
            continue

        db.session.add(PedidoItem(
            pedido_id=pedido.id,
            producto_id=prod.id,
            cantidad=cantidad,
            precio_unitario=prod.precio,   # el precio SIEMPRE viene del servidor
            notas=(item.get('notas') or '')[:255],
        ))
        total += float(prod.precio) * cantidad
        n_items += 1

    if n_items == 0:
        db.session.rollback()
        return jsonify({'error': 'Ningún item válido en el pedido'}), 400

    pedido.total = total
    mesa.estado = 'ocupada'
    if not mesa.mesero_id:
        mesa.mesero_id = g.usuario.id
    db.session.commit()

    try:
        emitir_nueva_comanda(socketio, pedido.to_dict_cocina(), pedido.empresa_id)
    except Exception as e:
        print(f'⚠️ No se pudo emitir WebSocket: {e}')

    return jsonify(pedido.to_dict()), 201

# ============================================================
#  ENVIAR A COCINA (opcional)
# ============================================================
@pos_bp.route('/<int:pedido_id>/enviar-cocina', methods=['POST'])
@requiere_permiso('pos.pedido.crear')
def enviar_cocina(pedido_id):
    pedido = Pedido.query.filter_by(
        id=pedido_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    pedido.estado = 'pendiente'
    db.session.commit()
    return jsonify({'ok': True, 'estado': pedido.estado})



# ============================================================
#  CONSUMO DE UNA MESA (para el modal de mesas)
# ============================================================
@pos_bp.route('/mesa/<int:mesa_id>/consumo', methods=['GET'])
@requiere_permiso('mesas.ver', 'pos.ver')
def consumo_mesa(mesa_id):
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    pedidos = Pedido.query.filter_by(
        mesa_id=mesa.id, empresa_id=g.usuario.empresa_id, cerrado=False
    ).all()

    items = []
    total = 0
    for p in pedidos:
        for it in p.items:
            items.append({
                'producto_id': it.producto_id,  
                'nombre': it.producto.nombre if it.producto else '',
                'cantidad': it.cantidad,
                'precio': float(it.precio_unitario),
                'notas': it.notas or '',
            })
            total += float(it.precio_unitario) * it.cantidad

    return jsonify({
        'mesa_id': mesa.id,
        'numero': mesa.numero,
        'estado': mesa.estado,
        'items': items,
        'total': total,
    })


# ============================================================
#  ABRIR MESA (para el botón "Abrir" en la pantalla de mesas)
# ============================================================
@pos_bp.route('/mesa/<int:mesa_id>/abrir', methods=['POST'])
@requiere_permiso('mesas.abrir')
def abrir_mesa(mesa_id):
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    if mesa.estado not in ('libre', 'reservada'):
        return jsonify({'error': f'La mesa está {mesa.estado}'}), 409
    mesa.estado = 'ocupada'
    mesa.mesero_id = g.usuario.id
    db.session.commit()
    return jsonify(mesa.to_dict())

# ============================================================
#  LIBERAR MESA (pasar de pagada a libre)
# ============================================================
@pos_bp.route('/mesa/<int:mesa_id>/liberar', methods=['POST'])
@requiere_permiso('mesas.abrir', 'mesas.cerrar')
def liberar_mesa(mesa_id):
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    if mesa.estado == 'ocupada':
        return jsonify({'error': 'La mesa tiene una cuenta abierta'}), 409
    mesa.estado = 'libre'
    mesa.mesero_id = None
    db.session.commit()
    return jsonify(mesa.to_dict())

@pos_bp.route('/mesa/<int:mesa_id>/cobrar', methods=['POST'])
@requiere_permiso('pos.cobrar', 'mesas.cerrar')
def cobrar_mesa(mesa_id):
    data = request.get_json() or {}
    metodo_pago = data.get('metodo', 'efectivo')
    if metodo_pago not in METODOS_PAGO:
        return jsonify({'error': 'Método de pago inválido'}), 400
    try:
        monto_recibido = float(data.get('monto', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Monto inválido'}), 400

    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    pedidos = Pedido.query.filter_by(
        mesa_id=mesa.id, empresa_id=g.usuario.empresa_id, cerrado=False
    ).all()
    if not pedidos:
        return jsonify({'error': 'No hay pedidos pendientes en esta mesa'}), 400

    total_cobrar = sum(float(p.total) for p in pedidos)
    if metodo_pago == 'efectivo' and monto_recibido < total_cobrar:
        return jsonify({'error': 'Monto recibido insuficiente'}), 400

    ahora = datetime.now(timezone.utc)
    
    # 2. Cerrar pedidos y generar los pagos
    for p in pedidos:
        p.cerrado = True
        p.fecha_cierre = ahora
        
        # Crear el registro de pago para cada pedido
        pago = Pago(
            empresa_id=g.usuario.empresa_id,
            sucursal_id=p.sucursal_id,
            pedido_id=p.id,
            metodo=metodo_pago,
            monto=p.total,
            factura_num=f"F-{random.randint(1000, 9999)}", # En producción usar un secuencial
            usuario_id=g.usuario.id,
            fecha=ahora
        )
        db.session.add(pago)
        
    # 3. Cambiar estado de la mesa
    mesa.estado = 'pagada'
    mesa.mesero_id = None
    db.session.commit()
    
    # 4. Armar la data de la factura para el frontend
    empresa = mesa.empresa if hasattr(mesa, 'empresa') else None
    # Obtenemos los items de todos los pedidos juntos
    items_ticket = []
    for p in pedidos:
        for item in p.items:
            items_ticket.append({
                'cantidad': item.cantidad,
                'nombre': item.producto.nombre,
                'precio': float(item.precio_unitario),
                'subtotal': float(item.precio_unitario) * item.cantidad
            })
            
    factura_data = {
        'empresa_nombre': "BARSTOCK", # O usar: empresa.nombre
        'empresa_ruc': "80012345-6",
        'empresa_dir': "Av. Principal 123, Asunción",
        'factura_num': f"001-001-{random.randint(1, 999999):07d}",
        'fecha': ahora.strftime('%d/%m/%Y %H:%M'),
        'mesa': mesa.numero,
        'mesero': g.usuario.nombre,
        'items': items_ticket,
        'total': total_cobrar,
        'metodo_pago': metodo_pago.upper(),
        'monto_recibido': monto_recibido,
        'cambio': max(0, monto_recibido - total_cobrar) if metodo_pago == 'efectivo' else 0
    }
    
    return jsonify({'ok': True, 'factura': factura_data})

