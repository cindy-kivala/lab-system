from app import db
from app.models.base import BaseModel
from datetime import datetime, date

class ProductionBatch(BaseModel):
    """Lab production batch tracking"""
    
    __tablename__ = 'production_batches'
    
    # Batch Info
    batch_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    formulation_id = db.Column(db.Integer, db.ForeignKey('formulations.id'), nullable=False)
    finished_product_id = db.Column(db.Integer, db.ForeignKey('products.id'))  # the final product created
    
    # Production Details
    production_date = db.Column(db.Date, nullable=False)
    quantity_produced = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    expiration_date = db.Column(db.Date)
    
    # Quality Control
    qc_status = db.Column(db.String(50), default='pending')  # pending, passed, failed
    qc_performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    qc_date = db.Column(db.Date)
    qc_notes = db.Column(db.Text)
    
    # Production Metadata
    produced_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    production_notes = db.Column(db.Text)
    cost_per_unit = db.Column(db.Numeric(10, 2))
    
    # Relationships
    ingredients_used = db.relationship('BatchIngredientUsed', backref='batch', lazy='dynamic', cascade='all, delete-orphan')
    producer = db.relationship('User', foreign_keys=[produced_by])
    qc_performer = db.relationship('User', foreign_keys=[qc_performed_by])
    finished_product = db.relationship('Product', foreign_keys=[finished_product_id])
    
    def __repr__(self):
        return f'<ProductionBatch {self.batch_number}: {self.qc_status}>'
    
    @property
    def is_qc_approved(self):
        """Check if batch passed QC"""
        return self.qc_status == 'passed'
    
    @property
    def total_cost(self):
        """Calculate total production cost"""
        return sum(float(ing.cost or 0) for ing in self.ingredients_used)
    
    def calculate_cost_per_unit(self):
        """Calculate cost per unit based on ingredients used"""
        if self.quantity_produced and self.quantity_produced > 0:
            self.cost_per_unit = self.total_cost / float(self.quantity_produced)
        return self.cost_per_unit
    
    def to_dict(self):
        data = super().to_dict()
        data['is_qc_approved'] = self.is_qc_approved
        data['total_cost'] = self.total_cost
        data['formulation_name'] = self.formulation.name if self.formulation else None
        data['formulation_code'] = self.formulation.code if self.formulation else None
        data['finished_product_name'] = self.finished_product.name if self.finished_product else None
        data['produced_by_name'] = self.producer.full_name if self.producer else None
        data['qc_performed_by_name'] = self.qc_performer.full_name if self.qc_performer else None
        data['ingredients_used'] = [ing.to_dict() for ing in self.ingredients_used]
        data['quantity_produced'] = float(data['quantity_produced'])
        data['cost_per_unit'] = float(data['cost_per_unit']) if data['cost_per_unit'] else None
        return data
    
    @classmethod
    def generate_batch_number(cls):
        """Generate unique batch number"""
        date_str = datetime.now().strftime('%Y%m%d')
        count = cls.query.filter(cls.batch_number.like(f'B-{date_str}%')).count()
        return f'B-{date_str}-{count + 1:04d}'


class BatchIngredientUsed(BaseModel):
    """Tracks actual ingredients used in production batch"""
    
    __tablename__ = 'batch_ingredients_used'
    
    batch_id = db.Column(db.Integer, db.ForeignKey('production_batches.id'), nullable=False)
    ingredient_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity_used = db.Column(db.Numeric(10, 4), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    batch_number = db.Column(db.String(100))  # batch number of the ingredient used
    cost = db.Column(db.Numeric(10, 2))  # total cost of this ingredient
    
    # Relationship
    ingredient_product = db.relationship('Product', foreign_keys=[ingredient_product_id])
    
    def __repr__(self):
        return f'<BatchIngredientUsed {self.ingredient_product.name if self.ingredient_product else "Unknown"}: {self.quantity_used}{self.unit}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['ingredient_name'] = self.ingredient_product.name if self.ingredient_product else None
        data['ingredient_sku'] = self.ingredient_product.sku if self.ingredient_product else None
        data['quantity_used'] = float(data['quantity_used'])
        data['cost'] = float(data['cost']) if data['cost'] else None
        return data
