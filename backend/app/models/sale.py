from app import db
from app.models.base import BaseModel
from datetime import datetime

class Sale(BaseModel):
    """Sales transaction model"""
    
    __tablename__ = 'sales'
    
    # Transaction Info
    sale_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Customer Info (optional for walk-ins)
    customer_name = db.Column(db.String(255))
    customer_phone = db.Column(db.String(50))
    customer_email = db.Column(db.String(255))
    
    # Totals
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=False)  # cash, card, mobile_money, insurance
    payment_status = db.Column(db.String(50), default='completed')  # completed, pending, refunded
    
    # Prescription Info
    prescription_number = db.Column(db.String(100))
    prescriber_name = db.Column(db.String(255))
    
    # Metadata
    sale_type = db.Column(db.String(50), default='in_store')  # in_store, online, delivery
    notes = db.Column(db.Text)
    served_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Sale {self.sale_number}: ${self.total_amount}>'
    
    @property
    def items_count(self):
        """Count total items in sale"""
        return sum(item.quantity for item in self.items)
    
    def to_dict(self):
        data = super().to_dict()
        data['items_count'] = self.items_count
        data['items'] = [item.to_dict() for item in self.items]
        data['served_by_name'] = self.served_by_user.full_name if self.served_by_user else None
        # Convert Decimal to float
        data['subtotal'] = float(data['subtotal'])
        data['tax_amount'] = float(data['tax_amount'])
        data['discount_amount'] = float(data['discount_amount'])
        data['total_amount'] = float(data['total_amount'])
        return data
    
    @classmethod
    def generate_sale_number(cls):
        """Generate unique sale number"""
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get count of sales today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = cls.query.filter(cls.transaction_date >= today_start).count()
        
        return f'SALE-{date_str}-{count + 1:04d}'


class SaleItem(BaseModel):
    """Individual items in a sale"""
    
    __tablename__ = 'sale_items'
    
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    batch_number = db.Column(db.String(100))
    is_prescription = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<SaleItem {self.product.name if self.product else "Unknown"}: {self.quantity}x @ ${self.unit_price}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['product_name'] = self.product.name if self.product else None
        data['product_sku'] = self.product.sku if self.product else None
        # Convert Decimal to float
        data['unit_price'] = float(data['unit_price'])
        data['discount_amount'] = float(data['discount_amount'])
        data['line_total'] = float(data['line_total'])
        return data
