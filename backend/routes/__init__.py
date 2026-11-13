"""
Paquete de rutas (blueprints) del backend.

Cada módulo define un Blueprint que se registra en app.py
con un prefijo /api/...

Módulos:
    auth       → autenticación (login, refresh, me, logout)
    mesas      → gestión de mesas y consumo
    pos        → punto de venta (pedidos)
    cocina     → monitor de producción
    usuarios   → administración de usuarios y roles
    reportes   → reportes y analítica comercial
"""