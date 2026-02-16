from app import db
from app.models.base import BaseModel
from datetime import date

class Product(BaseModel):
    """Product model"""
    
    __tablename__ = 'products'
    
    # Identification
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(100), unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Categorization
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    product_type = db.Column(db.String(50), nullable=False)  # prescription, otc, lab_formulated, raw_material
    
    # Pricing
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2))
    
    # Inventory Settings
    unit_of_measure = db.Column(db.String(50), default='unit')
    reorder_threshold = db.Column(db.Integer, default=10)
    reorder_quantity = db.Column(db.Integer, default=50)
    max_stock_level = db.Column(db.Integer)
    
    # Supplier Info
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    supplier_sku = db.Column(db.String(100))
    
    # Prescription-specific
    requires_prescription = db.Column(db.Boolean, default=False)
    controlled_substance_schedule = db.Column(db.String(10))  # I, II, III, IV, V
    
    # Lab Product Specific
    is_lab_formulated = db.Column(db.Boolean, default=False)
    formulation_id = db.Column(db.Integer, db.ForeignKey('formulations.id'))
    shelf_life_days = db.Column(db.Integer)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    discontinued_date = db.Column(db.Date)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    inventory_records = db.relationship('Inventory', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    inventory_movements = db.relationship('InventoryMovement', backref='product', lazy='dynamic')
    sale_items = db.relationship('SaleItem', backref='product', lazy='dynamic')
    purchase_order_items = db.relationship('PurchaseOrderItem', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.sku}: {self.name}>'
    
    @property
    def total_stock(self):
        """Calculate total stock across all inventory records"""
        return sum(inv.quantity for inv in self.inventory_records.filter_by())
    
    @property
    def is_low_stock(self):
        """Check if product is below reorder threshold"""
        return self.total_stock <= self.reorder_threshold
    
    @property
    def stock_status(self):
        """Get stock status"""
        total = self.total_stock
        if total == 0:
            return 'out_of_stock'
        elif total <= self.reorder_threshold:
            return 'low_stock'
        elif self.max_stock_level and total >= self.max_stock_level:
            return 'overstock'
        else:
            return 'in_stock'
    
    def to_dict(self):
        data = super().to_dict()
        data['total_stock'] = self.total_stock
        data['is_low_stock'] = self.is_low_stock
        data['stock_status'] = self.stock_status
        data['category_name'] = self.category.name if self.category else None
        data['supplier_name'] = self.supplier.name if self.supplier else None
        # Convert Decimal to float for JSON serialization
        data['unit_price'] = float(data['unit_price']) if data['unit_price'] else None
        data['cost_price'] = float(data['cost_price']) if data['cost_price'] else None
        return data
    
    @classmethod
    def get_by_sku(cls, sku):
        """Get product by SKU"""
        return cls.query.filter_by(sku=sku).first()
    
    @classmethod
    def get_by_barcode(cls, barcode):
        """Get product by barcode"""
        return cls.query.filter_by(barcode=barcode).first()
    
    @classmethod
    def get_low_stock_products(cls):
        """Get all products below reorder threshold"""
        products = cls.query.filter_by(is_active=True).all()
        return [p for p in products if p.is_low_stock]
    
    @classmethod
    def search(cls, query):
        """Search products by name, SKU, or barcode"""
        search = f'%{query}%'
        return cls.query.filter(
            db.or_(
                cls.name.ilike(search),
                cls.sku.ilike(search),
                cls.barcode.ilike(search)
            )
        ).filter_by(is_active=True).all()
