from datetime import datetime
from models import db


class Empresa(db.Model):
    __tablename__ = 'empresas'

    id         = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(150), nullable=False)
    nit        = db.Column(db.String(30), unique=True)
    direccion  = db.Column(db.String(200))
    telefono   = db.Column(db.String(30))
    email      = db.Column(db.String(120))
    logo_url   = db.Column(db.String(255))
    activa     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sucursales = db.relationship('Sucursal', backref='empresa', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'nit': self.nit,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'email': self.email,
            'activa': self.activa,
        }