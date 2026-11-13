from models import db
from models.insumo import Insumo
from models.receta import Receta
from models.empresa import Empresa
from models.producto import Producto


def seed_inventario_demo(db):
    """Carga insumos y recetas de ejemplo si la empresa no tiene ninguno."""
    empresa = Empresa.query.first()
    if not empresa:
        return
    if Insumo.query.filter_by(empresa_id=empresa.id).count() > 0:
        return

    insumos_data = [
        ('CAR-001', 'Lomo de res',      'Carnes',    'g',  45,  3000, 10000),
        ('CAR-002', 'Punta de anca',    'Carnes',    'g',  38,  2500, 8000),
        ('VER-010', 'Papa criolla',     'Verduras',  'g',  4,   2500, 15000),
        ('VER-011', 'Tomate chonto',    'Verduras',  'g',  3,   2000, 10000),
        ('BEB-100', 'Cerveza artesanal','Bebidas',   'und', 6500, 12, 48),
        ('ABR-050', 'Arroz',            'Abarrotes', 'g',  3,   5000, 50000),
        ('ABR-051', 'Aceite de oliva',  'Abarrotes', 'ml', 25,  500,  5000),
    ]

    insumos = {}
    for cod, nom, cat, und, costo, minimo, maximo in insumos_data:
        i = Insumo(
            empresa_id=empresa.id,
            codigo=cod, nombre=nom, categoria=cat,
            unidad=und, costo_unitario=costo,
            stock_minimo=minimo, stock_maximo=maximo,
            stock_actual=maximo,
        )
        db.session.add(i)
        insumos[cod] = i
    db.session.flush()

    # Recetas de ejemplo
    recetas = {
        'Lomo al trapo':  [('CAR-001', 300), ('ABR-051', 30), ('VER-010', 200)],
        'Punta de anca':  [('CAR-002', 300), ('ABR-051', 25)],
        'Cerveza artesanal': [('BEB-100', 1)],
    }

    for prod_nombre, componentes in recetas.items():
        prod = Producto.query.filter_by(
            empresa_id=empresa.id, nombre=prod_nombre
        ).first()
        if not prod:
            continue
        for cod_insumo, cant in componentes:
            insumo = insumos.get(cod_insumo)
            if insumo:
                db.session.add(Receta(
                    producto_id=prod.id,
                    insumo_id=insumo.id,
                    cantidad=cant,
                ))

    db.session.commit()
    print('✅ Inventario demo cargado')