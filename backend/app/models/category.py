from app import db
from app.models.base import BaseModel

class Category(BaseModel):
    """Product category model"""
    
    __tablename__ = 'categories'
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    
    # Self-referential relationship for subcategories
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side='Category.id'))
    
    # Products in this category
    products = db.relationship('Product', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        data = super().to_dict()
        data['subcategories_count'] = self.subcategories.count() if hasattr(self, 'subcategories') else 0
        data['products_count'] = self.products.count()
        return data
