"""
Seed de datos DEMO para el sistema Proyecto Bar.

Crea:
    - 12 mesas con estados variados
    - 30 productos en 6 categorías
    - 5 usuarios (mesero, cajero, cocina, gerente, admin)
    - Recetas para los productos principales
    - 40 pedidos históricos de los últimos 30 días
    - Pagos asociados a cada pedido
    - Movimientos de inventario generados

Uso:
    cd backend
    py seed_demo.py
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from app import create_app
from models import db
from models.empresa import Empresa
from models.sucursal import Sucursal
from models.usuario import Usuario
from models.rol import Rol
from models.mesa import Mesa
from models.producto import Producto
from models.receta import Receta
from models.insumo import Insumo
from models.pedido import Pedido, PedidoItem
from models.pago import Pago
from models.movimiento import Movimiento


# ============================================================
#  PRODUCTOS
# ============================================================
PRODUCTOS = [
    # Entradas
    ('Ceviche mixto',        'Entradas',  32000, 'Pescado y camarón fresco'),
    ('Carpaccio de res',     'Entradas',  28000, 'Láminas finas con parmesano'),
    ('Tartar de atún',       'Entradas',  30000, 'Con aguacate y sésamo'),
    ('Croquetas de jamón',   'Entradas',  22000, 'Caseras, 6 unidades'),
    ('Ensalada César',       'Entradas',  24000, 'Con pollo grillé'),
    ('Empanadas mixtas',     'Entradas',  18000, '3 unidades surtidas'),

    # Carnes
    ('Lomo al trapo',        'Carnes',    45000, 'Con sal parrillera'),
    ('Punta de anca',        'Carnes',    42000, 'Término al gusto'),
    ('Churrasco',            'Carnes',    48000, 'Con chimichurri'),
    ('Costillas BBQ',        'Carnes',    44000, 'Con papas rústicas'),
    ('Filete mignon',        'Carnes',    55000, 'Con salsa de vino'),

    # Pescados
    ('Salmón grillé',        'Pescados',  48000, 'Con vegetales al vapor'),
    ('Trucha al ajillo',     'Pescados',  40000, 'Con arroz de coco'),
    ('Cazuela de mariscos',  'Pescados',  52000, 'Con coco y hierbas'),
    ('Corvina a la plancha', 'Pescados',  46000, 'Con ensalada fresca'),

    # Pastas
    ('Pasta carbonara',      'Pastas',    34000, 'Receta tradicional italiana'),
    ('Lasaña boloñesa',      'Pastas',    32000, 'Con queso gratinado'),
    ('Fettuccine alfredo',   'Pastas',    33000, 'Con pollo y champiñones'),
    ('Risotto de hongos',    'Pastas',    36000, 'Con parmesano'),

    # Bebidas
    ('Limonada de coco',     'Bebidas',   12000, 'Refrescante'),
    ('Limonada natural',     'Bebidas',    9000, 'Clásica'),
    ('Jugo natural',         'Bebidas',   10000, 'Fruta del día'),
    ('Cerveza artesanal',    'Bebidas',   15000, 'Rubia o negra'),
    ('Copa de vino tinto',   'Bebidas',   18000, 'Reserva'),
    ('Agua mineral',         'Bebidas',    6000, 'Con o sin gas'),
    ('Café espresso',        'Bebidas',    7000, 'Doble carga'),

    # Postres
    ('Postre tres leches',   'Postres',   15000, 'Clásico'),
    ('Brownie con helado',   'Postres',   16000, 'Con nueces'),
    ('Cheesecake de maracuyá','Postres',  17000, 'Fruta de la pasión'),
    ('Tiramisú',             'Postres',   18000, 'Receta italiana'),
]


# ============================================================
#  RECETAS (producto → insumos)
#  Usa los insumos del seed_inventario previo
# ============================================================
RECETAS = {
    'Lomo al trapo':        [('CAR-001', 300), ('ABR-051', 30), ('VER-010', 200)],
    'Punta de anca':        [('CAR-002', 300), ('ABR-051', 25)],
    'Cerveza artesanal':    [('BEB-100', 1)],
    'Ceviche mixto':        [('CAR-001', 200), ('VER-011', 80)],
    'Salmón grillé':        [('CAR-001', 250), ('VER-010', 150)],
    'Pasta carbonara':      [('ABR-050', 200), ('CAR-002', 100)],
}


# ============================================================
#  USUARIOS DEMO
# ============================================================
USUARIOS_DEMO = [
    ('Ana Gómez',    'ana',     'ana@rest.com',    'mesero',  'Mesero123!'),
    ('Luis Pérez',   'luis',    'luis@rest.com',   'cajero',  'Cajero123!'),
    ('Carla Ruiz',   'carla',   'carla@rest.com',  'mesero',  'Mesero123!'),
    ('Chef Carlos',  'carlos',  'carlos@rest.com', 'cocina',  'Cocina123!'),
    ('Diego Mora',   'diego',   'diego@rest.com',  'gerente', 'Gerente123!'),
]


# ============================================================
#  SEED
# ============================================================
def seed_demo():
    app = create_app()
    with app.app_context():

        empresa = Empresa.query.first()
        if not empresa:
            print('❌ No hay empresa. Corre primero app.py.')
            return

        sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        if not sucursal:
            print('❌ No hay sucursal.')
            return

        print(f'\n🌱 Cargando datos DEMO para {empresa.nombre}...')

        # ---------- 1. Mesas ----------
        if Mesa.query.filter_by(empresa_id=empresa.id).count() == 0:
            print('\n📋 Creando 12 mesas...')
            zonas = ['Salón', 'Terraza', 'Barra']
            for i in range(1, 13):
                m = Mesa(
                    empresa_id=empresa.id,
                    sucursal_id=sucursal.id,
                    numero=i,
                    capacidad=random.choice([2, 4, 4, 6]),
                    zona=zonas[i % 3],
                    estado='libre',
                )
                db.session.add(m)
            db.session.commit()
            print(f'   ✅ 12 mesas creadas')
        else:
            print(f'   ℹ️  Ya hay mesas')

        # ---------- 2. Productos ----------
        if Producto.query.filter_by(empresa_id=empresa.id).count() == 0:
            print('\n🍽️  Creando 30 productos...')
            for nombre, categoria, precio, desc in PRODUCTOS:
                p = Producto(
                    empresa_id=empresa.id,
                    nombre=nombre,
                    categoria=categoria,
                    precio=Decimal(str(precio)),
                    descripcion=desc,
                    activo=True,
                )
                db.session.add(p)
            db.session.commit()
            print(f'   ✅ 30 productos creados')
        else:
            print(f'   ℹ️  Ya hay productos')

        # ---------- 3. Usuarios ----------
        if Usuario.query.count() < 6:
            print('\n👥 Creando usuarios demo...')
            for nombre, username, email, rol_nombre, password in USUARIOS_DEMO:
                if Usuario.query.filter_by(username=username).first():
                    continue
                u = Usuario(
                    empresa_id=empresa.id,
                    sucursal_id=sucursal.id,
                    nombre=nombre,
                    email=email,
                    username=username,
                    activo=True,
                )
                u.set_password(password)
                rol = Rol.query.filter_by(nombre=rol_nombre).first()
                if rol:
                    u.roles.append(rol)
                db.session.add(u)
            db.session.commit()
            print(f'   ✅ Usuarios creados: ana, luis, carla, carlos, diego')
        else:
            print(f'   ℹ️  Ya hay usuarios')

        # ---------- 4. Recetas ----------
        print('\n📖 Creando recetas...')
        productos_map = {p.nombre: p for p in Producto.query.all()}
        insumos_map = {i.codigo: i for i in Insumo.query.all()}
        creadas = 0

        for prod_nombre, componentes in RECETAS.items():
            prod = productos_map.get(prod_nombre)
            if not prod:
                continue
            for cod_insumo, cant in componentes:
                insumo = insumos_map.get(cod_insumo)
                if not insumo:
                    continue
                if Receta.query.filter_by(
                    producto_id=prod.id, insumo_id=insumo.id
                ).first():
                    continue
                db.session.add(Receta(
                    producto_id=prod.id,
                    insumo_id=insumo.id,
                    cantidad=Decimal(str(cant)),
                ))
                creadas += 1
        db.session.commit()
        print(f'   ✅ {creadas} recetas creadas')

        # ---------- 5. Pedidos históricos ----------
        if Pedido.query.count() > 10:
            print(f'\n   ℹ️  Ya hay pedidos históricos')
            return

        print('\n📊 Generando 40 pedidos históricos (últimos 30 días)...')

        meseros = Usuario.query.filter(
            Usuario.roles.any(Rol.nombre.in_(['mesero', 'admin']))
        ).all() or [Usuario.query.first()]

        mesas = Mesa.query.all()
        productos = Producto.query.all()

        total_creados = 0
        for _ in range(40):
            # Fecha aleatoria en los últimos 30 días
            dias_atras = random.randint(0, 29)
            hora = random.choice([12, 13, 14, 19, 20, 21, 22])
            fecha = datetime.utcnow() - timedelta(days=dias_atras)
            fecha = fecha.replace(hour=hora, minute=random.randint(0, 59))

            pedido = Pedido(
                empresa_id=empresa.id,
                sucursal_id=sucursal.id,
                mesa_id=random.choice(mesas).id,
                usuario_id=random.choice(meseros).id,
                estado='servido',
                cerrado=True,
                created_at=fecha,
                fecha_cierre=fecha + timedelta(minutes=random.randint(30, 90)),
            )
            db.session.add(pedido)
            db.session.flush()

            # 2-6 items aleatorios
            total = Decimal('0')
            n_items = random.randint(2, 6)
            for _ in range(n_items):
                prod = random.choice(productos)
                cant = random.randint(1, 3)
                item = PedidoItem(
                    pedido_id=pedido.id,
                    producto_id=prod.id,
                    cantidad=cant,
                    precio_unitario=prod.precio,
                    notas='',
                )
                db.session.add(item)
                total += prod.precio * cant

            pedido.total = total

            # Pago asociado
            metodo = random.choice(['efectivo', 'tarjeta', 'transferencia'])
            pago = Pago(
                empresa_id=empresa.id,
                sucursal_id=sucursal.id,
                pedido_id=pedido.id,
                metodo=metodo,
                monto=total,
                factura_num=f'F-{random.randint(1000, 9999)}',
                fecha=pedido.fecha_cierre,
            )
            db.session.add(pago)

            total_creados += 1

        db.session.commit()
        print(f'   ✅ {total_creados} pedidos creados')

        # ---------- 6. Actualizar estados de mesas ----------
        print('\n🎨 Actualizando estados de mesas...')
        estados = ['libre', 'libre', 'libre', 'ocupada', 'ocupada',
                   'reservada', 'pagada']
        for m in mesas:
            m.estado = random.choice(estados)
        db.session.commit()
        print('   ✅ Estados actualizados')

        print('\n' + '=' * 60)
        print('✅ SEED COMPLETADO')
        print('=' * 60)
        print('\n📊 Resumen final:')
        print(f'   Mesas:     {Mesa.query.count()}')
        print(f'   Productos: {Producto.query.count()}')
        print(f'   Usuarios:  {Usuario.query.count()}')
        print(f'   Pedidos:   {Pedido.query.count()}')
        print(f'   Pagos:     {Pago.query.count()}')
        print(f'   Recetas:   {Receta.query.count()}')
        print('\n🔑 Usuarios demo (para probar):')
        for _, user, _, rol, pwd in USUARIOS_DEMO:
            print(f'   {user:10s} / {pwd:15s} → rol: {rol}')
        print()


if __name__ == '__main__':
    seed_demo()