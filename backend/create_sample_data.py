from app import create_app, db
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.inventory import Inventory
from datetime import date, timedelta

app = create_app()

with app.app_context():
    print("🚀 Creating sample data...\n")
    
    # Create Categories
    print("📁 Creating categories...")
    categories = [
        Category(name='Prescription Drugs', description='Requires prescription'),
        Category(name='Over-the-Counter', description='No prescription needed'),
        Category(name='Lab Products', description='Formulated in-house'),
        Category(name='Raw Materials', description='For lab production')
    ]
    
    for cat in categories:
        db.session.add(cat)
    db.session.commit()
    print(f"   ✅ Created {len(categories)} categories")
    
    # Create Suppliers
    print("\n🏢 Creating suppliers...")
    suppliers = [
        Supplier(
            name='MediSupply Kenya Ltd',
            contact_person='John Kamau',
            email='john@medisupply.co.ke',
            phone='+254712345678',
            city='Nairobi',
            country='Kenya',
            lead_time_days=7
        ),
        Supplier(
            name='PharmaDist East Africa',
            contact_person='Jane Wanjiku',
            email='jane@pharmadist.co.ke',
            phone='+254787654321',
            city='Nairobi',
            country='Kenya',
            lead_time_days=5
        ),
        Supplier(
            name='LabChem Supplies',
            contact_person='David Omondi',
            email='david@labchem.co.ke',
            phone='+254723456789',
            city='Mombasa',
            country='Kenya',
            lead_time_days=10
        )
    ]
    
    for sup in suppliers:
        db.session.add(sup)
    db.session.commit()
    print(f"   ✅ Created {len(suppliers)} suppliers")
    
    # Create Products
    print("\n📦 Creating products...")
    products = [
        # Prescription drugs
        Product(
            sku='MED001', name='Paracetamol 500mg', category_id=1,
            product_type='prescription', unit_price=5.00, cost_price=3.00,
            supplier_id=1, reorder_threshold=50, reorder_quantity=200,
            requires_prescription=False, unit_of_measure='tablet'
        ),
        Product(
            sku='MED002', name='Amoxicillin 250mg', category_id=1,
            product_type='prescription', unit_price=15.00, cost_price=10.00,
            supplier_id=1, reorder_threshold=30, reorder_quantity=100,
            requires_prescription=True, unit_of_measure='capsule'
        ),
        Product(
            sku='MED003', name='Metformin 500mg', category_id=1,
            product_type='prescription', unit_price=12.00, cost_price=8.00,
            supplier_id=1, reorder_threshold=40, reorder_quantity=150,
            requires_prescription=True, unit_of_measure='tablet'
        ),
        
        # OTC products
        Product(
            sku='OTC001', name='Ibuprofen 200mg', category_id=2,
            product_type='otc', unit_price=8.00, cost_price=5.00,
            supplier_id=2, reorder_threshold=30, reorder_quantity=150,
            unit_of_measure='tablet'
        ),
        Product(
            sku='OTC002', name='Cough Syrup 100ml', category_id=2,
            product_type='otc', unit_price=25.00, cost_price=15.00,
            supplier_id=2, reorder_threshold=20, reorder_quantity=50,
            unit_of_measure='bottle'
        ),
        Product(
            sku='OTC003', name='Vitamin C 1000mg', category_id=2,
            product_type='otc', unit_price=18.00, cost_price=12.00,
            supplier_id=2, reorder_threshold=25, reorder_quantity=100,
            unit_of_measure='tablet'
        ),
        
        # Lab formulated products
        Product(
            sku='LAB001', name='Eczema Relief Cream 50g', category_id=3,
            product_type='lab_formulated', unit_price=350.00, cost_price=150.00,
            is_lab_formulated=True, reorder_threshold=15, reorder_quantity=30,
            shelf_life_days=180, unit_of_measure='tube'
        ),
        Product(
            sku='LAB002', name='Anti-Acne Gel 30g', category_id=3,
            product_type='lab_formulated', unit_price=280.00, cost_price=120.00,
            is_lab_formulated=True, reorder_threshold=10, reorder_quantity=25,
            shelf_life_days=180, unit_of_measure='tube'
        ),
        Product(
            sku='LAB003', name='Moisturizing Lotion 100ml', category_id=3,
            product_type='lab_formulated', unit_price=420.00, cost_price=200.00,
            is_lab_formulated=True, reorder_threshold=12, reorder_quantity=30,
            shelf_life_days=365, unit_of_measure='bottle'
        ),
        
        # Raw materials
        Product(
            sku='RAW001', name='Shea Butter 1kg', category_id=4,
            product_type='raw_material', unit_price=2500.00, cost_price=2000.00,
            supplier_id=3, reorder_threshold=5, reorder_quantity=20,
            unit_of_measure='kg'
        ),
        Product(
            sku='RAW002', name='Aloe Vera Gel 1L', category_id=4,
            product_type='raw_material', unit_price=1800.00, cost_price=1500.00,
            supplier_id=3, reorder_threshold=3, reorder_quantity=10,
            unit_of_measure='liter'
        ),
        Product(
            sku='RAW003', name='Essential Oil Mix 500ml', category_id=4,
            product_type='raw_material', unit_price=3500.00, cost_price=3000.00,
            supplier_id=3, reorder_threshold=2, reorder_quantity=5,
            unit_of_measure='bottle'
        ),
    ]
    
    for prod in products:
        db.session.add(prod)
    db.session.commit()
    print(f"   ✅ Created {len(products)} products")
    
    # Add Inventory
    print("\n📊 Adding inventory...")
    inventory_count = 0
    for product in Product.query.all():
        # Add different stock levels
        if product.product_type == 'prescription':
            quantity = 150
        elif product.product_type == 'otc':
            quantity = 100
        elif product.product_type == 'lab_formulated':
            quantity = 25
        else:  # raw_material
            quantity = 10
        
        inv = Inventory(
            product_id=product.id,
            quantity=quantity,
            location='main',
            batch_number=f'BATCH-{product.sku}-001',
            expiration_date=date.today() + timedelta(days=365),
            received_date=date.today(),
            cost_per_unit=product.cost_price
        )
        db.session.add(inv)
        inventory_count += 1
    
    db.session.commit()
    print(f"   ✅ Added inventory for {inventory_count} products")
    
    print("\n✅ Sample data creation complete!\n")
    print("📊 Summary:")
    print(f"   Categories: {Category.query.count()}")
    print(f"   Suppliers: {Supplier.query.count()}")
    print(f"   Products: {Product.query.count()}")
    print(f"   Inventory Records: {Inventory.query.count()}")