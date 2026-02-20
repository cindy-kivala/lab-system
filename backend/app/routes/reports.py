from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc
from app import db
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.purchase_order import PurchaseOrder
from app.models.production_batch import ProductionBatch

bp = Blueprint('reports', __name__)


@bp.route('/sales-summary', methods=['GET'])
@jwt_required()
def sales_summary():
    """Sales summary report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to last 30 days
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    sales = Sale.query.filter(
        Sale.transaction_date >= start_date,
        Sale.transaction_date <= end_date
    ).all()
    
    total_revenue = sum(float(s.total_amount) for s in sales)
    total_transactions = len(sales)
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
    
    # By payment method
    payment_breakdown = {}
    for sale in sales:
        method = sale.payment_method
        if method not in payment_breakdown:
            payment_breakdown[method] = {'count': 0, 'total': 0}
        payment_breakdown[method]['count'] += 1
        payment_breakdown[method]['total'] += float(sale.total_amount)
    
    # Daily breakdown
    daily_sales = {}
    for sale in sales:
        day = sale.transaction_date.strftime('%Y-%m-%d')
        if day not in daily_sales:
            daily_sales[day] = {'revenue': 0, 'transactions': 0}
        daily_sales[day]['revenue'] += float(sale.total_amount)
        daily_sales[day]['transactions'] += 1
    
    return jsonify({
        'period': {'start': start_date, 'end': end_date},
        'summary': {
            'total_revenue': round(total_revenue, 2),
            'total_transactions': total_transactions,
            'average_transaction': round(avg_transaction, 2)
        },
        'by_payment_method': payment_breakdown,
        'daily_breakdown': daily_sales
    }), 200


@bp.route('/top-products', methods=['GET'])
@jwt_required()
def top_products():
    """Top selling products report"""
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Query top products by quantity sold
    top_products_query = db.session.query(
        Product.id,
        Product.name,
        Product.sku,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.line_total).label('total_revenue'),
        func.count(SaleItem.id).label('transaction_count')
    ).join(SaleItem, Product.id == SaleItem.product_id
    ).join(Sale, SaleItem.sale_id == Sale.id
    ).filter(Sale.transaction_date >= start_date
    ).group_by(Product.id
    ).order_by(desc('total_quantity')
    ).limit(limit).all()
    
    products = []
    for row in top_products_query:
        products.append({
            'product_id': row.id,
            'name': row.name,
            'sku': row.sku,
            'quantity_sold': int(row.total_quantity),
            'revenue': float(row.total_revenue),
            'transactions': row.transaction_count
        })
    
    return jsonify({
        'period_days': days,
        'top_products': products
    }), 200


@bp.route('/inventory-valuation', methods=['GET'])
@jwt_required()
def inventory_valuation():
    """Inventory valuation report"""
    
    inventory_items = Inventory.query.filter(Inventory.quantity > 0).all()
    
    total_value = 0
    by_category = {}
    by_type = {}
    items = []
    
    for inv in inventory_items:
        if not inv.product or not inv.cost_per_unit:
            continue
        
        item_value = float(inv.cost_per_unit) * inv.quantity
        total_value += item_value
        
        # By category
        category_name = inv.product.category.name if inv.product.category else 'Uncategorized'
        if category_name not in by_category:
            by_category[category_name] = 0
        by_category[category_name] += item_value
        
        # By type
        product_type = inv.product.product_type
        if product_type not in by_type:
            by_type[product_type] = 0
        by_type[product_type] += item_value
        
        items.append({
            'product_name': inv.product.name,
            'sku': inv.product.sku,
            'quantity': inv.quantity,
            'cost_per_unit': float(inv.cost_per_unit),
            'total_value': round(item_value, 2),
            'location': inv.location,
            'batch_number': inv.batch_number
        })
    
    return jsonify({
        'total_value': round(total_value, 2),
        'by_category': {k: round(v, 2) for k, v in by_category.items()},
        'by_type': {k: round(v, 2) for k, v in by_type.items()},
        'items': items,
        'total_items': len(items)
    }), 200


@bp.route('/low-stock', methods=['GET'])
@jwt_required()
def low_stock_report():
    """Low stock report"""
    
    products = Product.get_low_stock_products()
    
    items = []
    for product in products:
        items.append({
            'product_id': product.id,
            'name': product.name,
            'sku': product.sku,
            'current_stock': product.total_stock,
            'reorder_threshold': product.reorder_threshold,
            'reorder_quantity': product.reorder_quantity,
            'supplier': product.supplier.name if product.supplier else None,
            'status': 'out_of_stock' if product.total_stock == 0 else 'low_stock'
        })
    
    return jsonify({
        'items': items,
        'count': len(items)
    }), 200


@bp.route('/expiring-items', methods=['GET'])
@jwt_required()
def expiring_items_report():
    """Expiring items report"""
    days = request.args.get('days', 30, type=int)
    
    expiring = Inventory.get_expiring_soon(days)
    expired = Inventory.get_expired()
    
    expiring_items = []
    for inv in expiring:
        expiring_items.append({
            'product_name': inv.product.name,
            'sku': inv.product.sku,
            'batch_number': inv.batch_number,
            'quantity': inv.quantity,
            'expiration_date': inv.expiration_date.isoformat() if inv.expiration_date else None,
            'days_until_expiration': inv.days_until_expiration,
            'location': inv.location,
            'estimated_value': float(inv.cost_per_unit * inv.quantity) if inv.cost_per_unit else 0
        })
    
    expired_items = []
    for inv in expired:
        expired_items.append({
            'product_name': inv.product.name,
            'sku': inv.product.sku,
            'batch_number': inv.batch_number,
            'quantity': inv.quantity,
            'expiration_date': inv.expiration_date.isoformat() if inv.expiration_date else None,
            'location': inv.location,
            'estimated_value': float(inv.cost_per_unit * inv.quantity) if inv.cost_per_unit else 0
        })
    
    return jsonify({
        'expiring_soon': {
            'days': days,
            'items': expiring_items,
            'count': len(expiring_items)
        },
        'expired': {
            'items': expired_items,
            'count': len(expired_items)
        }
    }), 200


@bp.route('/purchase-orders', methods=['GET'])
@jwt_required()
def purchase_orders_report():
    """Purchase orders report"""
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = PurchaseOrder.query
    
    if status:
        query = query.filter_by(status=status)
    
    if start_date:
        query = query.filter(PurchaseOrder.order_date >= start_date)
    
    if end_date:
        query = query.filter(PurchaseOrder.order_date <= end_date)
    
    pos = query.all()
    
    total_value = sum(float(po.total_amount) for po in pos if po.total_amount)
    
    by_supplier = {}
    by_status = {}
    
    for po in pos:
        # By supplier
        supplier_name = po.supplier.name if po.supplier else 'Unknown'
        if supplier_name not in by_supplier:
            by_supplier[supplier_name] = {'count': 0, 'total': 0}
        by_supplier[supplier_name]['count'] += 1
        by_supplier[supplier_name]['total'] += float(po.total_amount) if po.total_amount else 0
        
        # By status
        if po.status not in by_status:
            by_status[po.status] = 0
        by_status[po.status] += 1
    
    return jsonify({
        'summary': {
            'total_orders': len(pos),
            'total_value': round(total_value, 2)
        },
        'by_supplier': by_supplier,
        'by_status': by_status,
        'orders': [po.to_dict() for po in pos]
    }), 200


@bp.route('/lab-production', methods=['GET'])
@jwt_required()
def lab_production_report():
    """Lab production report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = ProductionBatch.query
    
    if start_date:
        query = query.filter(ProductionBatch.production_date >= start_date)
    
    if end_date:
        query = query.filter(ProductionBatch.production_date <= end_date)
    
    batches = query.all()
    
    total_batches = len(batches)
    total_units = sum(float(b.quantity_produced) for b in batches)
    
    by_formulation = {}
    by_qc_status = {'pending': 0, 'passed': 0, 'failed': 0}
    
    for batch in batches:
        # By formulation
        formula_name = batch.formulation.name if batch.formulation else 'Unknown'
        if formula_name not in by_formulation:
            by_formulation[formula_name] = {'batches': 0, 'units': 0}
        by_formulation[formula_name]['batches'] += 1
        by_formulation[formula_name]['units'] += float(batch.quantity_produced)
        
        # By QC status
        by_qc_status[batch.qc_status] += 1
    
    return jsonify({
        'summary': {
            'total_batches': total_batches,
            'total_units_produced': round(total_units, 2),
            'qc_pass_rate': round((by_qc_status['passed'] / total_batches * 100) if total_batches > 0 else 0, 2)
        },
        'by_formulation': by_formulation,
        'by_qc_status': by_qc_status,
        'batches': [b.to_dict() for b in batches]
    }), 200


