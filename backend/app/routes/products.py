from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.supplier import Supplier

bp = Blueprint('products', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_products():
    """Get all products with optional filtering"""
    # Query parameters
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    product_type = request.args.get('product_type')
    is_active = request.args.get('is_active', 'true').lower() == 'true'
    low_stock = request.args.get('low_stock', 'false').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Product.query
    
    if is_active:
        query = query.filter_by(is_active=True)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Product.name.ilike(search_pattern),
                Product.sku.ilike(search_pattern),
                Product.barcode.ilike(search_pattern)
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if product_type:
        query = query.filter_by(product_type=product_type)
    
    # Pagination
    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Filter for low stock if requested
    items = products.items
    if low_stock:
        items = [p for p in items if p.is_low_stock]
    
    return jsonify({
        'products': [p.to_dict() for p in items],
        'total': products.total,
        'pages': products.pages,
        'current_page': products.page
    }), 200


@bp.route('/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    """Get single product by ID"""
    product = Product.get_by_id(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(product.to_dict()), 200


@bp.route('/sku/<string:sku>', methods=['GET'])
@jwt_required()
def get_product_by_sku(sku):
    """Get product by SKU"""
    product = Product.get_by_sku(sku)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(product.to_dict()), 200


@bp.route('/barcode/<string:barcode>', methods=['GET'])
@jwt_required()
def get_product_by_barcode(barcode):
    """Get product by barcode"""
    product = Product.get_by_barcode(barcode)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(product.to_dict()), 200


@bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    """Create new product"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['sku', 'name', 'product_type', 'unit_price']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if SKU already exists
    if Product.get_by_sku(data['sku']):
        return jsonify({'error': 'SKU already exists'}), 409
    
    # Check if barcode already exists (if provided)
    if data.get('barcode') and Product.get_by_barcode(data['barcode']):
        return jsonify({'error': 'Barcode already exists'}), 409
    
    try:
        product = Product(
            sku=data['sku'],
            barcode=data.get('barcode'),
            name=data['name'],
            description=data.get('description'),
            category_id=data.get('category_id'),
            product_type=data['product_type'],
            unit_price=data['unit_price'],
            cost_price=data.get('cost_price'),
            unit_of_measure=data.get('unit_of_measure', 'unit'),
            reorder_threshold=data.get('reorder_threshold', 10),
            reorder_quantity=data.get('reorder_quantity', 50),
            max_stock_level=data.get('max_stock_level'),
            supplier_id=data.get('supplier_id'),
            supplier_sku=data.get('supplier_sku'),
            requires_prescription=data.get('requires_prescription', False),
            controlled_substance_schedule=data.get('controlled_substance_schedule'),
            is_lab_formulated=data.get('is_lab_formulated', False),
            formulation_id=data.get('formulation_id'),
            shelf_life_days=data.get('shelf_life_days'),
            created_by=current_user_id
        )
        
        product.save()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """Update product"""
    product = Product.get_by_id(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update fields if provided
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'category_id' in data:
            product.category_id = data['category_id']
        if 'unit_price' in data:
            product.unit_price = data['unit_price']
        if 'cost_price' in data:
            product.cost_price = data['cost_price']
        if 'reorder_threshold' in data:
            product.reorder_threshold = data['reorder_threshold']
        if 'reorder_quantity' in data:
            product.reorder_quantity = data['reorder_quantity']
        if 'max_stock_level' in data:
            product.max_stock_level = data['max_stock_level']
        if 'supplier_id' in data:
            product.supplier_id = data['supplier_id']
        if 'is_active' in data:
            product.is_active = data['is_active']
        
        product.save()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product': product.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """Soft delete product (set is_active to False)"""
    product = Product.get_by_id(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        product.is_active = False
        product.save()
        
        return jsonify({'message': 'Product deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/low-stock', methods=['GET'])
@jwt_required()
def get_low_stock_products():
    """Get all products below reorder threshold"""
    products = Product.get_low_stock_products()
    
    return jsonify({
        'products': [p.to_dict() for p in products],
        'count': len(products)
    }), 200


@bp.route('/search', methods=['GET'])
@jwt_required()
def search_products():
    """Search products"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    products = Product.search(query)
    
    return jsonify({
        'products': [p.to_dict() for p in products],
        'count': len(products)
    }), 200