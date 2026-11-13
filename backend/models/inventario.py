from datetime import datetime
from models import db


class InventarioSucursal(db.Model):
    __tablename__ = 'inventario_sucursal'

    id           = db.Column(db.Integer, primary_key=True)
    insumo_id    = db.Column(db.Integer, db.ForeignKey('insumos.id'),    nullable=False)
    sucursal_id  = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    stock_actual = db.Column(db.Numeric(12, 3), default=0)
    stock_minimo = db.Column(db.Numeric(12, 3), default=0)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('insumo_id', 'sucursal_id', name='uq_insumo_sucursal'),
    )

    insumo = db.relationship('Insumo', lazy='joined')

    @property
    def bajo_minimo(self):
        return float(self.stock_actual or 0) < float(self.stock_minimo or 0)