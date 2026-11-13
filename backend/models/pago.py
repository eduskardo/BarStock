from datetime import datetime
from models import db


class Pago(db.Model):
    __tablename__ = 'pagos'

    id           = db.Column(db.Integer, primary_key=True)
    empresa_id   = db.Column(db.Integer, db.ForeignKey('empresas.id'),  nullable=False)
    sucursal_id  = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    pedido_id    = db.Column(db.Integer, db.ForeignKey('pedidos.id'),    nullable=False)
    metodo       = db.Column(db.String(20), nullable=False)  # efectivo/tarjeta/transferencia
    monto        = db.Column(db.Numeric(12, 2), nullable=False)
    factura_num  = db.Column(db.String(30))
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha        = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'metodo': self.metodo,
            'monto': float(self.monto or 0),
            'factura_num': self.factura_num,
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }