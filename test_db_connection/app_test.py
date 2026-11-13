"""
Script de prueba de conexión Flask ↔ PostgreSQL.
Ejecuta:  python app_test.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from flask import Flask, jsonify
from sqlalchemy import text
from models_test import db, ClientePrueba


# ============================================================
#  CREAR APP
# ============================================================
def create_app():
    app = Flask(__name__)

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('❌ ERROR: DATABASE_URL no está definida en .env')
        sys.exit(1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,   # verifica conexión antes de usarla
        'pool_recycle': 3600,    # recicla conexiones cada hora
        'echo': False,           # cambia a True para ver el SQL generado
    }
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

    db.init_app(app)

    # Rutas de prueba
    @app.route('/')
    def home():
        return jsonify({
            'msg': 'API de prueba',
            'endpoints': ['/health', '/clientes', '/clientes/crear'],
        })

    @app.route('/health')
    def health():
        """Verifica que la conexión a la BD funciona."""
        try:
            db.session.execute(text('SELECT 1'))
            version = db.session.execute(text('SHOW server_version')).scalar()
            db_name = db.session.execute(text('SELECT current_database()')).scalar()
            db_user = db.session.execute(text('SELECT current_user')).scalar()

            return jsonify({
                'status': 'ok',
                'database': db_name,
                'usuario': db_user,
                'version_postgres': version,
                'timestamp': datetime.utcnow().isoformat(),
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'mensaje': str(e),
                'tipo': type(e).__name__,
            }), 500

    @app.route('/clientes')
    def listar_clientes():
        clientes = ClientePrueba.query.all()
        return jsonify([c.to_dict() for c in clientes])

    @app.route('/clientes/crear')
    def crear_cliente():
        """Crea un cliente de prueba con nombre aleatorio."""
        import random
        n = random.randint(1000, 9999)
        c = ClientePrueba(
            nombre=f'Cliente {n}',
            email=f'cliente{n}@test.com',
        )
        db.session.add(c)
        db.session.commit()
        return jsonify(c.to_dict()), 201

    return app


# ============================================================
#  DIAGNÓSTICO PREVIO
# ============================================================
def diagnostico():
    """Ejecuta verificaciones antes de levantar Flask."""
    print('=' * 60)
    print('🔍 DIAGNÓSTICO DE CONEXIÓN')
    print('=' * 60)

    # 1. Variables de entorno
    database_url = os.getenv('DATABASE_URL')
    print(f'\n1️⃣  DATABASE_URL:')
    if database_url:
        # Ocultar password en el log
        partes = database_url.split('@')
        if len(partes) == 2:
            credenciales = partes[0].split('://')[1]
            usuario = credenciales.split(':')[0]
            print(f'   ✅ {database_url.split("://")[0]}://{usuario}:***@{partes[1]}')
        else:
            print(f'   ✅ {database_url}')
    else:
        print('   ❌ NO DEFINIDA')
        return False

    # 2. Driver psycopg2
    try:
        import psycopg2
        print(f'\n2️⃣  Driver psycopg2: ✅ {psycopg2.__version__}')
    except ImportError:
        print('\n2️⃣  Driver psycopg2: ❌ NO INSTALADO')
        print('   Instala con: pip install psycopg2-binary')
        return False

    # 3. Conexión directa con psycopg2
    print('\n3️⃣  Conexión directa a PostgreSQL:')
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f'   ✅ {version[:70]}...')
    except Exception as e:
        print(f'   ❌ {type(e).__name__}: {e}')
        print('\n   Posibles causas:')
        print('   • PostgreSQL no está corriendo')
        print('   • Usuario o contraseña incorrectos')
        print('   • Base de datos no existe')
        print('   • Firewall bloqueando el puerto 5432')
        return False

    # 4. SQLAlchemy engine
    print('\n4️⃣  SQLAlchemy:')
    try:
        from sqlalchemy import create_engine
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1')).scalar()
        print(f'   ✅ Motor funciona (SELECT 1 → {result})')
    except Exception as e:
        print(f'   ❌ {type(e).__name__}: {e}')
        return False

    print('\n' + '=' * 60)
    print('✅ TODAS LAS VERIFICACIONES PASARON')
    print('=' * 60 + '\n')
    return True


# ============================================================
#  MAIN
# ============================================================
if __name__ == '__main__':
    print('\n🧪 TEST DE CONEXIÓN BACKEND ↔ POSTGRESQL\n')

    # Diagnóstico previo
    if not diagnostico():
        print('\n❌ Diagnóstico falló. Corrige los errores y vuelve a intentar.\n')
        sys.exit(1)

    # Crear app y tablas
    app = create_app()

    with app.app_context():
        print('📦 Creando tablas...')
        try:
            db.create_all()
            print('   ✅ Tablas creadas/verificadas')
        except Exception as e:
            print(f'   ❌ Error: {e}')
            sys.exit(1)

        # Test rápido: insertar y consultar
        print('\n🔬 Test de escritura/lectura:')
        try:
            c = ClientePrueba(nombre='Test Inicial', email='test@init.com')
            # Evitar duplicados
            existente = ClientePrueba.query.filter_by(email='test@init.com').first()
            if not existente:
                db.session.add(c)
                db.session.commit()
                print(f'   ✅ Cliente insertado (id={c.id})')
            else:
                print(f'   ℹ️  Cliente ya existe (id={existente.id})')

            total = ClientePrueba.query.count()
            print(f'   ✅ Total de clientes en BD: {total}')

        except Exception as e:
            print(f'   ❌ Error: {e}')
            db.session.rollback()

    print('\n' + '=' * 60)
    print('🌐 Levantando servidor Flask en http://localhost:5000')
    print('=' * 60)
    print('\nPrueba estos endpoints:')
    print('  → http://localhost:5000/health')
    print('  → http://localhost:5000/clientes')
    print('  → http://localhost:5000/clientes/crear')
    print('\nCtrl+C para detener\n')

    app.run(host='0.0.0.0', port=5000, debug=True)