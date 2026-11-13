from datetime import datetime
from models import db


class Receta(db.Model):
    __tablename__ = 'recetas'

    id          = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    insumo_id   = db.Column(db.Integer, db.ForeignKey('insumos.id'),   nullable=False)
    cantidad    = db.Column(db.Numeric(12, 3), nullable=False)
    merma_pct   = db.Column(db.Numeric(5, 2), default=0)
    opcional    = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    insumo = db.relationship('Insumo', lazy='joined')

    def cantidad_con_merma(self):
        c = float(self.cantidad or 0)
        m = float(self.merma_pct or 0)
        return c * (1 + m / 100)

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'insumo_id': self.insumo_id,
            'insumo_nombre': self.insumo.nombre if self.insumo else '',
            'unidad': self.insumo.unidad if self.insumo else '',
            'cantidad': float(self.cantidad or 0),
            'merma_pct': float(self.merma_pct or 0),
            'cantidad_neta': self.cantidad_con_merma(),
            'opcional': self.opcional,
        }