from app import app, db, User, Turf
from werkzeug.security import generate_password_hash

# Initialize database
with app.app_context():
    db.create_all()
   
    # 1 Create ADMIN user (Runs only once)
    # ---------------------------------------------------------
    admin_email = "admin@gmail.com"
    admin = User.query.filter_by(email=admin_email).first()

    
    if not admin:
        hashed_pw = generate_password_hash("admin123")
        admin = User(
            username="admin",
            email=admin_email,
            password_hash=hashed_pw,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✔ Admin account created successfully!")
   
    #Create sample turfs if none exist
    if not Turf.query.first():
        # Create a sample owner
        owner = User(
            username='owner1',
            email='owner@example.com',
            password_hash=generate_password_hash('password123'),
            is_owner=True
        )
        db.session.add(owner)
        db.session.commit()
    existing_owner = User.query.filter_by(username="owner1").first()

    if not existing_owner:
        owner = User(
            username='owner1',
            email='owner@example.com',
            password_hash=generate_password_hash('password123'),
            is_owner=True
        )
        db.session.add(owner)
        db.session.commit()
    else:
        owner = existing_owner
        
        # Create sample turfs
        sample_turfs = [
            {
                'name': ' FC Football Turf',
                'location': 'Goregaon, Mumbai',
                'description': 'Premium artificial turf with floodlights. Perfect for football matches.',
                'price_per_hour': 1200,
                'image_url':  '/static/images/football.webp'
            },
            {
                'name': 'Kandivali Turf Zone',
                'location': 'Kandivali,Mumbai',
                'description': 'Multi-sport facility with cricket and football options.',
                'price_per_hour': 1000,
                'image_url': '/static/images/cricket.webp'  
            },
            {
                'name': 'JP Turf',
                'location': 'Malad,Mumbai',
                'description': 'Professional ground for cricket and football.',
                'price_per_hour': 1200,
                'image_url':'/static/images/c&f.jpg' 
            },
            {
                'name': 'Eksar Cricket Ground',
                'location': 'Borivali,Mumbai',
                'description': 'Professional cricket ground with all facilities.',
                'price_per_hour': 2000,
                'image_url':'/static/images/professionalcricket.jpg' 
            }
        ]
        
        for turf_data in sample_turfs:
            turf = Turf(owner_id=owner.id, **turf_data)
            db.session.add(turf)
        
        db.session.commit()
