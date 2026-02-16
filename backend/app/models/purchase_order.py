from app import db
from app.models.base import BaseModel
from datetime import datetime, date

class PurchaseOrder(BaseModel):
    """Purchase Order model"""
    
    __tablename__ = 'purchase_orders'
    
    # PO Info
    po_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    # Dates
    order_date = db.Column(db.Date, nullable=False)
    expected_delivery_date = db.Column(db.Date)
    actual_delivery_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(50), nullable=False, default='draft')  # draft, submitted, confirmed, received, cancelled
    
    # Totals
    subtotal = db.Column(db.Numeric(10, 2))
    tax_amount = db.Column(db.Numeric(10, 2))
    shipping_cost = db.Column(db.Numeric(10, 2))
    total_amount = db.Column(db.Numeric(10, 2))
    
    # Metadata
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_number}: {self.status}>'
    
    @property
    def items_count(self):
        """Count total items in PO"""
        return self.items.count()
    
    @property
    def is_overdue(self):
        """Check if PO is overdue"""
        if self.expected_delivery_date and self.status not in ['received', 'cancelled']:
            return self.expected_delivery_date < date.today()
        return False
    
    def calculate_totals(self):
        """Calculate PO totals from items"""
        self.subtotal = sum(item.line_total for item in self.items)
        self.total_amount = self.subtotal + (self.tax_amount or 0) + (self.shipping_cost or 0)
    
    def to_dict(self):
        data = super().to_dict()
        data['items_count'] = self.items_count
        data['is_overdue'] = self.is_overdue
        data['items'] = [item.to_dict() for item in self.items]
        data['supplier_name'] = self.supplier.name if self.supplier else None
        data['created_by_name'] = self.creator.full_name if self.creator else None
        # Convert Decimal to float
        data['subtotal'] = float(data['subtotal']) if data['subtotal'] else 0
        data['tax_amount'] = float(data['tax_amount']) if data['tax_amount'] else 0
        data['shipping_cost'] = float(data['shipping_cost']) if data['shipping_cost'] else 0
        data['total_amount'] = float(data['total_amount']) if data['total_amount'] else 0
        return data
    
    @classmethod
    def generate_po_number(cls):
        """Generate unique PO number"""
        date_str = datetime.now().strftime('%Y%m%d')
        count = cls.query.filter(cls.po_number.like(f'PO-{date_str}%')).count()
        return f'PO-{date_str}-{count + 1:04d}'


class PurchaseOrderItem(BaseModel):
    """Individual items in a purchase order"""
    
    __tablename__ = 'purchase_order_items'
    
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # Quantities
    quantity_ordered = db.Column(db.Integer, nullable=False)
    quantity_received = db.Column(db.Integer, default=0)
    
    # Pricing
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Receiving Info
    batch_number = db.Column(db.String(100))
    expiration_date = db.Column(db.Date)
    received_date = db.Column(db.Date)
    
    def __repr__(self):
        return f'<PurchaseOrderItem {self.product.name if self.product else "Unknown"}: {self.quantity_ordered} ordered>'
    
    @property
    def is_fully_received(self):
        """Check if item is fully received"""
        return self.quantity_received >= self.quantity_ordered
    
    @property
    def quantity_pending(self):
        """Calculate pending quantity"""
        return self.quantity_ordered - self.quantity_received
    
    def to_dict(self):
        data = super().to_dict()
        data['product_name'] = self.product.name if self.product else None
        data['product_sku'] = self.product.sku if self.product else None
        data['is_fully_received'] = self.is_fully_received
        data['quantity_pending'] = self.quantity_pending
        # Convert Decimal to float
        data['unit_cost'] = float(data['unit_cost'])
        data['line_total'] = float(data['line_total'])
        return data
