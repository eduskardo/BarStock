from datetime import datetime
from models import db


class Insumo(db.Model):
    __tablename__ = 'insumos'

    id             = db.Column(db.Integer, primary_key=True)
    empresa_id     = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    codigo         = db.Column(db.String(40), index=True)
    nombre         = db.Column(db.String(120), nullable=False)
    categoria      = db.Column(db.String(60))
    unidad         = db.Column(db.String(20), nullable=False)
    costo_unitario = db.Column(db.Numeric(12, 2), default=0)
    stock_actual   = db.Column(db.Numeric(12, 3), default=0)
    stock_minimo   = db.Column(db.Numeric(12, 3), default=0)
    stock_maximo   = db.Column(db.Numeric(12, 3), default=0)
    perecedero     = db.Column(db.Boolean, default=False)
    activo         = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def bajo_minimo(self):
        return float(self.stock_actual or 0) < float(self.stock_minimo or 0)

    @property
    def valor_stock(self):
        return float(self.stock_actual or 0) * float(self.costo_unitario or 0)

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'unidad': self.unidad,
            'costo_unitario': float(self.costo_unitario or 0),
            'stock_actual': float(self.stock_actual or 0),
            'stock_minimo': float(self.stock_minimo or 0),
            'bajo_minimo': self.bajo_minimo,
            'valor_stock': self.valor_stock,
        }