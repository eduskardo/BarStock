from flask import Blueprint, request, jsonify, g
from models import db
from models.receta import Receta
from models.insumo import Insumo
from models.producto import Producto
from utils.auth_decorators import requiere_permiso

recetas_bp = Blueprint('recetas', __name__)

# Obtener la receta de un producto
@recetas_bp.route('/producto/<int:pid>', methods=['GET'])
@requiere_permiso('inventario.ver')
def obtener_receta(pid):
    recetas = Receta.query.filter_by(producto_id=pid).all()
    return jsonify([r.to_dict() for r in recetas])

# Agregar o actualizar un insumo en la receta
@recetas_bp.route('/producto/<int:pid>', methods=['POST'])
@requiere_permiso('inventario.ajuste')
def agregar_insumo(pid):
    data = request.get_json() or {}
    insumo_id = data.get('insumo_id')
    cantidad = data.get('cantidad')
    merma = data.get('merma_pct', 0)

    if not insumo_id or not cantidad:
        return jsonify({'error': 'insumo_id y cantidad son obligatorios'}), 400

    # Verificar que el insumo y producto pertenezcan a la empresa
    insumo = Insumo.query.filter_by(id=insumo_id, empresa_id=g.usuario.empresa_id).first_or_404()
    producto = Producto.query.filter_by(id=pid, empresa_id=g.usuario.empresa_id).first_or_404()

    # Si ya existe, actualizamos la cantidad. Si no, lo creamos.
    existente = Receta.query.filter_by(producto_id=pid, insumo_id=insumo_id).first()
    
    if existente:
        existente.cantidad = cantidad
        existente.merma_pct = merma
    else:
        nueva_receta = Receta(
            producto_id=pid,
            insumo_id=insumo_id,
            cantidad=cantidad,
            merma_pct=merma
        )
        db.session.add(nueva_receta)

    db.session.commit()
    return jsonify({'ok': True, 'msg': 'Insumo agregado a la receta'})

# Eliminar un insumo de la receta
@recetas_bp.route('/<int:rid>', methods=['DELETE'])
@requiere_permiso('inventario.ajuste')
def eliminar_insumo(rid):
    receta = Receta.query.get_or_404(rid)
    db.session.delete(receta)
    db.session.commit()
    return jsonify({'ok': True})

# Calcular el costo total de la receta
@recetas_bp.route('/costo/<int:pid>', methods=['GET'])
@requiere_permiso('inventario.ver')
def costo_receta(pid):
    recetas = Receta.query.filter_by(producto_id=pid).all()
    total = 0
    detalle = []
    for r in recetas:
        costo_insumo = r.cantidad_con_merma() * float(r.insumo.costo_unitario or 0)
        total += costo_insumo
        detalle.append({
            'insumo': r.insumo.nombre,
            'cantidad': r.cantidad_con_merma(),
            'unidad': r.insumo.unidad,
            'costo': costo_insumo,
        })
    return jsonify({'producto_id': pid, 'costo_total': total, 'detalle': detalle})