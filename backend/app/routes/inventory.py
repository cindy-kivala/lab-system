from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from app import db
from app.models.inventory import Inventory, InventoryMovement
from app.models.product import Product

bp = Blueprint('inventory', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_inventory():
    """Get all inventory records"""
    product_id = request.args.get('product_id', type=int)
    location = request.args.get('location')
    expiring_soon = request.args.get('expiring_soon', 'false').lower() == 'true'
    expired = request.args.get('expired', 'false').lower() == 'true'
    
    query = Inventory.query
    
    if product_id:
        query = query.filter_by(product_id=product_id)
    
    if location:
        query = query.filter_by(location=location)
    
    inventory = query.all()
    
    if expiring_soon:
        inventory = [inv for inv in inventory if inv.is_expiring_soon()]
    
    if expired:
        inventory = [inv for inv in inventory if inv.is_expired]
    
    return jsonify({
        'inventory': [inv.to_dict() for inv in inventory],
        'count': len(inventory)
    }), 200


@bp.route('/<int:inventory_id>', methods=['GET'])
@jwt_required()
def get_inventory_item(inventory_id):
    """Get single inventory record"""
    inventory = Inventory.get_by_id(inventory_id)
    
    if not inventory:
        return jsonify({'error': 'Inventory record not found'}), 404
    
    return jsonify(inventory.to_dict()), 200


@bp.route('/', methods=['POST'])
@jwt_required()
def add_inventory():
    """Add new inventory record"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    if not all(k in data for k in ['product_id', 'quantity']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        inventory = Inventory(
            product_id=data['product_id'],
            quantity=data['quantity'],
            location=data.get('location', 'main'),
            batch_number=data.get('batch_number'),
            expiration_date=data.get('expiration_date'),
            received_date=data.get('received_date', date.today()),
            cost_per_unit=data.get('cost_per_unit'),
            notes=data.get('notes')
        )
        
        inventory.save()
        
        # Create inventory movement record
        movement = InventoryMovement(
            product_id=data['product_id'],
            movement_type='purchase',
            quantity=data['quantity'],
            batch_number=data.get('batch_number'),
            reason='Initial stock addition',
            performed_by=current_user_id,
            movement_date=datetime.utcnow()
        )
        movement.save()
        
        return jsonify({
            'message': 'Inventory added successfully',
            'inventory': inventory.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:inventory_id>', methods=['PUT'])
@jwt_required()
def update_inventory(inventory_id):
    """Update inventory record"""
    inventory = Inventory.get_by_id(inventory_id)
    
    if not inventory:
        return jsonify({'error': 'Inventory record not found'}), 404
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    try:
        old_quantity = inventory.quantity
        
        # Update fields
        if 'quantity' in data:
            inventory.quantity = data['quantity']
            
            # Create movement record for adjustment
            if data['quantity'] != old_quantity:
                movement = InventoryMovement(
                    product_id=inventory.product_id,
                    movement_type='adjustment',
                    quantity=data['quantity'] - old_quantity,
                    batch_number=inventory.batch_number,
                    reason=data.get('reason', 'Manual adjustment'),
                    performed_by=current_user_id,
                    movement_date=datetime.utcnow()
                )
                movement.save()
        
        if 'location' in data:
            inventory.location = data['location']
        if 'notes' in data:
            inventory.notes = data['notes']
        
        inventory.save()
        
        return jsonify({
            'message': 'Inventory updated successfully',
            'inventory': inventory.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:inventory_id>', methods=['DELETE'])
@jwt_required()
def delete_inventory(inventory_id):
    """Delete inventory record"""
    inventory = Inventory.get_by_id(inventory_id)
    
    if not inventory:
        return jsonify({'error': 'Inventory record not found'}), 404
    
    try:
        inventory.delete()
        return jsonify({'message': 'Inventory record deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/expiring-soon', methods=['GET'])
@jwt_required()
def get_expiring_soon():
    """Get inventory items expiring soon"""
    days = request.args.get('days', 30, type=int)
    
    inventory = Inventory.get_expiring_soon(days)
    
    return jsonify({
        'inventory': [inv.to_dict() for inv in inventory],
        'count': len(inventory)
    }), 200


@bp.route('/expired', methods=['GET'])
@jwt_required()
def get_expired():
    """Get expired inventory items"""
    inventory = Inventory.get_expired()
    
    return jsonify({
        'inventory': [inv.to_dict() for inv in inventory],
        'count': len(inventory)
    }), 200


@bp.route('/movements', methods=['GET'])
@jwt_required()
def get_movements():
    """Get inventory movements (audit trail)"""
    product_id = request.args.get('product_id', type=int)
    movement_type = request.args.get('movement_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = InventoryMovement.query
    
    if product_id:
        query = query.filter_by(product_id=product_id)
    
    if movement_type:
        query = query.filter_by(movement_type=movement_type)
    
    if start_date:
        query = query.filter(InventoryMovement.movement_date >= start_date)
    
    if end_date:
        query = query.filter(InventoryMovement.movement_date <= end_date)
    
    movements = query.order_by(InventoryMovement.movement_date.desc()).all()
    
    return jsonify({
        'movements': [m.to_dict() for m in movements],
        'count': len(movements)
    }), 200


@bp.route('/adjust', methods=['POST'])
@jwt_required()
def adjust_inventory():
    """Manually adjust inventory quantity"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    if not all(k in data for k in ['product_id', 'adjustment', 'reason']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    product = Product.get_by_id(data['product_id'])
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        # Find or create inventory record
        inventory = Inventory.query.filter_by(
            product_id=data['product_id'],
            location=data.get('location', 'main')
        ).first()
        
        if not inventory:
            inventory = Inventory(
                product_id=data['product_id'],
                quantity=0,
                location=data.get('location', 'main')
            )
            inventory.save()
        
        # Adjust quantity
        inventory.quantity += data['adjustment']
        inventory.save()
        
        # Create movement record
        movement = InventoryMovement(
            product_id=data['product_id'],
            movement_type='adjustment',
            quantity=data['adjustment'],
            reason=data['reason'],
            performed_by=current_user_id,
            movement_date=datetime.utcnow()
        )
        movement.save()
        
        return jsonify({
            'message': 'Inventory adjusted successfully',
            'inventory': inventory.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500