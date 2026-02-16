from app import db
from app.models.base import BaseModel

class Supplier(BaseModel):
    """Supplier model"""
    
    __tablename__ = 'suppliers'
    
    # Basic Info
    name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    
    # Address
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    
    # Business Terms
    lead_time_days = db.Column(db.Integer, default=7)
    payment_terms = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='supplier', lazy='dynamic')
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['products_count'] = self.products.count()
        data['purchase_orders_count'] = self.purchase_orders.count()
        return data
