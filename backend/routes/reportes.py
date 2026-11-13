from flask import Blueprint, request, jsonify, g, Response
from utils.auth_decorators import requiere_permiso
from services import reportes_service

reportes_bp = Blueprint('reportes', __name__)


def _filtros():
    return {
        'empresa_id':  g.usuario.empresa_id,
        'desde':       request.args.get('desde'),
        'hasta':       request.args.get('hasta'),
        'sucursal_id': request.args.get('sucursal_id', type=int),
    }


@reportes_bp.route('/kpis', methods=['GET'])
@requiere_permiso('reportes.ver')
def kpis():
    return jsonify(reportes_service.kpis_principales(**_filtros()))


@reportes_bp.route('/ventas-por-dia', methods=['GET'])
@requiere_permiso('reportes.ventas')
def ventas_por_dia():
    return jsonify(reportes_service.ventas_por_dia(**_filtros()))


@reportes_bp.route('/ventas-por-hora', methods=['GET'])
@requiere_permiso('reportes.ventas')
def ventas_por_hora():
    return jsonify(reportes_service.ventas_por_hora(**_filtros()))


@reportes_bp.route('/top-productos', methods=['GET'])
@requiere_permiso('reportes.ventas')
def top_productos():
    limite = request.args.get('limite', 15, type=int)
    f = _filtros()
    f['limite'] = limite
    return jsonify(reportes_service.top_productos(**f))


@reportes_bp.route('/ventas-por-categoria', methods=['GET'])
@requiere_permiso('reportes.ventas')
def ventas_por_categoria():
    return jsonify(reportes_service.ventas_por_categoria(**_filtros()))


@reportes_bp.route('/ventas-por-mesero', methods=['GET'])
@requiere_permiso('reportes.ventas')
def ventas_por_mesero():
    return jsonify(reportes_service.ventas_por_mesero(**_filtros()))


@reportes_bp.route('/ventas-por-metodo-pago', methods=['GET'])
@requiere_permiso('reportes.financiero')
def ventas_por_metodo_pago():
    return jsonify(reportes_service.ventas_por_metodo_pago(**_filtros()))


@reportes_bp.route('/food-cost-productos', methods=['GET'])
@requiere_permiso('reportes.financiero')
def food_cost_productos():
    limite = request.args.get('limite', 50, type=int)
    f = _filtros()
    f['limite'] = limite
    return jsonify(reportes_service.food_cost_por_producto(**f))


@reportes_bp.route('/ventas-por-sucursal', methods=['GET'])
@requiere_permiso('reportes.financiero')
def ventas_por_sucursal():
    return jsonify(reportes_service.ventas_por_sucursal(
        empresa_id=g.usuario.empresa_id,
        desde=request.args.get('desde'),
        hasta=request.args.get('hasta'),
    ))


@reportes_bp.route('/rentabilidad-mesas', methods=['GET'])
@requiere_permiso('reportes.ventas')
def rentabilidad_mesas():
    return jsonify(reportes_service.rentabilidad_por_mesa(**_filtros()))


@reportes_bp.route('/exportar/top-productos.csv', methods=['GET'])
@requiere_permiso('reportes.ventas')
def exportar_top_productos():
    csv = reportes_service.exportar_top_productos_csv(**_filtros())
    return Response(
        csv,
        mimetype='text/csv',
        headers={'Content-Disposition':
                 'attachment; filename=top_productos.csv'},
    )


@reportes_bp.route('/cierre-caja', methods=['GET'])
@requiere_permiso('reportes.financiero')
def cierre_caja():
    fecha = request.args.get('fecha')
    if not fecha:
        from datetime import date
        fecha = date.today().isoformat()
        
    data = reportes_service.cierre_caja(
        empresa_id=g.usuario.empresa_id,
        fecha=fecha,
        sucursal_id=request.args.get('sucursal_id', type=int)
    )
    return jsonify(data)