from app import db
from app.models.base import BaseModel
from datetime import date, timedelta

class Inventory(BaseModel):
    """Inventory model for tracking stock levels"""
    
    __tablename__ = 'inventory'
    __table_args__ = (
        db.UniqueConstraint('product_id', 'batch_number', 'location', name='unique_product_batch_location'),
    )
    
    # Product reference
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # Stock details
    quantity = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(100), default='main')  # main, storage, lab, etc
    batch_number = db.Column(db.String(100))
    expiration_date = db.Column(db.Date)
    received_date = db.Column(db.Date)
    cost_per_unit = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Inventory {self.product.name if self.product else "Unknown"}: {self.quantity} units>'
    
    @property
    def is_expired(self):
        """Check if inventory item is expired"""
        if self.expiration_date:
            return self.expiration_date < date.today()
        return False
    
    @property
    def days_until_expiration(self):
        """Calculate days until expiration"""
        if self.expiration_date:
            delta = self.expiration_date - date.today()
            return delta.days
        return None
    
    @property
    def is_expiring_soon(self, days=30):
        """Check if item expires within specified days"""
        days_left = self.days_until_expiration
        if days_left is not None:
            return 0 <= days_left <= days
        return False
    
    def to_dict(self):
        data = super().to_dict()
        data['is_expired'] = self.is_expired
        data['days_until_expiration'] = self.days_until_expiration
        data['is_expiring_soon'] = self.is_expiring_soon()
        data['product_name'] = self.product.name if self.product else None
        data['product_sku'] = self.product.sku if self.product else None
        data['cost_per_unit'] = float(data['cost_per_unit']) if data['cost_per_unit'] else None
        return data
    
    @classmethod
    def get_expiring_soon(cls, days=30):
        """Get inventory items expiring within specified days"""
        threshold_date = date.today() + timedelta(days=days)
        return cls.query.filter(
            cls.expiration_date.isnot(None),
            cls.expiration_date > date.today(),
            cls.expiration_date <= threshold_date,
            cls.quantity > 0
        ).all()
    
    @classmethod
    def get_expired(cls):
        """Get all expired inventory items"""
        return cls.query.filter(
            cls.expiration_date < date.today(),
            cls.quantity > 0
        ).all()


class InventoryMovement(BaseModel):
    """Audit trail for inventory movements"""
    
    __tablename__ = 'inventory_movements'
    
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    movement_type = db.Column(db.String(50), nullable=False)  # sale, purchase, adjustment, production, waste, return
    quantity = db.Column(db.Integer, nullable=False)  # positive for additions, negative for reductions
    batch_number = db.Column(db.String(100))
    
    # Reference to source transaction
    reference_type = db.Column(db.String(50))  # sale_id, po_id, batch_id, adjustment_id
    reference_id = db.Column(db.Integer)
    
    reason = db.Column(db.Text)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    movement_date = db.Column(db.DateTime, nullable=False)
    
    # Relationship
    user = db.relationship('User', foreign_keys=[performed_by])
    
    def __repr__(self):
        return f'<InventoryMovement {self.movement_type}: {self.quantity} units of {self.product.name if self.product else "Unknown"}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['product_name'] = self.product.name if self.product else None
        data['product_sku'] = self.product.sku if self.product else None
        data['performed_by_name'] = self.user.full_name if self.user else None
        return data
