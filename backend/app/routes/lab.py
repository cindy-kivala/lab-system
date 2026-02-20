from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime, timedelta
from app import db
from app.models.formulation import Formulation, FormulationIngredient
from app.models.production_batch import ProductionBatch, BatchIngredientUsed
from app.models.product import Product
from app.models.inventory import Inventory, InventoryMovement

bp = Blueprint('lab', __name__)


# FORMULATIONS

@bp.route('/formulations', methods=['GET'])
@jwt_required()
def get_formulations():
    """Get all formulations"""
    status = request.args.get('status')
    
    query = Formulation.query
    
    if status:
        query = query.filter_by(status=status)
    
    formulations = query.order_by(Formulation.created_at.desc()).all()
    
    return jsonify({
        'formulations': [f.to_dict() for f in formulations],
        'count': len(formulations)
    }), 200


@bp.route('/formulations/<int:formulation_id>', methods=['GET'])
@jwt_required()
def get_formulation(formulation_id):
    """Get single formulation"""
    formulation = Formulation.get_by_id(formulation_id)
    
    if not formulation:
        return jsonify({'error': 'Formulation not found'}), 404
    
    return jsonify(formulation.to_dict()), 200


@bp.route('/formulations', methods=['POST'])
@jwt_required()
def create_formulation():
    """Create new formulation"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['name', 'code', 'base_quantity', 'base_unit']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if code already exists
    if Formulation.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Formulation code already exists'}), 409
    
    try:
        formulation = Formulation(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            product_type=data.get('product_type'),
            base_quantity=data['base_quantity'],
            base_unit=data['base_unit'],
            instructions=data.get('instructions'),
            storage_conditions=data.get('storage_conditions'),
            shelf_life_days=data.get('shelf_life_days'),
            status=data.get('status', 'testing'),
            version=data.get('version', 1),
            created_by=current_user_id
        )
        
        formulation.save()
        
        # Add ingredients
        for ingredient in data.get('ingredients', []):
            form_ingredient = FormulationIngredient(
                formulation_id=formulation.id,
                ingredient_product_id=ingredient['ingredient_product_id'],
                quantity=ingredient['quantity'],
                unit=ingredient['unit'],
                percentage=ingredient.get('percentage'),
                notes=ingredient.get('notes'),
                sequence_order=ingredient.get('sequence_order')
            )
            form_ingredient.save()
        
        return jsonify({
            'message': 'Formulation created successfully',
            'formulation': formulation.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/formulations/<int:formulation_id>', methods=['PUT'])
@jwt_required()
def update_formulation(formulation_id):
    """Update formulation"""
    formulation = Formulation.get_by_id(formulation_id)
    
    if not formulation:
        return jsonify({'error': 'Formulation not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update fields
        if 'name' in data:
            formulation.name = data['name']
        if 'description' in data:
            formulation.description = data['description']
        if 'instructions' in data:
            formulation.instructions = data['instructions']
        if 'status' in data:
            formulation.status = data['status']
        
        formulation.save()
        
        return jsonify({
            'message': 'Formulation updated successfully',
            'formulation': formulation.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/formulations/<int:formulation_id>/approve', methods=['POST'])
@jwt_required()
def approve_formulation(formulation_id):
    """Approve formulation for production"""
    formulation = Formulation.get_by_id(formulation_id)
    
    if not formulation:
        return jsonify({'error': 'Formulation not found'}), 404
    
    current_user_id = get_jwt_identity()
    
    try:
        formulation.status = 'approved'
        formulation.approved_by = current_user_id
        formulation.approved_date = date.today()
        formulation.save()
        
        return jsonify({
            'message': 'Formulation approved successfully',
            'formulation': formulation.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


#  PRODUCTION BATCHES

@bp.route('/batches', methods=['GET'])
@jwt_required()
def get_batches():
    """Get all production batches"""
    formulation_id = request.args.get('formulation_id', type=int)
    qc_status = request.args.get('qc_status')
    start_date = request.args.get('start_date')
    
    query = ProductionBatch.query
    
    if formulation_id:
        query = query.filter_by(formulation_id=formulation_id)
    
    if qc_status:
        query = query.filter_by(qc_status=qc_status)
    
    if start_date:
        query = query.filter(ProductionBatch.production_date >= start_date)
    
    batches = query.order_by(ProductionBatch.production_date.desc()).all()
    
    return jsonify({
        'batches': [b.to_dict() for b in batches],
        'count': len(batches)
    }), 200


@bp.route('/batches/<int:batch_id>', methods=['GET'])
@jwt_required()
def get_batch(batch_id):
    """Get single production batch"""
    batch = ProductionBatch.get_by_id(batch_id)
    
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404
    
    return jsonify(batch.to_dict()), 200


@bp.route('/batches', methods=['POST'])
@jwt_required()
def create_batch():
    """Create new production batch"""
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Validate required fields
    required_fields = ['formulation_id', 'quantity_produced', 'unit']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get formulation
    formulation = Formulation.get_by_id(data['formulation_id'])
    if not formulation:
        return jsonify({'error': 'Formulation not found'}), 404
    
    if formulation.status != 'approved':
        return jsonify({'error': 'Only approved formulations can be produced'}), 400
    
    try:
        # Generate batch number
        batch_number = ProductionBatch.generate_batch_number()
        
        # Calculate expiration date
        production_date = data.get('production_date', date.today())
        if isinstance(production_date, str):
            production_date = datetime.strptime(production_date, '%Y-%m-%d').date()
        
        expiration_date = None
        if formulation.shelf_life_days:
            expiration_date = production_date + timedelta(days=formulation.shelf_life_days)
        
        # Create batch
        batch = ProductionBatch(
            batch_number=batch_number,
            formulation_id=data['formulation_id'],
            finished_product_id=data.get('finished_product_id'),
            production_date=production_date,
            quantity_produced=data['quantity_produced'],
            unit=data['unit'],
            expiration_date=expiration_date,
            production_notes=data.get('production_notes'),
            produced_by=current_user_id
        )
        
        batch.save()
        
        # Record ingredients used and deduct from inventory
        for ingredient_data in data.get('ingredients_used', []):
            batch_ingredient = BatchIngredientUsed(
                batch_id=batch.id,
                ingredient_product_id=ingredient_data['ingredient_product_id'],
                quantity_used=ingredient_data['quantity_used'],
                unit=ingredient_data['unit'],
                batch_number=ingredient_data.get('batch_number'),
                cost=ingredient_data.get('cost')
            )
            batch_ingredient.save()
            
            # Deduct from inventory
            inventory = Inventory.query.filter_by(
                product_id=ingredient_data['ingredient_product_id']
            ).first()
            
            if inventory:
                inventory.quantity -= float(ingredient_data['quantity_used'])
                inventory.save()
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=ingredient_data['ingredient_product_id'],
                movement_type='production',
                quantity=-float(ingredient_data['quantity_used']),
                reference_type='batch_id',
                reference_id=batch.id,
                reason=f'Used in batch {batch_number}',
                performed_by=current_user_id,
                movement_date=datetime.utcnow()
            )
            movement.save()
        
        # Calculate cost per unit
        batch.calculate_cost_per_unit()
        batch.save()
        
        # Add finished product to inventory if QC passed or auto-approve
        if data.get('auto_approve_qc'):
            batch.qc_status = 'passed'
            batch.qc_performed_by = current_user_id
            batch.qc_date = date.today()
            batch.save()
            
            # Add to inventory
            if batch.finished_product_id:
                inventory = Inventory(
                    product_id=batch.finished_product_id,
                    quantity=int(batch.quantity_produced),
                    location='main',
                    batch_number=batch_number,
                    expiration_date=expiration_date,
                    received_date=production_date,
                    cost_per_unit=batch.cost_per_unit
                )
                inventory.save()
        
        return jsonify({
            'message': 'Production batch created successfully',
            'batch': batch.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/batches/<int:batch_id>/qc', methods=['POST'])
@jwt_required()
def perform_qc(batch_id):
    """Perform quality control on batch"""
    batch = ProductionBatch.get_by_id(batch_id)
    
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404
    
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    try:
        batch.qc_status = data['qc_status']  # 'passed' or 'failed'
        batch.qc_performed_by = current_user_id
        batch.qc_date = date.today()
        batch.qc_notes = data.get('qc_notes')
        batch.save()
        
        # If passed, add to inventory
        if data['qc_status'] == 'passed' and batch.finished_product_id:
            inventory = Inventory(
                product_id=batch.finished_product_id,
                quantity=int(batch.quantity_produced),
                location='main',
                batch_number=batch.batch_number,
                expiration_date=batch.expiration_date,
                received_date=batch.production_date,
                cost_per_unit=batch.cost_per_unit
            )
            inventory.save()
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=batch.finished_product_id,
                movement_type='production',
                quantity=int(batch.quantity_produced),
                batch_number=batch.batch_number,
                reference_type='batch_id',
                reference_id=batch.id,
                reason=f'QC passed for batch {batch.batch_number}',
                performed_by=current_user_id,
                movement_date=datetime.utcnow()
            )
            movement.save()
        
        return jsonify({
            'message': f'QC {data["qc_status"]} successfully',
            'batch': batch.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/batches/pending-qc', methods=['GET'])
@jwt_required()
def get_pending_qc():
    """Get batches pending QC"""
    batches = ProductionBatch.query.filter_by(qc_status='pending').all()
    
    return jsonify({
        'batches': [b.to_dict() for b in batches],
        'count': len(batches)
    }), 200