from models import db
from datetime import datetime, timezone

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id            = db.Column(db.Integer, primary_key=True)
    empresa_id    = db.Column(db.Integer, db.ForeignKey('empresas.id'),  nullable=False)
    sucursal_id   = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    mesa_id       = db.Column(db.Integer, db.ForeignKey('mesas.id'),      nullable=True)
    usuario_id    = db.Column(db.Integer, db.ForeignKey('usuarios.id'),   nullable=True)
    estado        = db.Column(db.String(20), default='pendiente')  # pendiente/en_preparacion/listo/servido
    total         = db.Column(db.Numeric(12, 2), default=0)
    cerrado       = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    fecha_cierre = db.Column(db.DateTime, index=True)

    mesa    = db.relationship('Mesa',    lazy='joined')
    usuario = db.relationship('Usuario', lazy='joined')
    items   = db.relationship('PedidoItem', backref='pedido',
                              cascade='all, delete-orphan', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'mesa_id': self.mesa_id,
            'mesa_numero': self.mesa.numero if self.mesa else None,
            'usuario_id': self.usuario_id,
            'estado': self.estado,
            'total': float(self.total or 0),
            'cerrado': self.cerrado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'items': [i.to_dict() for i in self.items],
        }

    def to_dict_cocina(self):
        # Forzamos a que la fecha se envíe con el formato UTC correcto (con la 'Z')
        hora_utc = self.created_at.isoformat()
        if not hora_utc.endswith('Z') and '+' not in hora_utc:
            hora_utc += 'Z'

        return {
            'id': self.id,
            'mesa_numero': self.mesa.numero if self.mesa else 0,
            'mesero': self.usuario.nombre if self.usuario else 'N/A',
            'estado': self.estado,
            'hora_pedido': hora_utc, # 👈 Enviamos la hora corregida
            'items': [
                {
                    'cantidad': i.cantidad,
                    'nombre':   i.producto.nombre if i.producto else '',
                    'notas':    i.notas or '',
                }
                for i in self.items
            ],
        }


class PedidoItem(db.Model):
    __tablename__ = 'pedido_items'

    id              = db.Column(db.Integer, primary_key=True)
    pedido_id       = db.Column(db.Integer, db.ForeignKey('pedidos.id'),    nullable=False)
    producto_id     = db.Column(db.Integer, db.ForeignKey('productos.id'),  nullable=False)
    cantidad        = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    notas           = db.Column(db.String(255))

    producto = db.relationship('Producto', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'nombre': self.producto.nombre if self.producto else '',
            'cantidad': self.cantidad,
            'precio': float(self.precio_unitario or 0),
            'notas': self.notas or '',
        }