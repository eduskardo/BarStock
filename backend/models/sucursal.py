from datetime import datetime
from models import db


class Sucursal(db.Model):
    __tablename__ = 'sucursales'

    id         = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nombre     = db.Column(db.String(100), nullable=False)
    direccion  = db.Column(db.String(200))
    telefono   = db.Column(db.String(30))
    activa     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'activa': self.activa,
        }