@bp.route('/profitability', methods=['GET'])
@jwt_required()
def profitability_report():
    """Product profitability analysis"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get sales with product details
    sales_data = db.session.query(
        Product.id,
        Product.name,
        Product.sku,
        Product.cost_price,
        Product.unit_price,
        func.sum(SaleItem.quantity).label('quantity_sold'),
        func.sum(SaleItem.line_total).label('revenue')
    ).join(SaleItem, Product.id == SaleItem.product_id
    ).join(Sale, SaleItem.sale_id == Sale.id
    ).filter(Sale.transaction_date >= start_date
    ).group_by(Product.id
    ).all()
    
    products = []
    total_revenue = 0
    total_profit = 0
    
    for row in sales_data:
        if not row.cost_price:
            continue
        
        revenue = float(row.revenue)
        cost = float(row.cost_price) * int(row.quantity_sold)
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0
        
        total_revenue += revenue
        total_profit += profit
        
        products.append({
            'product_id': row.id,
            'name': row.name,
            'sku': row.sku,
            'quantity_sold': int(row.quantity_sold),
            'revenue': round(revenue, 2),
            'cost': round(cost, 2),
            'profit': round(profit, 2),
            'margin_percent': round(margin, 2)
        })
    
    # Sort by profit
    products.sort(key=lambda x: x['profit'], reverse=True)
    
    return jsonify({
        'period_days': days,
        'summary': {
            'total_revenue': round(total_revenue, 2),
            'total_profit': round(total_profit, 2),
            'overall_margin': round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 2)
        },
        'products': products
    }), 200