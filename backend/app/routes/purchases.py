from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime
from app import db
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.inventory import Inventory, InventoryMovement

bp = Blueprint('purchases', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_purchase_orders():
    """Get all purchase orders"""
    status = request.args.get('status')
    supplier_id = request.args.get('supplier_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = PurchaseOrder.query
    
    if status:
        query = query.filter_by(status=status)
    
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    
    pos = query.order_by(PurchaseOrder.order_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'purchase_orders': [po.to_dict() for po in pos.items],
        'total': pos.total,
        'pages': pos.pages,
        'current_page': pos.page
    }), 200


@bp.route('/<int:po_id>', methods=['GET'])
@jwt_required()
def get_purchase_order(po_id):
    """Get single purchase order"""
    po = PurchaseOrder.get_by_id(po_id)
    
    if not po:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    return jsonify(po.to_dict()), 200


@bp.route('/', methods=['POST'])
@jwt_required()
def create_purchase_order():
    """Create new purchase order"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    if not data.get('supplier_id'):
        return jsonify({'error': 'Supplier is required'}), 400
    
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'PO must have at least one item'}), 400
    
    # Check supplier exists
    supplier = Supplier.get_by_id(data['supplier_id'])
    if not supplier:
        return jsonify({'error': 'Supplier not found'}), 404
    
    try:
        # Generate PO number
        po_number = PurchaseOrder.generate_po_number()
        
        # Create PO
        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=data['supplier_id'],
            order_date=data.get('order_date', date.today()),
            expected_delivery_date=data.get('expected_delivery_date'),
            status=data.get('status', 'draft'),
            tax_amount=data.get('tax_amount', 0),
            shipping_cost=data.get('shipping_cost', 0),
            notes=data.get('notes'),
            created_by=current_user_id
        )
        
        po.save()
        
        # Create PO items
        for item in data['items']:
            product = Product.get_by_id(item['product_id'])
            if not product:
                raise ValueError(f'Product {item["product_id"]} not found')
            
            unit_cost = item.get('unit_cost', float(product.cost_price) if product.cost_price else 0)
            line_total = unit_cost * item['quantity_ordered']
            
            po_item = PurchaseOrderItem(
                po_id=po.id,
                product_id=item['product_id'],
                quantity_ordered=item['quantity_ordered'],
                unit_cost=unit_cost,
                line_total=line_total
            )
            po_item.save()
        
        # Calculate totals
        po.calculate_totals()
        po.save()
        
        return jsonify({
            'message': 'Purchase order created successfully',
            'purchase_order': po.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:po_id>', methods=['PUT'])
@jwt_required()
def update_purchase_order(po_id):
    """Update purchase order"""
    po = PurchaseOrder.get_by_id(po_id)
    
    if not po:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if po.status in ['received', 'cancelled']:
        return jsonify({'error': 'Cannot update received or cancelled PO'}), 400
    
    data = request.get_json()
    
    try:
        # Update fields
        if 'expected_delivery_date' in data:
            po.expected_delivery_date = data['expected_delivery_date']
        if 'status' in data:
            po.status = data['status']
        if 'notes' in data:
            po.notes = data['notes']
        if 'tax_amount' in data:
            po.tax_amount = data['tax_amount']
        if 'shipping_cost' in data:
            po.shipping_cost = data['shipping_cost']
        
        # Recalculate totals
        po.calculate_totals()
        po.save()
        
        return jsonify({
            'message': 'Purchase order updated successfully',
            'purchase_order': po.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:po_id>/receive', methods=['POST'])
@jwt_required()
def receive_purchase_order(po_id):
    """Receive items from purchase order"""
    po = PurchaseOrder.get_by_id(po_id)
    
    if not po:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if po.status == 'received':
        return jsonify({'error': 'PO already fully received'}), 400
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    try:
        # Receive items
        for item_data in data.get('items', []):
            po_item = PurchaseOrderItem.get_by_id(item_data['po_item_id'])
            
            if not po_item or po_item.po_id != po.id:
                continue
            
            quantity_received = item_data['quantity_received']
            
            # Update PO item
            po_item.quantity_received += quantity_received
            po_item.batch_number = item_data.get('batch_number')
            po_item.expiration_date = item_data.get('expiration_date')
            po_item.received_date = date.today()
            po_item.save()
            
            # Add to inventory
            inventory = Inventory(
                product_id=po_item.product_id,
                quantity=quantity_received,
                location=item_data.get('location', 'main'),
                batch_number=item_data.get('batch_number'),
                expiration_date=item_data.get('expiration_date'),
                received_date=date.today(),
                cost_per_unit=po_item.unit_cost
            )
            inventory.save()
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=po_item.product_id,
                movement_type='purchase',
                quantity=quantity_received,
                batch_number=item_data.get('batch_number'),
                reference_type='po_id',
                reference_id=po.id,
                reason=f'Received from PO {po.po_number}',
                performed_by=current_user_id,
                movement_date=datetime.utcnow()
            )
            movement.save()
        
        # Check if all items fully received
        all_received = all(item.is_fully_received for item in po.items)
        
        if all_received:
            po.status = 'received'
            po.actual_delivery_date = date.today()
        else:
            po.status = 'confirmed'
        
        po.save()
        
        return jsonify({
            'message': 'Items received successfully',
            'purchase_order': po.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:po_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_purchase_order(po_id):
    """Cancel purchase order"""
    po = PurchaseOrder.get_by_id(po_id)
    
    if not po:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if po.status == 'received':
        return jsonify({'error': 'Cannot cancel received PO'}), 400
    
    try:
        po.status = 'cancelled'
        po.save()
        
        return jsonify({
            'message': 'Purchase order cancelled successfully',
            'purchase_order': po.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/pending', methods=['GET'])
@jwt_required()
def get_pending_orders():
    """Get pending purchase orders"""
    pos = PurchaseOrder.query.filter(
        PurchaseOrder.status.in_(['draft', 'submitted', 'confirmed'])
    ).all()
    
    return jsonify({
        'purchase_orders': [po.to_dict() for po in pos],
        'count': len(pos)
    }), 200


@bp.route('/overdue', methods=['GET'])
@jwt_required()
def get_overdue_orders():
    """Get overdue purchase orders"""
    pos = PurchaseOrder.query.filter(
        PurchaseOrder.status.in_(['submitted', 'confirmed']),
        PurchaseOrder.expected_delivery_date < date.today()
    ).all()
    
    return jsonify({
        'purchase_orders': [po.to_dict() for po in pos],
        'count': len(pos)
    }), 200