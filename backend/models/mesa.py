from datetime import datetime
from models import db


class Mesa(db.Model):
    __tablename__ = 'mesas'

    id          = db.Column(db.Integer, primary_key=True)
    empresa_id  = db.Column(db.Integer, db.ForeignKey('empresas.id'),  nullable=False)
    sucursal_id = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    numero      = db.Column(db.Integer, nullable=False)
    capacidad   = db.Column(db.Integer, default=4)
    zona        = db.Column(db.String(50))        # salón, terraza, barra
    estado      = db.Column(db.String(20), default='libre')  # libre/ocupada/pagada/reservada
    mesero_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    activa      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'sucursal_id': self.sucursal_id,
            'numero': self.numero,
            'capacidad': self.capacidad,
            'zona': self.zona,
            'estado': self.estado,
            'mesero_id': self.mesero_id,
        }