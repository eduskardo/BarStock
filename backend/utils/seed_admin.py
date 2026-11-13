import os
from models.usuario import Usuario
from models.rol import Rol


def seed_admin(db):
    """Crea la empresa, sucursal y usuario admin inicial si no existen."""
    from models.empresa  import Empresa
    from models.sucursal import Sucursal

    if Usuario.query.filter_by(username='admin').first():
        return

    # Empresa
    empresa = Empresa.query.first()
    if not empresa:
        empresa = Empresa(nombre='Mi Restaurante', nit='000000000', activa=True)
        db.session.add(empresa)
        db.session.flush()

    # Sucursal
    sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
    if not sucursal:
        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre='Sucursal Principal',
            direccion='Dirección principal',
        )
        db.session.add(sucursal)
        db.session.flush()

    # Usuario admin
    admin = Usuario(
        empresa_id=empresa.id,
        sucursal_id=sucursal.id,
        nombre='Administrador',
        email='admin@restaurante.com',
        username='admin',
        activo=True,
    )
    admin.set_password(os.getenv('ADMIN_PASSWORD', 'Admin123!'))

    rol_admin = Rol.query.filter_by(nombre='admin', es_sistema=True).first()
    if rol_admin:
        admin.roles.append(rol_admin)

    db.session.add(admin)
    db.session.commit()
    print('✅ Admin creado: admin / Admin123!')