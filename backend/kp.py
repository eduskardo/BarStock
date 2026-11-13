from app import create_app
from models import db
from models.pedido import Pedido
from models.mesa import Mesa
from datetime import datetime, timezone

app = create_app()
with app.app_context():
    # Cerrar todos los pedidos viejos
    pedidos = Pedido.query.all()
    for p in pedidos:
        p.cerrado = True
        if not p.fecha_cierre:
            p.fecha_cierre = datetime.now(timezone.utc)
            
    # Liberar todas las mesas
    for m in Mesa.query.all():
        m.estado = 'libre'
        m.mesero_id = None
        
    db.session.commit()
    print("✅ Base de datos limpia. Mesas libres y pedidos cerrados.")
exit()