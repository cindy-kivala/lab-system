from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, date, timedelta
from sqlalchemy import func
from app import db
from app.models.sale import Sale
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.purchase_order import PurchaseOrder
from app.models.production_batch import ProductionBatch

bp = Blueprint('dashboard', __name__)


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get main dashboard statistics"""
    
    # Today's sales
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales = Sale.query.filter(Sale.transaction_date >= today_start).all()
    today_revenue = sum(float(s.total_amount) for s in today_sales)
    
    # Low stock items
    low_stock_products = Product.get_low_stock_products()
    
    # Pending purchase orders
    pending_pos = PurchaseOrder.query.filter(
        PurchaseOrder.status.in_(['draft', 'submitted', 'confirmed'])
    ).count()
    
    # Expiring soon items (next 30 days)
    expiring_soon = Inventory.get_expiring_soon(30)
    
    # This week's sales trend
    week_ago = datetime.now() - timedelta(days=7)
    week_sales = Sale.query.filter(Sale.transaction_date >= week_ago).all()
    
    # Group sales by day
    daily_sales = {}
    for sale in week_sales:
        day = sale.transaction_date.strftime('%Y-%m-%d')
        if day not in daily_sales:
            daily_sales[day] = 0
        daily_sales[day] += float(sale.total_amount)
    
    # Top selling products (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    top_products_query = db.session.query(
        Product.name,
        func.sum(db.literal_column('sale_items.quantity')).label('total_sold')
    ).join(
        db.literal_column('sale_items'), Product.id == db.literal_column('sale_items.product_id')
    ).join(
        Sale, db.literal_column('sale_items.sale_id') == Sale.id
    ).filter(
        Sale.transaction_date >= thirty_days_ago
    ).group_by(Product.id).order_by(db.desc('total_sold')).limit(5)
    
    return jsonify({
        'today': {
            'revenue': today_revenue,
            'transactions': len(today_sales)
        },
        'alerts': {
            'low_stock_count': len(low_stock_products),
            'expiring_soon_count': len(expiring_soon),
            'pending_orders': pending_pos
        },
        'sales_trend': daily_sales,
        'week_revenue': sum(daily_sales.values())
    }), 200


@bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get all dashboard alerts"""
    
    # Low stock products
    low_stock = Product.get_low_stock_products()
    
    # Expiring soon (next 30 days)
    expiring_soon = Inventory.get_expiring_soon(30)
    
    # Expired items
    expired = Inventory.get_expired()
    
    # Overdue purchase orders
    overdue_pos = PurchaseOrder.query.filter(
        PurchaseOrder.status.in_(['submitted', 'confirmed']),
        PurchaseOrder.expected_delivery_date < date.today()
    ).all()
    
    # Pending QC batches (lab)
    pending_qc = ProductionBatch.query.filter_by(qc_status='pending').all()
    
    alerts = []
    
    # Add low stock alerts
    for product in low_stock:
        alerts.append({
            'type': 'low_stock',
            'severity': 'high' if product.total_stock == 0 else 'medium',
            'title': f'{product.name} - Low Stock',
            'message': f'Only {product.total_stock} units left. Reorder threshold: {product.reorder_threshold}',
            'product_id': product.id,
            'action': 'reorder'
        })
    
    # Add expiring soon alerts
    for inv in expiring_soon:
        days_left = inv.days_until_expiration
        severity = 'high' if days_left <= 7 else 'medium'
        alerts.append({
            'type': 'expiring_soon',
            'severity': severity,
            'title': f'{inv.product.name} - Expiring Soon',
            'message': f'Batch {inv.batch_number} expires in {days_left} days',
            'inventory_id': inv.id,
            'days_left': days_left
        })
    
    # Add expired alerts
    for inv in expired:
        alerts.append({
            'type': 'expired',
            'severity': 'critical',
            'title': f'{inv.product.name} - Expired',
            'message': f'Batch {inv.batch_number} expired. Remove from inventory.',
            'inventory_id': inv.id
        })
    
    # Add overdue PO alerts
    for po in overdue_pos:
        days_overdue = (date.today() - po.expected_delivery_date).days
        alerts.append({
            'type': 'overdue_po',
            'severity': 'medium',
            'title': f'PO {po.po_number} Overdue',
            'message': f'Expected {days_overdue} days ago from {po.supplier.name}',
            'po_id': po.id
        })
    
    # Add pending QC alerts
    for batch in pending_qc:
        alerts.append({
            'type': 'pending_qc',
            'severity': 'medium',
            'title': f'Batch {batch.batch_number} - QC Pending',
            'message': f'{batch.formulation.name} awaiting quality control',
            'batch_id': batch.id,
            'action': 'perform_qc'
        })
    
    # Sort by severity
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    alerts.sort(key=lambda x: severity_order.get(x['severity'], 99))
    
    return jsonify({
        'alerts': alerts,
        'count': len(alerts),
        'by_severity': {
            'critical': sum(1 for a in alerts if a['severity'] == 'critical'),
            'high': sum(1 for a in alerts if a['severity'] == 'high'),
            'medium': sum(1 for a in alerts if a['severity'] == 'medium'),
            'low': sum(1 for a in alerts if a['severity'] == 'low')
        }
    }), 200


@bp.route('/quick-stats', methods=['GET'])
@jwt_required()
def get_quick_stats():
    """Get quick stats for dashboard cards"""
    
    # Total products
    total_products = Product.query.filter_by(is_active=True).count()
    
    # Total inventory value
    inventory_value = 0
    for inv in Inventory.query.all():
        if inv.cost_per_unit:
            inventory_value += float(inv.cost_per_unit) * inv.quantity
    
    # This month's revenue
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_sales = Sale.query.filter(Sale.transaction_date >= month_start).all()
    month_revenue = sum(float(s.total_amount) for s in month_sales)
    
    # Lab batches this month
    month_batches = ProductionBatch.query.filter(
        ProductionBatch.production_date >= month_start.date()
    ).count()
    
    return jsonify({
        'total_products': total_products,
        'inventory_value': round(inventory_value, 2),
        'month_revenue': round(month_revenue, 2),
        'month_batches': month_batches
    }), 200
