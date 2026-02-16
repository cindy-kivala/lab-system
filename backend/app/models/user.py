from app import db
from app.models.base import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash

class User(BaseModel):
    """User model for authentication and authorization"""
    
    __tablename__ = 'users'
    
    # Basic Info
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    
    # Role & Status
    role = db.Column(db.String(50), nullable=False, default='admin')  # admin, pharmacist, staff, lab_tech
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    sales = db.relationship('Sale', backref='served_by_user', lazy='dynamic', foreign_keys='Sale.served_by')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary (exclude password)"""
        data = super().to_dict()
        data.pop('password_hash', None)
        return data
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def create_user(cls, email, password, full_name, role='admin'):
        """Create new user"""
        user = cls(email=email, full_name=full_name, role=role)
        user.set_password(password)
        user.save()
        return user
