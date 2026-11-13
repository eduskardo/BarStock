from flask import Flask, jsonify, render_template, request, g
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from sqlalchemy import text
from config import Config
from models import db
from socket_events import register_socket_events
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.usuario import Usuario



# Extensiones (se inicializan en create_app)
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent')
jwt = JWTManager()


def create_app():
    # 👇 UNA SOLA instancia, con templates y static
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path='/static',
    )
    app.config.from_object(Config)
    CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

    db.init_app(app)
    socketio.init_app(app)
    jwt.init_app(app)

    # ---------- Manejo global de errores JWT ----------
    @jwt.unauthorized_loader
    def _no_token(err):
        return jsonify({'error': 'Token requerido', 'detalle': err}), 401

    @jwt.expired_token_loader
    def _expired(jwt_header, jwt_payload):
        return jsonify({'error': 'Token expirado'}), 401

    @jwt.invalid_token_loader
    def _invalid(err):
        return jsonify({'error': 'Token inválido', 'detalle': err}), 401

    # ---------- Blueprints ----------
    from routes.auth        import auth_bp
    from routes.mesas       import mesas_bp
    from routes.pos         import pos_bp
    from routes.cocina      import cocina_bp
    from routes.usuarios    import usuarios_bp
    from routes.reportes    import reportes_bp
    from routes.inventario  import inventario_bp
    from routes.recetas     import recetas_bp

    app.register_blueprint(auth_bp,        url_prefix='/api/auth')
    app.register_blueprint(mesas_bp,       url_prefix='/api/mesas')
    app.register_blueprint(pos_bp,         url_prefix='/api/pedidos')
    app.register_blueprint(cocina_bp,      url_prefix='/api/cocina')
    app.register_blueprint(recetas_bp, url_prefix='/api/recetas')
    app.register_blueprint(usuarios_bp,    url_prefix='/api/usuarios')
    app.register_blueprint(reportes_bp,    url_prefix='/api/reportes')
    app.register_blueprint(inventario_bp,  url_prefix='/api/inventario')

    # ---------- Socket.IO ----------
    register_socket_events(socketio)

    # ---------- Rutas de páginas HTML ----------
    @app.route('/')
    @app.route('/login')
    def page_login():
        return render_template('login.html')

    @app.route('/app')
    def page_index():
        return render_template('index.html', active_page='index')

    @app.route('/app/pos')
    def page_pos():
        return render_template('pos.html')

    @app.route('/app/cocina')
    def page_cocina():
        return render_template('cocina.html', active_page='cocina')

    @app.route('/app/inventario')
    def page_inventario():
        return render_template('inventario.html', active_page='inventario')

    @app.route('/app/reportes')
    def page_reportes():
        return render_template('reportes.html', active_page='reportes')

    @app.route('/app/recetas')
    def page_recetas():
        return render_template('recetas.html', active_page='recetas')

    @app.route('/app/usuarios')
    def page_usuarios():
        return render_template('usuarios.html', active_page='usuarios')

    @app.route('/app/cierre-caja')
    def page_cierre_caja():
        return render_template('cierre_caja.html', active_page='cierre_caja')

    # ---------- BD y seeds ----------
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            print('✅ Conexión DB OK')
        except Exception as e:
            print(f'❌ Error de conexión a BD: {e}')
            raise
        db.create_all()

        from utils.permisos import seed_permisos_y_roles
        seed_permisos_y_roles(db)

        from utils.seed_admin import seed_admin
        seed_admin(db)

        from utils.seed_inventario import seed_inventario_demo
        seed_inventario_demo(db)

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True,)