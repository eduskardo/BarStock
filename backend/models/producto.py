from datetime import datetime
from models import db


class Producto(db.Model):
    __tablename__ = 'productos'

    id          = db.Column(db.Integer, primary_key=True)
    empresa_id  = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nombre      = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(255))
    categoria   = db.Column(db.String(60))
    precio      = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    activo      = db.Column(db.Boolean, default=True)
    destacado   = db.Column(db.Boolean, default=False)
    imagen_url  = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'precio': float(self.precio or 0),
            'activo': self.activo,
            'destacado': self.destacado,
        }