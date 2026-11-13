"""
Servicio de reportes y análisis comercial.
Todas las funciones respetan multiempresa (empresa_id) y opcionalmente sucursal_id.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy import func, and_, case
from models import db
from models.pedido import Pedido, PedidoItem
from models.pago import Pago
from models.producto import Producto
from models.receta import Receta
from models.insumo import Insumo
from models.usuario import Usuario
from models.mesa import Mesa
from models.sucursal import Sucursal
from models.movimiento import Movimiento


# ============================================================
#  HELPERS
# ============================================================
def _rango(desde=None, hasta=None):
    """Normaliza un rango de fechas (por defecto: últimos 30 días)."""
    if not hasta:
        hasta = datetime.utcnow().replace(hour=23, minute=59, second=59)
    else:
        hasta = _parse_fecha(hasta).replace(hour=23, minute=59, second=59)

    if not desde:
        desde = (hasta - timedelta(days=29)).replace(hour=0, minute=0, second=0)
    else:
        desde = _parse_fecha(desde).replace(hour=0, minute=0, second=0)

    return desde, hasta


def _parse_fecha(v):
    if isinstance(v, (datetime, date)):
        return datetime(v.year, v.month, v.day)
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(str(v), fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _base_query(empresa_id, sucursal_id=None):
    """Query base de pedidos entregados/pagados."""
    q = Pedido.query.filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)
    return q


# ============================================================
#  1. KPIs PRINCIPALES (DASHBOARD)
# ============================================================
def kpis_principales(empresa_id, desde=None, hasta=None, sucursal_id=None):
    """
    Devuelve los KPIs del período y la comparativa con el período anterior
    de la misma duración.
    """
    desde, hasta = _rango(desde, hasta)
    duracion = hasta - desde

    # ── Período actual ──
    pedidos = _base_query(empresa_id, sucursal_id).filter(
        Pedido.fecha_cierre.between(desde, hasta)
    ).all()

    ventas_total = sum(float(p.total or 0) for p in pedidos)
    n_pedidos    = len(pedidos)
    ticket_prom  = ventas_total / n_pedidos if n_pedidos else 0

    # ── Período anterior (mismo rango) ──
    desde_ant = desde - duracion
    hasta_ant = desde - timedelta(seconds=1)

    pedidos_ant = _base_query(empresa_id, sucursal_id).filter(
        Pedido.fecha_cierre.between(desde_ant, hasta_ant)
    ).all()

    ventas_ant  = sum(float(p.total or 0) for p in pedidos_ant)
    n_ant       = len(pedidos_ant)
    ticket_ant  = ventas_ant / n_ant if n_ant else 0

    # ── Cálculo de food cost ──
    food_cost      = _food_cost_periodo(empresa_id, desde, hasta, sucursal_id)
    margen_bruto   = ventas_total - food_cost
    margen_pct     = (margen_bruto / ventas_total * 100) if ventas_total else 0

    # ── Food cost % del período anterior (para comparativa) ──
    food_cost_ant  = _food_cost_periodo(empresa_id, desde_ant, hasta_ant, sucursal_id)
    margen_ant     = ventas_ant - food_cost_ant
    margen_pct_ant = (margen_ant / ventas_ant * 100) if ventas_ant else 0

    def var_pct(actual, anterior):
        if not anterior: return 0
        return round((actual - anterior) / anterior * 100, 2)

    return {
        'periodo': {
            'desde': desde.isoformat(),
            'hasta': hasta.isoformat(),
        },
        'ventas': {
            'total': ventas_total,
            'variacion_pct': var_pct(ventas_total, ventas_ant),
        },
        'pedidos': {
            'total': n_pedidos,
            'variacion_pct': var_pct(n_pedidos, n_ant),
        },
        'ticket_promedio': {
            'valor': ticket_prom,
            'variacion_pct': var_pct(ticket_prom, ticket_ant),
        },
        'food_cost': {
            'total': food_cost,
            'porcentaje': round((food_cost / ventas_total * 100) if ventas_total else 0, 2),
        },
        'margen_bruto': {
            'total': margen_bruto,
            'porcentaje': round(margen_pct, 2),
            'variacion_pct': round(margen_pct - margen_pct_ant, 2),
        },
    }


def _food_cost_periodo(empresa_id, desde, hasta, sucursal_id=None):
    """
    Calcula el food cost real del período sumando los movimientos
    de egreso por venta, valorizados al costo unitario del insumo.
    """
    q = db.session.query(
        func.coalesce(func.sum(Movimiento.costo_total), 0)
    ).filter(
        Movimiento.empresa_id == empresa_id,
        Movimiento.tipo == 'egreso',
        Movimiento.fecha.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Movimiento.sucursal_id == sucursal_id)

    return float(q.scalar() or 0)


# ============================================================
#  2. VENTAS EN EL TIEMPO (gráfico de línea)
# ============================================================
def ventas_por_dia(empresa_id, desde=None, hasta=None, sucursal_id=None):
    """Serie diaria de ventas para gráfico de líneas."""
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        func.date(Pedido.fecha_cierre).label('dia'),
        func.count(Pedido.id).label('pedidos'),
        func.coalesce(func.sum(Pedido.total), 0).label('ventas'),
    ).filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(func.date(Pedido.fecha_cierre)) \
         .order_by(func.date(Pedido.fecha_cierre))

    return [
        {
            'fecha': row.dia.isoformat() if row.dia else None,
            'pedidos': int(row.pedidos),
            'ventas': float(row.ventas),
        }
        for row in q.all()
    ]


# ============================================================
#  3. VENTAS POR HORA (mapa de calor)
# ============================================================
def ventas_por_hora(empresa_id, desde=None, hasta=None, sucursal_id=None):
    """Distribución de ventas por hora del día (útil para staffing)."""
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        func.extract('hour', Pedido.fecha_cierre).label('hora'),
        func.count(Pedido.id).label('pedidos'),
        func.coalesce(func.sum(Pedido.total), 0).label('ventas'),
    ).filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(func.extract('hour', Pedido.fecha_cierre)) \
         .order_by(func.extract('hour', Pedido.fecha_cierre))

    return [
        {
            'hora': int(row.hora),
            'pedidos': int(row.pedidos),
            'ventas': float(row.ventas),
        }
        for row in q.all()
    ]


# ============================================================
#  4. TOP PRODUCTOS
# ============================================================
def top_productos(empresa_id, desde=None, hasta=None,
                  sucursal_id=None, limite=15):
    """
    Ranking de productos por unidades vendidas e ingresos.
    Calcula también margen unitario a partir de la receta.
    """
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Producto.id,
        Producto.nombre,
        Producto.categoria,
        Producto.precio,
        func.sum(PedidoItem.cantidad).label('unidades'),
        func.sum(PedidoItem.cantidad * PedidoItem.precio_unitario).label('ingresos'),
    ).join(
        PedidoItem, PedidoItem.producto_id == Producto.id
    ).join(
        Pedido, Pedido.id == PedidoItem.pedido_id
    ).filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(Producto.id) \
         .order_by(func.sum(PedidoItem.cantidad).desc()) \
         .limit(limite)

    resultados = []
    for row in q.all():
        # Costo de receta
        costo_unit = _costo_receta_producto(row.id)

        ingresos = float(row.ingresos or 0)
        unidades = int(row.unidades or 0)
        costo_total = costo_unit * unidades
        margen = ingresos - costo_total

        resultados.append({
            'producto_id': row.id,
            'nombre': row.nombre,
            'categoria': row.categoria,
            'precio': float(row.precio or 0),
            'unidades': unidades,
            'ingresos': ingresos,
            'costo_total': costo_total,
            'margen': margen,
            'margen_pct': round((margen / ingresos * 100) if ingresos else 0, 2),
            'food_cost_pct': round((costo_total / ingresos * 100) if ingresos else 0, 2),
        })

    return resultados


def _costo_receta_producto(producto_id):
    """Suma el costo de los insumos de la receta de un producto."""
    recetas = Receta.query.filter_by(producto_id=producto_id).all()
    total = Decimal('0')
    for r in recetas:
        if not r.insumo:
            continue
        cantidad = Decimal(str(r.cantidad_con_merma()))
        costo    = Decimal(str(r.insumo.costo_unitario or 0))
        total   += cantidad * costo
    return float(total)


# ============================================================
#  5. VENTAS POR CATEGORÍA
# ============================================================
def ventas_por_categoria(empresa_id, desde=None, hasta=None, sucursal_id=None):
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Producto.categoria,
        func.sum(PedidoItem.cantidad).label('unidades'),
        func.sum(PedidoItem.cantidad * PedidoItem.precio_unitario).label('ingresos'),
    ).join(PedidoItem, PedidoItem.producto_id == Producto.id) \
     .join(Pedido, Pedido.id == PedidoItem.pedido_id) \
     .filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(Producto.categoria) \
         .order_by(func.sum(PedidoItem.cantidad * PedidoItem.precio_unitario).desc())

    return [
        {
            'categoria': row.categoria or 'Sin categoría',
            'unidades': int(row.unidades or 0),
            'ingresos': float(row.ingresos or 0),
        }
        for row in q.all()
    ]


# ============================================================
#  6. VENTAS POR MESERO
# ============================================================
def ventas_por_mesero(empresa_id, desde=None, hasta=None, sucursal_id=None):
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Usuario.id,
        Usuario.nombre,
        func.count(Pedido.id).label('pedidos'),
        func.coalesce(func.sum(Pedido.total), 0).label('ventas'),
        func.coalesce(func.avg(Pedido.total), 0).label('ticket_prom'),
    ).join(Pedido, Pedido.usuario_id == Usuario.id) \
     .filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(Usuario.id) \
         .order_by(func.sum(Pedido.total).desc())

    return [
        {
            'usuario_id': row.id,
            'nombre': row.nombre,
            'pedidos': int(row.pedidos),
            'ventas': float(row.ventas),
            'ticket_promedio': float(row.ticket_prom),
        }
        for row in q.all()
    ]


# ============================================================
#  7. MÉTODOS DE PAGO
# ============================================================
def ventas_por_metodo_pago(empresa_id, desde=None, hasta=None, sucursal_id=None):
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Pago.metodo,
        func.count(Pago.id).label('transacciones'),
        func.coalesce(func.sum(Pago.monto), 0).label('total'),
    ).filter(
        Pago.empresa_id == empresa_id,
        Pago.fecha.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pago.sucursal_id == sucursal_id)

    q = q.group_by(Pago.metodo).order_by(func.sum(Pago.monto).desc())

    return [
        {
            'metodo': row.metodo,
            'transacciones': int(row.transacciones),
            'total': float(row.total),
        }
        for row in q.all()
    ]


# ============================================================
#  8. FOOD COST POR PRODUCTO (análisis de rentabilidad)
# ============================================================
def food_cost_por_producto(empresa_id, desde=None, hasta=None,
                           sucursal_id=None, limite=50):
    """
    Analiza cada producto vendido en el período y calcula:
    - costo unitario por receta
    - precio de venta
    - margen unitario y %
    - clasificación (estrella / vaca / incógnita / perro) según margen y volumen
    """
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Producto.id,
        Producto.nombre,
        Producto.categoria,
        Producto.precio,
        func.sum(PedidoItem.cantidad).label('unidades'),
        func.sum(PedidoItem.cantidad * PedidoItem.precio_unitario).label('ingresos'),
    ).join(PedidoItem, PedidoItem.producto_id == Producto.id) \
     .join(Pedido, Pedido.id == PedidoItem.pedido_id) \
     .filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(Producto.id).limit(limite)

    resultados = []
    for row in q.all():
        costo_unit = _costo_receta_producto(row.id)
        precio     = float(row.precio or 0)
        unidades   = int(row.unidades or 0)
        ingresos   = float(row.ingresos or 0)

        margen_unit    = precio - costo_unit
        margen_pct     = (margen_unit / precio * 100) if precio else 0
        food_cost_pct  = (costo_unit / precio * 100) if precio else 0
        margen_total   = ingresos - (costo_unit * unidades)

        resultados.append({
            'producto_id': row.id,
            'nombre': row.nombre,
            'categoria': row.categoria,
            'precio': precio,
            'costo_unitario': costo_unit,
            'margen_unitario': margen_unit,
            'margen_pct': round(margen_pct, 2),
            'food_cost_pct': round(food_cost_pct, 2),
            'unidades': unidades,
            'ingresos': ingresos,
            'margen_total': margen_total,
            'clasificacion': _clasificar_producto(margen_pct, unidades),
        })

    return resultados


def _clasificar_producto(margen_pct, unidades):
    """
    Matriz BCG simple:
    - Estrella:    alto margen + alto volumen
    - Vaca:        alto margen + bajo volumen
    - Incógnita:   bajo margen + alto volumen
    - Perro:       bajo margen + bajo volumen
    """
    alto_margen = margen_pct >= 60
    alto_volumen = unidades >= 20
    if alto_margen and alto_volumen:    return 'estrella'
    if alto_margen and not alto_volumen:return 'vaca'
    if not alto_margen and alto_volumen:return 'incognita'
    return 'perro'


# ============================================================
#  9. VENTAS POR SUCURSAL (multiempresa)
# ============================================================
def ventas_por_sucursal(empresa_id, desde=None, hasta=None):
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Sucursal.id,
        Sucursal.nombre,
        func.count(Pedido.id).label('pedidos'),
        func.coalesce(func.sum(Pedido.total), 0).label('ventas'),
    ).outerjoin(Pedido, and_(
        Pedido.sucursal_id == Sucursal.id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )).filter(Sucursal.empresa_id == empresa_id) \
     .group_by(Sucursal.id) \
     .order_by(func.coalesce(func.sum(Pedido.total), 0).desc())

    return [
        {
            'sucursal_id': row.id,
            'nombre': row.nombre,
            'pedidos': int(row.pedidos or 0),
            'ventas': float(row.ventas or 0),
        }
        for row in q.all()
    ]


# ============================================================
#  10. RENTABILIDAD POR MESA (mesas más productivas)
# ============================================================
def rentabilidad_por_mesa(empresa_id, desde=None, hasta=None, sucursal_id=None):
    desde, hasta = _rango(desde, hasta)

    q = db.session.query(
        Mesa.id,
        Mesa.numero,
        func.count(Pedido.id).label('turnos'),
        func.coalesce(func.sum(Pedido.total), 0).label('ventas'),
        func.coalesce(func.avg(Pedido.total), 0).label('ticket_prom'),
    ).join(Pedido, Pedido.mesa_id == Mesa.id) \
     .filter(
        Pedido.empresa_id == empresa_id,
        Pedido.cerrado == True,
        Pedido.fecha_cierre.between(desde, hasta),
    )
    if sucursal_id:
        q = q.filter(Pedido.sucursal_id == sucursal_id)

    q = q.group_by(Mesa.id).order_by(func.sum(Pedido.total).desc())

    return [
        {
            'mesa_id': row.id,
            'numero': row.numero,
            'turnos': int(row.turnos),
            'ventas': float(row.ventas),
            'ticket_promedio': float(row.ticket_prom),
        }
        for row in q.all()
    ]


# ============================================================
#  11. EXPORTACIÓN CSV
# ============================================================
def exportar_top_productos_csv(empresa_id, desde=None, hasta=None,
                               sucursal_id=None):
    """Devuelve string CSV de productos top."""
    data = top_productos(empresa_id, desde, hasta, sucursal_id, limite=200)

    lineas = ['Producto,Categoria,Precio,Costo Unitario,Margen Unit,FC %,Uds,Ingresos,Margen Total']
    for d in data:
        lineas.append(
            f'"{d["nombre"]}",'
            f'"{d["categoria"] or ""}",'
            f'{d["precio"]:.2f},'
            f'{d["costo_total"] / d["unidades"] if d["unidades"] else 0:.2f},'
            f'{(d["margen"] / d["unidades"]) if d["unidades"] else 0:.2f},'
            f'{d["food_cost_pct"]:.2f},'
            f'{d["unidades"]},'
            f'{d["ingresos"]:.2f},'
            f'{d["margen"]:.2f}'
        )
    return '\n'.join(lineas)


# ============================================================
#  12. CIERRE DE CAJA DIARIO
# ============================================================
def cierre_caja(empresa_id, fecha, sucursal_id=None):
    """
    Genera el resumen de cierre de caja para un día específico.
    Retorna totales agrupados por método de pago y el detalle de transacciones.
    """
    from datetime import datetime, timedelta
    
    # Parsear la fecha (YYYY-MM-DD)
    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
    inicio_dia = fecha_dt.replace(hour=0, minute=0, second=0)
    fin_dia = fecha_dt.replace(hour=23, minute=59, second=59)

    # Query base de pagos del día
    q = db.session.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.fecha.between(inicio_dia, fin_dia)
    )
    if sucursal_id:
        q = q.filter(Pago.sucursal_id == sucursal_id)

    pagos = q.order_by(Pago.fecha.asc()).all()

    # Totales por método
    total_efectivo = 0
    total_tarjeta = 0
    total_transferencia = 0
    detalle_transacciones = []

    for p in pagos:
        monto = float(p.monto or 0)
        if p.metodo == 'efectivo': total_efectivo += monto
        elif p.metodo == 'tarjeta': total_tarjeta += monto
        elif p.metodo == 'transferencia': total_transferencia += monto

        # Obtener datos del pedido y mesa
        pedido = p.pedido if hasattr(p, 'pedido') else None
        mesa_num = pedido.mesa.numero if pedido and pedido.mesa else 'N/A'
        
        detalle_transacciones.append({
            'hora': p.fecha.strftime('%H:%M'),
            'factura': p.factura_num or 'S/N',
            'mesa': mesa_num,
            'metodo': p.metodo.upper(),
            'monto': monto
        })

    total_general = total_efectivo + total_tarjeta + total_transferencia

    return {
        'fecha': fecha,
        'resumen': {
            'total_general': total_general,
            'efectivo': total_efectivo,
            'tarjeta': total_tarjeta,
            'transferencia': total_transferencia,
            'cantidad_pagos': len(pagos),
            'ticket_promedio': total_general / len(pagos) if pagos else 0
        },
        'transacciones': detalle_transacciones
    }