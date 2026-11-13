from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.usuario import Usuario


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            print(f'❌ [JWT ERROR] {type(e).__name__}: {e}')
            return jsonify({
                'error': 'Token inválido o expirado',
                'detalle': str(e),
                'tipo': type(e).__name__,
            }), 401

        user_id = get_jwt_identity()          # 👈 ahora es string '1'
        usuario = Usuario.query.get(int(user_id))   # 👈 convertir a int

        if not usuario or not usuario.activo:
            return jsonify({'error': 'Usuario no autorizado'}), 401

        g.usuario = usuario
        return fn(*args, **kwargs)
    return wrapper


def requiere_permiso(*codigos):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not g.usuario.tiene_alguno(codigos):
                return jsonify({
                    'error': 'Permiso denegado',
                    'requeridos': list(codigos),
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def requiere_rol(*nombres_rol):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            roles_usuario = {r.nombre for r in g.usuario.roles}
            if not roles_usuario.intersection(nombres_rol):
                return jsonify({'error': 'Rol no autorizado'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def requiere_empresa(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.usuario.empresa_id:
            return jsonify({'error': 'Usuario sin empresa asignada'}), 403
        return fn(*args, **kwargs)
    return wrapper