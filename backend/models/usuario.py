from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


usuario_rol = db.Table(
    'usuario_rol',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('rol_id',     db.Integer, db.ForeignKey('roles.id'),    primary_key=True),
)

usuario_sucursal = db.Table(
    'usuario_sucursal',
    db.Column('usuario_id',  db.Integer, db.ForeignKey('usuarios.id'),   primary_key=True),
    db.Column('sucursal_id', db.Integer, db.ForeignKey('sucursales.id'), primary_key=True),
)


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id            = db.Column(db.Integer, primary_key=True)
    empresa_id    = db.Column(db.Integer, db.ForeignKey('empresas.id'),  nullable=False)
    sucursal_id   = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=True)
    nombre        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username      = db.Column(db.String(50),  unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono      = db.Column(db.String(30))
    activo        = db.Column(db.Boolean, default=True)
    ultimo_login  = db.Column(db.DateTime)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    empresa   = db.relationship('Empresa',  backref='usuarios', foreign_keys=[empresa_id])
    sucursal  = db.relationship('Sucursal', foreign_keys=[sucursal_id])
    roles = db.relationship(
        'Rol',
        secondary=usuario_rol,
        backref=db.backref('usuarios', lazy='dynamic'),
        lazy='joined',
    )
    sucursales = db.relationship(
        'Sucursal',
        secondary=usuario_sucursal,
        backref=db.backref('empleados', lazy='dynamic'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def permisos(self):
        s = set()
        for rol in self.roles:
            if rol.activo:
                s.update(p.codigo for p in rol.permisos)
        return s

    def tiene_permiso(self, codigo):
        return codigo in self.permisos

    def tiene_alguno(self, codigos):
        return bool(self.permisos.intersection(codigos))

    def to_dict(self, incluir_roles=True):
        data = {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'sucursal_id': self.sucursal_id,
            'nombre': self.nombre,
            'email': self.email,
            'username': self.username,
            'telefono': self.telefono,
            'activo': self.activo,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
        }
        if incluir_roles:
            data['roles']    = [r.nombre for r in self.roles]
            data['permisos'] = sorted(self.permisos)
            data['empresa']  = self.empresa.nombre if self.empresa else None
            data['sucursal'] = self.sucursal.nombre if self.sucursal else None
        return data