"""
Asigna recetas a todos los productos que no las tengan.
Uso:  py seed_recetas.py
"""

from decimal import Decimal
from app import create_app
from models import db
from models.producto import Producto
from models.insumo import Insumo
from models.receta import Receta


# Recetas genéricas por categoría (cantidades por unidad de insumo base)
RECETAS_POR_CATEGORIA = {
    'Entradas':  [('CAR-001', 120), ('VER-011', 60), ('ABR-051', 10)],
    'Carnes':    [('CAR-001', 300), ('VER-010', 200), ('ABR-051', 25)],
    'Pescados':  [('CAR-001', 250), ('VER-010', 150), ('ABR-051', 20)],
    'Pastas':    [('ABR-050', 200), ('CAR-002', 100), ('ABR-051', 15)],
    'Bebidas':   [('BEB-100', 1),   ('ABR-051', 5)],
    'Postres':   [('ABR-050', 100), ('CAR-002', 50)],
}

# Overrides específicos por nombre de producto
RECETAS_ESPECIFICAS = {
    'Lomo al trapo':     [('CAR-001', 300), ('VER-010', 200), ('ABR-051', 30)],
    'Punta de anca':     [('CAR-002', 300), ('VER-010', 200), ('ABR-051', 25)],
    'Salmón grillé':     [('CAR-001', 250), ('VER-010', 150), ('ABR-051', 20)],
    'Cerveza artesanal': [('BEB-100', 1)],
    'Ceviche mixto':     [('CAR-001', 200), ('VER-011', 80)],
    'Pasta carbonara':   [('ABR-050', 200), ('CAR-002', 100), ('ABR-051', 15)],
    'Limonada natural':  [('VER-011', 100), ('ABR-051', 5)],
    'Limonada de coco':  [('VER-011', 100), ('ABR-051', 5)],
    'Agua mineral':      [('BEB-100', 1)],
    'Lasaña boloñesa':   [('ABR-050', 180), ('CAR-002', 120), ('ABR-051', 20)],
}


def seed_recetas():
    app = create_app()
    with app.app_context():

        productos = Producto.query.all()
        insumos_map = {i.codigo: i for i in Insumo.query.all()}

        creadas = 0
        actualizadas = 0
        omitidas = 0

        for prod in productos:
            # Receta específica o por categoría
            receta = RECETAS_ESPECIFICAS.get(prod.nombre)
            if not receta:
                receta = RECETAS_POR_CATEGORIA.get(prod.categoria, [])
            if not receta:
                omitidas += 1
                continue

            # ¿Ya tiene receta?
            existentes = Receta.query.filter_by(producto_id=prod.id).count()

            if existentes > 0:
                # Actualizar cantidades si ya existe
                for cod, cant in receta:
                    insumo = insumos_map.get(cod)
                    if not insumo:
                        continue
                    r = Receta.query.filter_by(
                        producto_id=prod.id, insumo_id=insumo.id
                    ).first()
                    if r:
                        r.cantidad = Decimal(str(cant))
                        actualizadas += 1
                    else:
                        db.session.add(Receta(
                            producto_id=prod.id,
                            insumo_id=insumo.id,
                            cantidad=Decimal(str(cant)),
                        ))
                        creadas += 1
            else:
                # Crear receta nueva
                for cod, cant in receta:
                    insumo = insumos_map.get(cod)
                    if not insumo:
                        continue
                    db.session.add(Receta(
                        producto_id=prod.id,
                        insumo_id=insumo.id,
                        cantidad=Decimal(str(cant)),
                    ))
                    creadas += 1

        db.session.commit()

        print('=' * 60)
        print('✅ SEED DE RECETAS COMPLETADO')
        print('=' * 60)
        print(f'   Recetas creadas:      {creadas}')
        print(f'   Recetas actualizadas: {actualizadas}')
        print(f'   Productos omitidos:   {omitidas}')
        print(f'   Total productos:      {len(productos)}')
        print(f'   Total recetas en BD:  {Receta.query.count()}')


if __name__ == '__main__':
    seed_recetas()