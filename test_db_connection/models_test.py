from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ClientePrueba(db.Model):
    __tablename__ = 'clientes_prueba'

    id         = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }