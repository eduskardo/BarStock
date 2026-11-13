"""
Genera movimientos de inventario para pedidos históricos que no los tienen.
Uso:  py backfill_movimientos.py
"""

from decimal import Decimal
from datetime import timedelta
from app import create_app
from models import db
from models.pedido import Pedido
from models.receta import Receta
from models.insumo import Insumo
from models.movimiento import Movimiento


def backfill():
    app = create_app()
    with app.app_context():

        # Pedidos cerrados que NO tengan movimientos asociados
        pedidos = Pedido.query.filter_by(cerrado=True).all()
        print(f'📦 Procesando {len(pedidos)} pedidos cerrados...')

        total_movs = 0
        insumos_afectados = set()

        for pedido in pedidos:
            # ¿Ya tiene movimientos?
            existe = Movimiento.query.filter_by(
                referencia_id=pedido.id,
                referencia_tipo='pedido',
            ).first()
            if existe:
                continue

            sucursal_id = pedido.sucursal_id
            fecha = pedido.fecha_cierre or pedido.created_at

            for item in pedido.items:
                recetas = Receta.query.filter_by(
                    producto_id=item.producto_id
                ).all()

                for r in recetas:
                    insumo = r.insumo
                    if not insumo:
                        continue

                    cantidad = Decimal(str(r.cantidad_con_merma())) \
                               * Decimal(str(item.cantidad))

                    # Estado previo del stock (simulado hacia atrás)
                    stock_actual = Decimal(str(insumo.stock_actual or 0))
                    stock_antes = stock_actual
                    stock_despues = max(
                        Decimal('0'), stock_antes - cantidad
                    )

                    mov = Movimiento(
                        empresa_id=insumo.empresa_id,
                        sucursal_id=sucursal_id,
                        insumo_id=insumo.id,
                        tipo='egreso',
                        cantidad=cantidad,
                        stock_antes=stock_antes,
                        stock_despues=stock_despues,
                        costo_unitario=Decimal(str(insumo.costo_unitario or 0)),
                        costo_total=cantidad * Decimal(str(insumo.costo_unitario or 0)),
                        motivo=f'Venta: {item.producto.nombre} (x{item.cantidad})',
                        referencia_id=pedido.id,
                        referencia_tipo='pedido',
                        fecha=fecha,
                    )
                    db.session.add(mov)
                    total_movs += 1
                    insumos_afectados.add(insumo.id)

        db.session.commit()

        print('=' * 60)
        print('✅ BACKFILL COMPLETADO')
        print('=' * 60)
        print(f'   Movimientos creados:     {total_movs}')
        print(f'   Insumos afectados:       {len(insumos_afectados)}')
        print(f'   Total movimientos en BD: {Movimiento.query.count()}')


if __name__ == '__main__':
    backfill()