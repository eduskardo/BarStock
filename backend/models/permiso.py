from models import db


class Permiso(db.Model):
    __tablename__ = 'permisos'

    id          = db.Column(db.Integer, primary_key=True)
    codigo      = db.Column(db.String(80), unique=True, nullable=False)
    modulo      = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'modulo': self.modulo,
            'descripcion': self.descripcion,
        }


PERMISOS_BASE = [
    ('mesas.ver',            'mesas',      'Ver la lista de mesas'),
    ('mesas.abrir',          'mesas',      'Abrir mesa'),
    ('mesas.cerrar',         'mesas',      'Cerrar cuenta y cobrar'),
    ('pos.ver',              'pos',        'Acceder al punto de venta'),
    ('pos.pedido.crear',     'pos',        'Crear pedidos'),
    ('pos.cobrar',           'pos',        'Registrar cobros'),
    ('cocina.ver',           'cocina',     'Ver el monitor de cocina'),
    ('cocina.estado',        'cocina',     'Cambiar estado de comandas'),
    ('inventario.ver',       'inventario', 'Ver inventario'),
    ('inventario.movimiento','inventario', 'Registrar movimientos'),
    ('inventario.ajuste',    'inventario', 'Ajustar stock'),
    ('reportes.ver',         'reportes',   'Ver reportes generales'),
    ('reportes.ventas',      'reportes',   'Ver reportes de ventas'),
    ('reportes.financiero',  'reportes',   'Ver reportes financieros'),
    ('usuarios.ver',         'usuarios',   'Ver usuarios'),
    ('usuarios.crear',       'usuarios',   'Crear usuarios'),
    ('usuarios.editar',      'usuarios',   'Editar usuarios'),
    ('usuarios.eliminar',    'usuarios',   'Eliminar usuarios'),
    ('roles.ver',            'usuarios',   'Ver roles'),
    ('roles.editar',         'usuarios',   'Editar roles y permisos'),
    ('reservas.ver',         'reservas',   'Ver reservas'),
    ('reservas.gestionar',   'reservas',   'Crear / editar reservas'),
]