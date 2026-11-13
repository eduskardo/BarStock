from datetime import datetime
from models import db


class Movimiento(db.Model):
    __tablename__ = 'movimientos'

    id              = db.Column(db.Integer, primary_key=True)
    empresa_id      = db.Column(db.Integer, db.ForeignKey('empresas.id'),  nullable=False)
    sucursal_id     = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    insumo_id       = db.Column(db.Integer, db.ForeignKey('insumos.id'),   nullable=False)
    tipo            = db.Column(db.String(20), nullable=False)
    cantidad        = db.Column(db.Numeric(12, 3), nullable=False)
    stock_antes     = db.Column(db.Numeric(12, 3), default=0)
    stock_despues   = db.Column(db.Numeric(12, 3), default=0)
    costo_unitario  = db.Column(db.Numeric(12, 2), default=0)
    costo_total     = db.Column(db.Numeric(12, 2), default=0)
    motivo          = db.Column(db.String(200))
    referencia_id   = db.Column(db.Integer)
    referencia_tipo = db.Column(db.String(30))
    usuario_id      = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha           = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    insumo  = db.relationship('Insumo',  lazy='joined')
    usuario = db.relationship('Usuario', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'insumo_id': self.insumo_id,
            'insumo_nombre': self.insumo.nombre if self.insumo else '',
            'unidad': self.insumo.unidad if self.insumo else '',
            'tipo': self.tipo,
            'cantidad': float(self.cantidad or 0),
            'stock_antes': float(self.stock_antes or 0),
            'stock_despues': float(self.stock_despues or 0),
            'costo_unitario': float(self.costo_unitario or 0),
            'costo_total': float(self.costo_total or 0),
            'motivo': self.motivo,
            'referencia_id': self.referencia_id,
            'referencia_tipo': self.referencia_tipo,
            'usuario': self.usuario.nombre if self.usuario else 'Sistema',
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }