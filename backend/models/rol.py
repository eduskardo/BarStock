from datetime import datetime
from models import db


rol_permiso = db.Table(
    'rol_permiso',
    db.Column('rol_id',     db.Integer, db.ForeignKey('roles.id'),    primary_key=True),
    db.Column('permiso_id', db.Integer, db.ForeignKey('permisos.id'), primary_key=True),
)


class Rol(db.Model):
    __tablename__ = 'roles'

    id          = db.Column(db.Integer, primary_key=True)
    empresa_id  = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    nombre      = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    es_sistema  = db.Column(db.Boolean, default=False)
    activo      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    permisos = db.relationship(
        'Permiso',
        secondary=rol_permiso,
        backref=db.backref('roles', lazy='dynamic'),
        lazy='joined',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'es_sistema': self.es_sistema,
            'permisos': [p.codigo for p in self.permisos],
        }