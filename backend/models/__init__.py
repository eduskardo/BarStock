from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Importar TODOS los modelos aquí para que SQLAlchemy los registre
from models.empresa   import Empresa
from models.sucursal  import Sucursal
from models.permiso   import Permiso
from models.rol       import Rol
from models.usuario   import Usuario
from models.mesa      import Mesa
from models.producto  import Producto
from models.pedido    import Pedido, PedidoItem
from models.pago      import Pago
from models.insumo    import Insumo
from models.receta    import Receta
from models.movimiento import Movimiento
from models.inventario import InventarioSucursal