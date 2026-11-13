from flask import Blueprint, jsonify, request, g
from models import db
from models.pedido import Pedido, PedidoItem
from models.mesa import Mesa
from models.producto import Producto
from utils.auth_decorators import login_required
from datetime import datetime, timezone
from models.pago import Pago
from models.receta import Receta
from models.insumo import Insumo
from models.inventario import InventarioSucursal
import random

pos_bp = Blueprint('pos', __name__)


# ============================================================
#  LISTAR PRODUCTOS
# ============================================================

@pos_bp.route('/productos', methods=['GET'])
def lista_productos():
    """Devuelve la carta activa con validación de stock en tiempo real."""
    prods = Producto.query.filter_by(activo=True).all()
    resultado = []
    
    for prod in prods:
        prod_dict = prod.to_dict()
        
        # Evaluar si hay stock para al menos 1 unidad de este producto
        recetas = Receta.query.filter_by(producto_id=prod.id).all()
        disponible = True
        faltante = []
        
        for r in recetas:
            if r.opcional: 
                continue
            
            insumo = r.insumo
            if not insumo: 
                continue
                
            cantidad_necesaria = float(r.cantidad_con_merma())
            
            # Buscar stock real en la sucursal (asumiendo sucursal_id = 1 para pruebas)
            # En producción, obtenemos la sucursal del g.usuario.sucursal_id
            sucursal_id = 1 
            reg = InventarioSucursal.query.filter_by(
                insumo_id=insumo.id, sucursal_id=sucursal_id
            ).first()
            
            stock_actual = float(reg.stock_actual) if reg else 0.0
            
            if stock_actual < cantidad_necesaria:
                disponible = False
                faltante.append({
                    'insumo': insumo.nombre,
                    'necesita': cantidad_necesaria,
                    'tiene': stock_actual,
                    'unidad': insumo.unidad
                })
                
        prod_dict['disponible'] = disponible
        prod_dict['faltante'] = faltante
        resultado.append(prod_dict)
        
    return jsonify(resultado)

# ============================================================
#  CREAR PEDIDO
# ============================================================
@pos_bp.route('', methods=['POST'])
@login_required
def crear_pedido():
    """Crea un pedido, sus items, marca la mesa ocupada y notifica a cocina."""
    from app import socketio
    from socket_events import emitir_nueva_comanda

    data = request.get_json() or {}
    mesa_id = data.get('mesa_id')
    items = data.get('items', [])

    if not mesa_id or not items:
        return jsonify({'error': 'mesa_id e items son obligatorios'}), 400

    # Verificar que la mesa existe y pertenece a la empresa del usuario
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first()
    if not mesa:
        return jsonify({'error': 'Mesa no encontrada'}), 404

    # Crear el pedido con TODOS los campos obligatorios
    pedido = Pedido(
        empresa_id=g.usuario.empresa_id,
        sucursal_id=mesa.sucursal_id,
        mesa_id=mesa_id,
        usuario_id=g.usuario.id,
        estado='pendiente',
        cerrado=False,
    )
    db.session.add(pedido)
    db.session.flush()   # Para obtener pedido.id

    # Agregar items
    total = 0
    for item in items:
        prod = Producto.query.get(item['producto_id'])
        if not prod:
            continue
        cantidad = int(item['cantidad'])
        pi = PedidoItem(
            pedido_id=pedido.id,
            producto_id=prod.id,
            cantidad=cantidad,
            precio_unitario=prod.precio,
            notas=item.get('notas', ''),
        )
        total += float(prod.precio) * cantidad
        db.session.add(pi)

    pedido.total = total

    # Marcar la mesa como ocupada
    mesa.estado = 'ocupada'

    db.session.commit()

    # 🔔 Notificar a las pantallas de cocina en vivo
    try:
        comanda_dict = pedido.to_dict_cocina()
        emitir_nueva_comanda(socketio, comanda_dict)
    except Exception as e:
        print(f'⚠️ No se pudo emitir WebSocket: {e}')

    return jsonify(pedido.to_dict()), 201


# ============================================================
#  ENVIAR A COCINA (opcional)
# ============================================================
@pos_bp.route('/<int:pedido_id>/enviar-cocina', methods=['POST'])
@login_required
def enviar_cocina(pedido_id):
    """Marca el pedido como enviado a cocina (compatibilidad)."""
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = 'pendiente'   # o 'en_cocina' según tu flujo
    db.session.commit()
    return jsonify({'ok': True, 'estado': pedido.estado})


# ============================================================
#  CONSUMO DE UNA MESA (para el modal de mesas)
# ============================================================
@pos_bp.route('/mesa/<int:mesa_id>/consumo', methods=['GET'])
@login_required
def consumo_mesa(mesa_id):
    """Devuelve el consumo actual de una mesa."""
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    pedidos = Pedido.query.filter_by(
        mesa_id=mesa_id, cerrado=False
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
@login_required
def abrir_mesa(mesa_id):
    """Marca una mesa como ocupada."""
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    mesa.estado = 'ocupada'
    mesa.mesero_id = g.usuario.id
    db.session.commit()
    return jsonify(mesa.to_dict())

# ============================================================
#  LIBERAR MESA (pasar de pagada a libre)
# ============================================================
@pos_bp.route('/mesa/<int:mesa_id>/liberar', methods=['POST'])
@login_required
def liberar_mesa(mesa_id):
    mesa = Mesa.query.filter_by(
        id=mesa_id, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    
    # Solo se pueden liberar mesas pagadas o reservadas
    mesa.estado = 'libre'
    mesa.mesero_id = None
    db.session.commit()
    
    return jsonify(mesa.to_dict())

from datetime import datetime, timezone

@pos_bp.route('/mesa/<int:mesa_id>/cobrar', methods=['POST'])
@login_required
def cobrar_mesa(mesa_id):
    data = request.get_json() or {}
    metodo_pago = data.get('metodo', 'efectivo')
    monto_recibido = float(data.get('monto', 0))
    
    mesa = Mesa.query.filter_by(id=mesa_id, empresa_id=g.usuario.empresa_id).first_or_404()
    
    # 1. Buscar todos los pedidos abiertos de esta mesa
    pedidos = Pedido.query.filter_by(mesa_id=mesa_id, cerrado=False).all()
    if not pedidos:
        return jsonify({'error': 'No hay pedidos pendientes en esta mesa'}), 400
        
    total_cobrar = sum(float(p.total) for p in pedidos)
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

