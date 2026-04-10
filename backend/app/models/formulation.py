from app import db
from app.models.base import BaseModel
from datetime import date

class Formulation(BaseModel):
    """Lab formulation/recipe model"""
    
    __tablename__ = 'formulations'
    
    # Basic Info
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    product_type = db.Column(db.String(100))  # cream, ointment, lotion, etc
    
    # Batch Info
    base_quantity = db.Column(db.Numeric(10, 2), nullable=False)  # e.g., 100g, 500ml
    base_unit = db.Column(db.String(50), nullable=False)  # g, ml, etc
    
    # Production Details
    instructions = db.Column(db.Text)  # Production instructions
    storage_conditions = db.Column(db.Text)
    shelf_life_days = db.Column(db.Integer)
    
    # Status & Versioning
    status = db.Column(db.String(50), default='testing')  # testing, approved, discontinued
    version = db.Column(db.Integer, default=1)
    
    # Approval
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_date = db.Column(db.Date)
    
    # Relationships
    ingredients = db.relationship('FormulationIngredient', backref='formulation', lazy='dynamic', cascade='all, delete-orphan')
    production_batches = db.relationship('ProductionBatch', backref='formulation', lazy='dynamic')
    products = db.relationship('Product', backref='formulation', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<Formulation {self.code}: {self.name}>'
    
    @property
    def ingredient_count(self):
        """Count ingredients in formulation"""
        return self.ingredients.count()
    
    @property
    def total_cost(self):
        """Calculate total cost of ingredients for base quantity"""
        total = 0
        for ingredient in self.ingredients:
            if ingredient.ingredient_product and ingredient.ingredient_product.cost_price:
                total += float(ingredient.ingredient_product.cost_price) * float(ingredient.quantity)
        return total
    
    def to_dict(self):
        data = super().to_dict()
        data['ingredient_count'] = self.ingredient_count
        data['total_cost'] = self.total_cost
        data['ingredients'] = [ing.to_dict() for ing in self.ingredients]
        data['created_by_name'] = self.creator.full_name if self.creator else None
        data['approved_by_name'] = self.approver.full_name if self.approver else None
        data['base_quantity'] = float(data['base_quantity'])
        return data


class FormulationIngredient(BaseModel):
    """Ingredients in a formulation"""
    
    __tablename__ = 'formulation_ingredients'
    
    formulation_id = db.Column(db.Integer, db.ForeignKey('formulations.id'), nullable=False)
    ingredient_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # links to raw materials
    
    quantity = db.Column(db.Numeric(10, 4), nullable=False)
    unit = db.Column(db.String(50), nullable=False)  # g, mg, ml, etc
    percentage = db.Column(db.Numeric(5, 2))  # percentage of total
    notes = db.Column(db.Text)
    sequence_order = db.Column(db.Integer)  # order to add ingredients
    
    # Relationship
    ingredient_product = db.relationship('Product', foreign_keys=[ingredient_product_id])
    
    def __repr__(self):
        return f'<FormulationIngredient {self.ingredient_product.name if self.ingredient_product else "Unknown"}: {self.quantity}{self.unit}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['ingredient_name'] = self.ingredient_product.name if self.ingredient_product else None
        data['ingredient_sku'] = self.ingredient_product.sku if self.ingredient_product else None
        data['quantity'] = float(data['quantity'])
        data['percentage'] = float(data['percentage']) if data['percentage'] else None
        return data
