from flask import Blueprint, request, jsonify, g
from models import db
from models.usuario import Usuario, usuario_rol, usuario_sucursal
from models.rol import Rol
from models.sucursal import Sucursal
from utils.auth_decorators import requiere_permiso

usuarios_bp = Blueprint('usuarios', __name__)


# ------------------------------------------------------------
# LISTAR USUARIOS (de la empresa del admin)
# ------------------------------------------------------------
@usuarios_bp.route('', methods=['GET'])
@requiere_permiso('usuarios.ver')
def listar():
    usuarios = Usuario.query.filter_by(
        empresa_id=g.usuario.empresa_id
    ).order_by(Usuario.nombre).all()
    return jsonify([u.to_dict() for u in usuarios])


# ------------------------------------------------------------
# OBTENER UNO
# ------------------------------------------------------------
@usuarios_bp.route('/<int:uid>', methods=['GET'])
@requiere_permiso('usuarios.ver')
def obtener(uid):
    u = Usuario.query.filter_by(
        id=uid, empresa_id=g.usuario.empresa_id
    ).first_or_404()
    return jsonify(u.to_dict())


# ------------------------------------------------------------
# CREAR
# ------------------------------------------------------------
@usuarios_bp.route('', methods=['POST'])
@requiere_permiso('usuarios.crear')
def crear():
    data = request.get_json() or {}

    obligatorios = ['nombre', 'email', 'username', 'password']
    for campo in obligatorios:
        if not data.get(campo):
            return jsonify({'error': f'Campo "{campo}" requerido'}), 400

    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email ya registrado'}), 409
    if Usuario.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Usuario ya registrado'}), 409

    u = Usuario(
        empresa_id=g.usuario.empresa_id,
        sucursal_id=data.get('sucursal_id'),
        nombre=data['nombre'],
        email=data['email'].lower(),
        username=data['username'].lower(),
        telefono=data.get('telefono'),
        activo=data.get('activo', True),
    )
    u.set_password(data['password'])

    # Asignar roles
    for rol_nombre in data.get('roles', []):
        rol = Rol.query.filter_by(nombre=rol_nombre).first()
        if rol:
            u.roles.append(rol)

    # Asignar sucursales (opcional)
    for suc_id in data.get('sucursales', []):
        s = Sucursal.query.filter_by(
            id=suc_id, empresa_id=g.usuario.empresa_id
        ).first()
        if s:
            u.sucursales.append(s)

    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201


# ------------------------------------------------------------
# ACTUALIZAR
# ------------------------------------------------------------
@usuarios_bp.route('/<int:uid>', methods=['PUT'])
@requiere_permiso('usuarios.editar')
def actualizar(uid):
    u = Usuario.query.filter_by(
        id=uid, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    data = request.get_json() or {}

    u.nombre   = data.get('nombre', u.nombre)
    u.email    = data.get('email', u.email).lower()
    u.telefono = data.get('telefono', u.telefono)
    u.activo   = data.get('activo', u.activo)
    u.sucursal_id = data.get('sucursal_id', u.sucursal_id)

    # Cambio de contraseña opcional
    if data.get('password'):
        u.set_password(data['password'])

    # Roles
    if 'roles' in data:
        u.roles = []
        for rol_nombre in data['roles']:
            rol = Rol.query.filter_by(nombre=rol_nombre).first()
            if rol:
                u.roles.append(rol)

    db.session.commit()
    return jsonify(u.to_dict())


# ------------------------------------------------------------
# ELIMINAR (soft: solo desactiva)
# ------------------------------------------------------------
@usuarios_bp.route('/<int:uid>', methods=['DELETE'])
@requiere_permiso('usuarios.eliminar')
def eliminar(uid):
    if uid == g.usuario.id:
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400

    u = Usuario.query.filter_by(
        id=uid, empresa_id=g.usuario.empresa_id
    ).first_or_404()

    u.activo = False
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Usuario desactivado'})


# ------------------------------------------------------------
# LISTAR ROLES DISPONIBLES
# ------------------------------------------------------------
@usuarios_bp.route('/roles', methods=['GET'])
@requiere_permiso('roles.ver')
def listar_roles():
    roles = Rol.query.filter_by(activo=True).all()
    return jsonify([r.to_dict() for r in roles])


# ------------------------------------------------------------
# LISTAR PERMISOS DISPONIBLES
# ------------------------------------------------------------
@usuarios_bp.route('/permisos', methods=['GET'])
@requiere_permiso('roles.ver')
def listar_permisos():
    from models.permiso import Permiso
    permisos = Permiso.query.order_by(Permiso.modulo, Permiso.codigo).all()
    return jsonify([p.to_dict() for p in permisos])