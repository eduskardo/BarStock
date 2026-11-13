from datetime import datetime
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from models.usuario import Usuario
from models import db
from utils.auth_decorators import login_required

auth_bp = Blueprint('auth', __name__)


# ------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña obligatorios'}), 400

    usuario = Usuario.query.filter(
        (Usuario.username == username) | (Usuario.email == username)
    ).first()

    if not usuario or not usuario.check_password(password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    if not usuario.activo:
        return jsonify({'error': 'Usuario desactivado'}), 403

    usuario.ultimo_login = datetime.utcnow()
    db.session.commit()

    # 👇 identity SIEMPRE string
    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={
            'empresa_id':  usuario.empresa_id,
            'sucursal_id': usuario.sucursal_id,
            'roles':       [r.nombre for r in usuario.roles],
        },
    )
    refresh_token = create_refresh_token(identity=str(usuario.id))

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'usuario': usuario.to_dict(),
    }), 200


# ------------------------------------------------------------
# REFRESH
# ------------------------------------------------------------
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()                 # string
    usuario = Usuario.query.get(int(user_id))    # 👈 int() para BD
    if not usuario or not usuario.activo:
        return jsonify({'error': 'Usuario no válido'}), 401

    nuevo_access = create_access_token(
        identity=str(usuario.id),                # 👈 string
        additional_claims={
            'empresa_id':  usuario.empresa_id,
            'sucursal_id': usuario.sucursal_id,
            'roles':       [r.nombre for r in usuario.roles],
        },
    )
    return jsonify({'access_token': nuevo_access}), 200


# ------------------------------------------------------------
# PERFIL ACTUAL
# ------------------------------------------------------------
@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify(g.usuario.to_dict()), 200


# ------------------------------------------------------------
# CAMBIAR CONTRASEÑA
# ------------------------------------------------------------
@auth_bp.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    data = request.get_json() or {}
    actual = data.get('actual') or ''
    nueva  = data.get('nueva') or ''

    if len(nueva) < 8:
        return jsonify({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}), 400

    if not g.usuario.check_password(actual):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400

    g.usuario.set_password(nueva)
    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Contraseña actualizada'}), 200


# ------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    return jsonify({'ok': True, 'msg': 'Sesión cerrada'}), 200