from decimal import Decimal
from models import pedido
from models import db
from models.insumo import Insumo
from models.receta import Receta
from models.movimiento import Movimiento
from models.inventario import InventarioSucursal


# ============================================================
#  HELPERS
# ============================================================
def _get_stock_sucursal(insumo_id, sucursal_id):
    """Obtiene el registro de stock por sucursal (lo crea si no existe)."""
    reg = InventarioSucursal.query.filter_by(
        insumo_id=insumo_id, sucursal_id=sucursal_id
    ).first()
    if not reg:
        insumo = Insumo.query.get(insumo_id)
        reg = InventarioSucursal(
            insumo_id=insumo_id,
            sucursal_id=sucursal_id,
            stock_actual=0,
            stock_minimo=insumo.stock_minimo if insumo else 0,
        )
        db.session.add(reg)
        db.session.flush()
    return reg


def _aplicar_movimiento(
    insumo, sucursal_id, tipo, cantidad,
    motivo='', referencia_id=None, referencia_tipo=None,
    usuario_id=None, permitir_negativo=False,
):
    """
    Aplica un movimiento al inventario y deja registro en el kardex.
    Devuelve el Movimiento creado.
    """
    cantidad = Decimal(str(cantidad))

    if cantidad <= 0:
        raise ValueError('La cantidad debe ser positiva')

    reg = _get_stock_sucursal(insumo.id, sucursal_id)
    stock_antes = Decimal(str(reg.stock_actual or 0))

    # Signo del movimiento
    if tipo in ('ingreso', 'ajuste_pos'):
        stock_despues = stock_antes + cantidad
    else:  # egreso, ajuste_neg, merma, devolucion
        stock_despues = stock_antes - cantidad
        if stock_despues < 0 and not permitir_negativo:
            # Permite descontar pero deja el stock en 0 y registra el faltante
            stock_despues = Decimal('0')

    # Actualizar stock por sucursal
    reg.stock_actual = stock_despues
    reg.stock_minimo = reg.stock_minimo or insumo.stock_minimo

    # Actualizar stock consolidado del insumo (empresa)
    insumo.stock_actual = Decimal(str(insumo.stock_actual or 0))

    if tipo in ('ingreso', 'ajuste_pos'):
        insumo.stock_actual += cantidad
    else:
        insumo.stock_actual = max(
            Decimal('0'),
            insumo.stock_actual - cantidad
        )

    # Kardex
    mov = Movimiento(
        empresa_id=insumo.empresa_id,
        sucursal_id=sucursal_id,
        insumo_id=insumo.id,
        tipo=tipo,
        cantidad=cantidad,
        stock_antes=stock_antes,
        stock_despues=stock_despues,
        costo_unitario=Decimal(str(insumo.costo_unitario or 0)),
        costo_total=cantidad * Decimal(str(insumo.costo_unitario or 0)),
        motivo=motivo,
        referencia_id=referencia_id,
        referencia_tipo=referencia_tipo,
        usuario_id=usuario_id,
    )
    db.session.add(mov)

    return mov


# ============================================================
#  DESCUENTO AUTOMÁTICO POR RECETA
# ============================================================
def descontar_por_pedido(pedido, usuario_id=None, socketio=None):
    """
    Recorre los ítems del pedido, busca la receta de cada producto
    y descuenta del inventario los insumos correspondientes.

    Se llama cuando un pedido pasa a estado 'servido'.
    Devuelve un dict con el resumen de la operación.
    """
    if not pedido.mesa:
        return {'ok': False, 'error': 'Pedido sin mesa'}

    sucursal_id = pedido.mesa.sucursal_id or pedido.sucursal_id
    if not sucursal_id:
        return {'ok': False, 'error': 'Pedido sin sucursal'}

    alertas = []
    items_procesados = []

    for item in pedido.items:
        recetas = Receta.query.filter_by(producto_id=item.producto_id).all()

        # Producto sin receta → no descuenta (avisa al admin)
        if not recetas:
            items_procesados.append({
                'producto': item.producto.nombre,
                'descontado': False,
                'motivo': 'Sin receta definida',
            })
            continue

        for r in recetas:
            if r.opcional:
                continue

            cantidad_total = Decimal(str(r.cantidad_con_merma())) \
                             * Decimal(str(item.cantidad))

            insumo = r.insumo
            if not insumo:
                continue

            mov = _aplicar_movimiento(
                insumo=insumo,
                sucursal_id=sucursal_id,
                tipo='egreso',
                cantidad=cantidad_total,
                motivo=f'Venta: {item.producto.nombre} (x{item.cantidad})',
                referencia_id=pedido.id,
                referencia_tipo='pedido',
                usuario_id=usuario_id,
                permitir_negativo=False,
            )

            # ¿Bajó del mínimo?
            reg = _get_stock_sucursal(insumo.id, sucursal_id)
            if reg.bajo_minimo:
                alertas.append({
                    'insumo_id': insumo.id,
                    'insumo': insumo.nombre,
                    'stock_actual': float(reg.stock_actual),
                    'stock_minimo': float(reg.stock_minimo),
                    'unidad': insumo.unidad,
                })

        items_procesados.append({
            'producto': item.producto.nombre,
            'cantidad': item.cantidad,
            'descontado': True,
            'insumos_afectados': len(recetas),
        })

    db.session.commit()

    # Emitir alertas por WebSocket (solo a la empresa dueña del pedido)
    if socketio and alertas:
        from socket_events import emitir_alerta_stock
        emitir_alerta_stock(socketio, alertas, pedido.empresa_id)

    return {
        'ok': True,
        'pedido_id': pedido.id,
        'items': items_procesados,
        'alertas': alertas,
    }


# ============================================================
#  MOVIMIENTOS MANUALES
# ============================================================
def registrar_ingreso(insumo_id, sucursal_id, cantidad, costo_unitario,
                      factura=None, proveedor_id=None, motivo='Compra',
                      usuario_id=None):
    insumo = Insumo.query.get_or_404(insumo_id)

    # Actualiza costo unitario (promedio simple o último costo)
    if costo_unitario and float(costo_unitario) > 0:
        insumo.costo_unitario = Decimal(str(costo_unitario))

    mov = _aplicar_movimiento(
        insumo=insumo,
        sucursal_id = pedido.sucursal_id or (pedido.mesa.sucursal_id if pedido.mesa else None),
        tipo='ingreso',
        cantidad=cantidad,
        motivo=f'{motivo} · Factura {factura}' if factura else motivo,
        referencia_tipo='compra',
        usuario_id=usuario_id,
    )
    db.session.commit()
    return mov


def registrar_ajuste(insumo_id, sucursal_id, cantidad, tipo, motivo,
                     usuario_id=None):
    """tipo: 'ajuste_pos' o 'ajuste_neg' o 'merma'."""
    insumo = Insumo.query.get_or_404(insumo_id)
    mov = _aplicar_movimiento(
        insumo=insumo,
        sucursal_id=sucursal_id,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo or 'Ajuste manual',
        referencia_tipo='ajuste',
        usuario_id=usuario_id,
    )
    db.session.commit()
    return mov