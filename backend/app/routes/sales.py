from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from app import db
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import Inventory, InventoryMovement

bp = Blueprint('sales', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_sales():
    """Get all sales with optional filtering"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    payment_method = request.args.get('payment_method')
    customer_email = request.args.get('customer_email')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Sale.query
    
    if start_date:
        query = query.filter(Sale.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Sale.transaction_date <= end_date)
    
    if payment_method:
        query = query.filter_by(payment_method=payment_method)
    
    if customer_email:
        query = query.filter_by(customer_email=customer_email)
    
    sales = query.order_by(Sale.transaction_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'sales': [s.to_dict() for s in sales.items],
        'total': sales.total,
        'pages': sales.pages,
        'current_page': sales.page
    }), 200


@bp.route('/<int:sale_id>', methods=['GET'])
@jwt_required()
def get_sale(sale_id):
    """Get single sale by ID"""
    sale = Sale.get_by_id(sale_id)
    
    if not sale:
        return jsonify({'error': 'Sale not found'}), 404
    
    return jsonify(sale.to_dict()), 200


@bp.route('/', methods=['POST'])
@jwt_required()
def create_sale():
    """Create new sale (POS transaction)"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'Sale must have at least one item'}), 400
    
    if not data.get('payment_method'):
        return jsonify({'error': 'Payment method is required'}), 400
    
    try:
        # Generate sale number
        sale_number = Sale.generate_sale_number()
        
        # Calculate totals
        subtotal = 0
        items_data = []
        
        # Validate items and check stock
        for item in data['items']:
            product = Product.get_by_id(item['product_id'])
            if not product:
                return jsonify({'error': f'Product {item["product_id"]} not found'}), 404
            
            if product.total_stock < item['quantity']:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            unit_price = item.get('unit_price', float(product.unit_price))
            discount = item.get('discount_amount', 0)
            line_total = (unit_price * item['quantity']) - discount
            subtotal += line_total
            
            items_data.append({
                'product_id': item['product_id'],
                'product': product,
                'quantity': item['quantity'],
                'unit_price': unit_price,
                'discount_amount': discount,
                'line_total': line_total,
                'is_prescription': item.get('is_prescription', False)
            })
        
        # Calculate final total
        tax_amount = data.get('tax_amount', 0)
        discount_amount = data.get('discount_amount', 0)
        total_amount = subtotal + tax_amount - discount_amount
        
        # Create sale
        sale = Sale(
            sale_number=sale_number,
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone'),
            customer_email=data.get('customer_email'),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            payment_method=data['payment_method'],
            payment_status=data.get('payment_status', 'completed'),
            prescription_number=data.get('prescription_number'),
            prescriber_name=data.get('prescriber_name'),
            sale_type=data.get('sale_type', 'in_store'),
            notes=data.get('notes'),
            served_by=current_user_id
        )
        
        sale.save()
        
        # Create sale items and update inventory
        for item_data in items_data:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                discount_amount=item_data['discount_amount'],
                line_total=item_data['line_total'],
                is_prescription=item_data['is_prescription']
            )
            sale_item.save()
            
            # Deduct from inventory (FIFO - oldest first)
            remaining_qty = item_data['quantity']
            inventory_records = Inventory.query.filter_by(
                product_id=item_data['product_id']
            ).filter(Inventory.quantity > 0).order_by(Inventory.expiration_date).all()
            
            for inv in inventory_records:
                if remaining_qty <= 0:
                    break
                
                deduct_qty = min(inv.quantity, remaining_qty)
                inv.quantity -= deduct_qty
                inv.save()
                remaining_qty -= deduct_qty
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=item_data['product_id'],
                movement_type='sale',
                quantity=-item_data['quantity'],
                reference_type='sale_id',
                reference_id=sale.id,
                reason=f'Sale {sale_number}',
                performed_by=current_user_id,
                movement_date=datetime.utcnow()
            )
            movement.save()
        
        return jsonify({
            'message': 'Sale completed successfully',
            'sale': sale.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_sales():
    """Get today's sales summary"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    sales = Sale.query.filter(Sale.transaction_date >= today_start).all()
    
    total_sales = sum(float(s.total_amount) for s in sales)
    total_transactions = len(sales)
    
    return jsonify({
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'average_transaction': total_sales / total_transactions if total_transactions > 0 else 0,
        'sales': [s.to_dict() for s in sales]
    }), 200


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_sales_stats():
    """Get sales statistics for a date range"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    sales = Sale.query.filter(Sale.transaction_date >= start_date).all()
    
    total_revenue = sum(float(s.total_amount) for s in sales)
    total_transactions = len(sales)
    
    # Group by payment method
    payment_breakdown = {}
    for sale in sales:
        method = sale.payment_method
        if method not in payment_breakdown:
            payment_breakdown[method] = {'count': 0, 'total': 0}
        payment_breakdown[method]['count'] += 1
        payment_breakdown[method]['total'] += float(sale.total_amount)
    
    return jsonify({
        'period_days': days,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'average_transaction': total_revenue / total_transactions if total_transactions > 0 else 0,
        'payment_breakdown': payment_breakdown
    }), 200


@bp.route('/<int:sale_id>/refund', methods=['POST'])
@jwt_required()
def refund_sale(sale_id):
    """Refund a sale"""
    sale = Sale.get_by_id(sale_id)
    
    if not sale:
        return jsonify({'error': 'Sale not found'}), 404
    
    if sale.payment_status == 'refunded':
        return jsonify({'error': 'Sale already refunded'}), 400
    
    current_user_id = get_jwt_identity()
    
    try:
        # Update sale status
        sale.payment_status = 'refunded'
        sale.save()
        
        # Return items to inventory
        for item in sale.items:
            # Find inventory record or create new one
            inventory = Inventory.query.filter_by(
                product_id=item.product_id,
                location='main'
            ).first()
            
            if inventory:
                inventory.quantity += item.quantity
                inventory.save()
            else:
                inventory = Inventory(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    location='main'
                )
                inventory.save()
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=item.product_id,
                movement_type='return',
                quantity=item.quantity,
                reference_type='sale_id',
                reference_id=sale.id,
                reason=f'Refund for sale {sale.sale_number}',
                performed_by=current_user_id,
                movement_date=datetime.utcnow()
            )
            movement.save()
        
        return jsonify({
            'message': 'Sale refunded successfully',
            'sale': sale.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500