"""
Catálogo de permisos y roles base que se siembran en la BD al iniciar.
"""

from models.permiso import PERMISOS_BASE, Permiso
from models.rol import Rol

# Definición de roles del sistema con sus permisos por defecto
ROLES_SISTEMA = {
    'admin': {
        'descripcion': 'Acceso total al sistema',
        'permisos': ['*'],  # comodín → todos
    },
    'gerente': {
        'descripcion': 'Gestión operativa y reportes',
        'permisos': [
            'mesas.ver', 'mesas.abrir', 'mesas.cerrar',
            'pos.ver', 'pos.pedido.crear', 'pos.pedido.cancelar',
            'pos.descuento', 'pos.cobrar',
            'cocina.ver', 'cocina.estado',
            'inventario.ver', 'inventario.movimiento', 'inventario.ajuste',
            'reportes.ver', 'reportes.ventas', 'reportes.financiero',
            'usuarios.ver', 'usuarios.crear', 'usuarios.editar',
            'reservas.ver', 'reservas.gestionar',
        ],
    },
    'cajero': {
        'descripcion': 'Cobra cuentas y maneja el POS',
        'permisos': [
            'mesas.ver', 'mesas.cerrar',
            'pos.ver', 'pos.cobrar', 'pos.pedido.crear',
            'reportes.ver', 'reportes.ventas',
        ],
    },
    'mesero': {
        'descripcion': 'Toma pedidos y atiende mesas',
        'permisos': [
            'mesas.ver', 'mesas.abrir',
            'pos.ver', 'pos.pedido.crear',
            'reservas.ver',
        ],
    },
    'cocina': {
        'descripcion': 'Monitor de producción',
        'permisos': [
            'cocina.ver', 'cocina.estado',
            'inventario.ver',
        ],
    },
    'bodega': {
        'descripcion': 'Control de inventario',
        'permisos': [
            'inventario.ver', 'inventario.movimiento', 'inventario.ajuste',
        ],
    },
}


def seed_permisos_y_roles(db):
    """Siembra permisos y roles base. Idempotente."""
    # 1) Permisos
    for codigo, modulo, desc in PERMISOS_BASE:
        if not Permiso.query.filter_by(codigo=codigo).first():
            db.session.add(Permiso(codigo=codigo, modulo=modulo, descripcion=desc))
    db.session.commit()

    # 2) Roles del sistema
    todos_permisos = {p.codigo: p for p in Permiso.query.all()}

    for nombre, conf in ROLES_SISTEMA.items():
        rol = Rol.query.filter_by(nombre=nombre, es_sistema=True).first()
        if not rol:
            rol = Rol(
                nombre=nombre,
                descripcion=conf['descripcion'],
                es_sistema=True,
                empresa_id=None,   # roles de sistema son globales
            )
            db.session.add(rol)
            db.session.flush()

        # Asignar permisos
        if conf['permisos'] == ['*']:
            rol.permisos = list(todos_permisos.values())
        else:
            rol.permisos = [
                todos_permisos[c]
                for c in conf['permisos']
                if c in todos_permisos
            ]

    db.session.commit()
    print('✅ Permisos y roles base sembrados')