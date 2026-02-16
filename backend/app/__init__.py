from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Register blueprints (API routes)
    from app.routes import auth, products, inventory, sales, purchases, lab, reports, dashboard
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(products.bp, url_prefix='/api/products')
    app.register_blueprint(inventory.bp, url_prefix='/api/inventory')
    app.register_blueprint(sales.bp, url_prefix='/api/sales')
    app.register_blueprint(purchases.bp, url_prefix='/api/purchases')
    app.register_blueprint(lab.bp, url_prefix='/api/lab')
    app.register_blueprint(reports.bp, url_prefix='/api/reports')
    app.register_blueprint(dashboard.bp, url_prefix='/api/dashboard')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'version': app.config['APP_VERSION']}, 200
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': app.config['APP_NAME'],
            'version': app.config['APP_VERSION'],
            'status': 'running'
        }, 200
    
    return app
