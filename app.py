from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify,abort,current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime, time, timedelta
import stripe
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText 
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from functools import wraps
from flask_migrate import Migrate
from datetime import datetime, timedelta, time
from sqlalchemy import func ,desc,asc,extract
from flask import send_file
import io 
import csv
from functools import wraps
from sqlalchemy import func as sa_func 
import json
from sqlalchemy.ext.hybrid import hybrid_property
import humanize
from flask_login import logout_user
from  collections import defaultdict
import requests
# from sqlalchemy import event
# from sqlalchemy.engine import Engine
# import sqlite3

load_dotenv()

# @event.listens_for(Engine, "connect")
# def set_sqlite_pragma(dbapi_connection, connection_record):
#     if isinstance(dbapi_connection, sqlite3.Connection):
#         cursor = dbapi_connection.cursor()
#         cursor.execute("PRAGMA foreign_keys=ON")
#         cursor.close()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "sslmode": "require"
    }
}


# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # Replace with  actual Stripe secret key
STRIPE_PUBLISHABLE_KEY = "pk_test_51RxU4f4XZ7d53ETuWSPMdxGdkpzbIO1EluWJEKcrikvwacHblcIgmtWn45QQSWf0DDNL0zgzs0Z7GkQbgG0ddYS900085XdRaJ"  # Replace with actual Stripe publishable key


# Email Configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = os.getenv("EMAIL_ADDRESS")  # Replace with  email
EMAIL_PASS = os.getenv("EMAIL_PASS")   # Replace with app password

db = SQLAlchemy(app)

migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    active = db.Column(db.Boolean, default=True)
    
   

class Turf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price_per_hour = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner = db.relationship('User', backref='turfs', lazy=True)
    bookings = db.relationship('Booking', backref='turf', lazy=True ,cascade='all, delete-orphan')
    reviews = db.relationship(
        'Review',
        backref='turf',
        lazy=True,
        cascade='all, delete-orphan'
    )
    slots = db.relationship(
       'TimeSlot',
        backref='turf',
        cascade='all, delete-orphan',
        lazy=True
    )
    address = db.Column(db.Text, nullable=False)
     # Operating Hours
    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    #  Contact Info
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    # Turf Specifications
    surface_type = db.Column(db.String(50))
    length = db.Column(db.Integer)
    width = db.Column(db.Integer)
    player_capacity = db.Column(db.String(50))
    available_days = db.Column(db.String(200))
    # Facilities
    floodlights = db.Column(db.Boolean, default=False)
    parking = db.Column(db.Boolean, default=False)
    wifi = db.Column(db.Boolean, default=False)
    restrooms = db.Column(db.Boolean, default=False)
    refreshments = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    @hybrid_property
    def average_rating(self):
        if not self.reviews:
            return 0.0
        return round(
            sum(r.rating for r in self.reviews) / len(self.reviews),
            1
        )

    
    @average_rating.expression
    def average_rating(cls):
        return (
            db.select(func.coalesce(func.avg(Review.rating), 0))
            .where(Review.turf_id == cls.id)
            .correlate(cls)
            .scalar_subquery()
        )
  
    

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    turf_id = db.Column(db.Integer, db.ForeignKey('turf.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    base_price = db.Column(db.Float, nullable=False)
    final_price = db.Column(db.Float, nullable=False)

    is_holiday = db.Column(db.Boolean, default=False)
    is_weekend = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.UniqueConstraint('turf_id', 'date', 'start_time', name='unique_slot_per_time'),
    )

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    turf_id = db.Column(db.Integer, db.ForeignKey('turf.id', ondelete='CASCADE' ), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    booking_status = db.Column(db.String(20), default='confirmed')
    stripe_payment_intent_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False)
    phone_number = db.Column(db.String(20))
    number_of_players = db.Column(db.Integer)
    special_requests = db.Column(db.Text)    
    stripe_refund_id = db.Column(db.String(200), nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    turf_id = db.Column(db.Integer, db.ForeignKey('turf.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)  # Rating from 1.0 to 5.0
    comment = db.Column(db.Text, nullable=True)   # User's written review
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships for easy lookup
    user = db.relationship('User', backref='reviews')
    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_confirmation_email(user_email, booking_details):
    """Send booking confirmation email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = user_email
        msg['Subject'] = "Turf Booking Confirmation"
        
        body = f"""
        Dear Customer,
        
        Your turf booking has been confirmed!
        
        Booking Details:
        - Turf: {booking_details['turf_name']}
        - Date: {booking_details['date']}
        - Time: {booking_details['start_time']} - {booking_details['end_time']}
        - Amount: ₹{booking_details['amount']}
        
        Thank you for choosing our service!!!
        
        Best regards,
        Turf Playgrounds Booking Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, user_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False
    
def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_owner:
            flash('This page is for owners only.', 'danger')
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access only!", "danger")
            return redirect(url_for("homepage"))
        return f(*args, **kwargs)
    return wrapper

#Turf  images Source
UPLOAD_FOLDER = 'static/images'
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_location(loc):
    """Extract clean area name (before comma), formatted properly."""
    if not loc:
        return None
    return loc.split(',')[0].strip().title()


# Routes


@app.before_request
def block_inactive_users():
    if current_user.is_authenticated and not current_user.active:
        logout_user()
        flash("Your account has been blocked by admin.", "danger")
        return redirect(url_for("login"))


#----------------------------------------------------ABOUT NAVBAR ------------------------------------
@app.route('/about')
def about():
    """About Us Page"""
    return render_template('about.html')

@app.route('/')
def index():
    """Intro/Homepage"""
    return render_template('index.html',show_flash=False)
#----------------------------------------- SIGNUP-----------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_owner = 'is_owner' in request.form
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists','danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered','danger')
            return redirect(url_for('signup'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_owner=is_owner
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

#--------------------------------- LOGIN --------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

        if not user.active:
            flash('Your account has been blocked by admin', 'danger')
            return redirect(url_for('login'))

        if not check_password_hash(user.password_hash, password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

        login_user(user)

        # Role-based redirect
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        elif user.is_owner:
            return redirect(url_for('owner_dashboard'))
        else:
            return redirect(url_for('homepage'))

    return render_template('login.html',show_flash=True)


#-----------------------------LOGOUT---------------------------------------

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/homepage')
@login_required

def homepage():
    """Main homepage after login"""
    search_query = request.args.get('search', '')
    location_filter = request.args.get('location', '')
    
    # Base query
    turfs_query = Turf.query
    
    # Apply filters
    if search_query:
        turfs_query = turfs_query.filter(
            Turf.name.contains(search_query) | 
            Turf.description.contains(search_query)
        )
    
    if location_filter:
        turfs_query = turfs_query.filter(Turf.location.contains(location_filter))
    
    turfs = turfs_query.all()
    raw_locations = db.session.query(Turf.location).all()
    locations = sorted(
        set(
                loc.location.split(",")[0].strip().title()
                for loc in raw_locations
                if loc.location
            )
    )
    
    return render_template('homepage.html', 
                         turfs=turfs, 
                         locations=locations,
                         search_query=search_query,
                         location_filter=location_filter)

@app.route('/turf/submit_review/<int:turf_id>', methods=['POST'])
@login_required
def submit_review(turf_id):
    rating = request.form.get('rating', type=float)
    comment = request.form.get('comment')
    
    # Check if user already reviewed this turf 
    existing_review = Review.query.filter_by(
        user_id=current_user.id, 
        turf_id=turf_id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this turf.', 'warning')
        return redirect(url_for('turf_details', turf_id=turf_id))

    if rating and 1 <= rating <= 5:
        new_review = Review(
            user_id=current_user.id,
            turf_id=turf_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
        db.session.commit()
        flash('Your review has been successfully submitted!', 'success')
    else:
        flash('Please provide a valid rating between 1 and 5.', 'danger')
        
    return redirect(url_for('turf_details', turf_id=turf_id))


@app.route('/turf/<int:turf_id>')
def turf_details(turf_id):
    
    turf = Turf.query.get_or_404(turf_id)
    print("TURF ADDRESS:", turf.address)
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    now = datetime.now()

    selected_date_str = request.args.get("date")

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        # get first available slot date
        today = datetime.now().date()

        # get next available slot from today onwards
        first_slot = TimeSlot.query.filter(
            TimeSlot.turf_id == turf_id,
            TimeSlot.date >= today
        ).order_by(TimeSlot.date).first()

        if first_slot:
            selected_date = first_slot.date
        else:
            selected_date = today


    slots = TimeSlot.query.filter(
        TimeSlot.turf_id == turf_id,
        TimeSlot.date == selected_date
    ).order_by(
        TimeSlot.start_time
    ).all()


    available_slots = []

    for slot in slots:

        slot_datetime = datetime.combine(slot.date, slot.start_time)

        # Skip past slots
        if slot_datetime <= now and slot.date == today:
            continue

        # Check booking conflict
        booking = Booking.query.filter_by(
            turf_id=turf_id,
            booking_date=slot.date,
            start_time=slot.start_time
        ).first()

        is_booked = booking and booking.booking_status != "cancelled"

        #  Last Slot Logic 
        is_last_slot = False

        #  Dynamic Pricing Logic
        price = slot.base_price

        # Weekend Multiplier (Saturday=5, Sunday=6)
        if slot.date.weekday() in [5, 6]:
            price *= 1.2  # 20% weekend increase

        # Holiday Pricing
        if slot.is_holiday:
            price *= 0.7  

        available_slots.append({
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "price": round(price, 0),
            "is_booked": is_booked,
            "base_price": round(slot.base_price, 0) if slot.base_price else 0,
            "is_weekend": slot.date.weekday() in [5, 6],
            "is_holiday": slot.is_holiday,
            "is_last_slot": is_last_slot
        })
    
    
    
    # Reviews
    reviews = Review.query.filter_by(turf_id=turf_id).order_by(
        Review.created_at.desc()
    ).all()

    avg_rating = db.session.query(
        sa_func.avg(Review.rating)
    ).filter(
        Review.turf_id == turf_id
    ).scalar()

    avg_rating_final = round(avg_rating or 0, 1)

    calendar_status = {}

    # Get all slots for calendar
    all_slots = TimeSlot.query.filter_by(turf_id=turf_id).all()

    for slot in all_slots:
        date_key = slot.date.isoformat()

        booking = Booking.query.filter_by(
        turf_id=turf_id,
        booking_date=slot.date,
        start_time=slot.start_time
        ).first()

        is_booked = booking and booking.booking_status != "cancelled"

        if slot.is_holiday:
            calendar_status[date_key] = "holiday"
        elif is_booked:
            # mark as booked only if no available slots left
            if calendar_status.get(date_key) != "available":
                calendar_status[date_key] = "booked"
        else:
            calendar_status[date_key] = "available"
    
    


    return render_template(
        "turf_details.html",
        turf=turf,
        available_slots=available_slots,
        reviews=reviews,
        avg_rating_final=avg_rating_final,
        today=today,
        tomorrow=tomorrow,
        selected_date=selected_date,
        calendar_status=calendar_status,
             
    )


@app.route('/api/turf/<int:turf_id>/slots')
def turf_slots_api(turf_id):

    turf = Turf.query.get_or_404(turf_id)
    selected_date = request.args.get("date")

    if not selected_date:
        return jsonify([])

    selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    slots_db = TimeSlot.query.filter_by(
        turf_id=turf_id,
        date=selected_date
    ).order_by(TimeSlot.start_time).all()

    now = datetime.now()
    slots = []

    for slot in slots_db:

        slot_datetime = datetime.combine(slot.date, slot.start_time)
        today = datetime.now().date()

        #  skip expired slots
        if slot.date == today and slot_datetime <= now:
            continue

        booking = Booking.query.filter_by(
            turf_id=turf_id,
            booking_date=slot.date,
            start_time=slot.start_time
        ).first()

        is_booked = booking and booking.booking_status != "cancelled"

        is_last_slot = False

        slots.append({
            "date": slot.date,
            "start_time": slot.start_time,   
            "end_time": slot.end_time,
            "price": slot.final_price,
            "base_price": slot.base_price,
            "is_weekend": slot.is_weekend,
            "is_holiday": slot.is_holiday,
            "is_booked": is_booked,
            "is_last_slot": is_last_slot
        })

    return render_template(
        "calendarslot.html",
        available_slots=slots,
        turf=turf, 
        today=datetime.now().date(),
        tomorrow=datetime.now().date() + timedelta(days=1)
    )

@app.route('/api/turf/<int:turf_id>/calendar')
def turf_calendar_data(turf_id):

    today = datetime.now().date()
    end_date = today + timedelta(days=30)

    slots = TimeSlot.query.filter(
        TimeSlot.turf_id == turf_id,
        TimeSlot.date >= today,
        TimeSlot.date <= end_date
    ).all()

    events = {}

    for slot in slots:
        date_key = slot.date.isoformat()

        booking = Booking.query.filter_by(
            turf_id=turf_id,
            booking_date=slot.date,
            start_time=slot.start_time
        ).first()

        is_booked = booking and booking.booking_status != "cancelled"

        if slot.is_holiday:
            events[date_key] = "holiday"
        elif is_booked:
            events[date_key] = "booked"
        else:
            events[date_key] = "available"

    calendar_events = []

    for date, status in events.items():

        color = "#198754"     # green

        if status == "booked":
            color = "#dc3545"# red
        if status == "holiday":
            color = "#ffc107"  # yellow

        calendar_events.append({
            "start": date,
            "display": "background",
            "backgroundColor": color
        })

    return jsonify(calendar_events)


@app.route('/delete_review/<int:review_id>')
@login_required
def delete_review(review_id):
    """Deletes a review if the current user is the author."""
    
    review = Review.query.get_or_404(review_id)

    # CRITICAL SECURITY CHECK: Ensure the user owns the review
    if review.user_id != current_user.id:
        flash('Unauthorized: You can only delete your own reviews.', 'danger')
        return redirect(url_for('turf_details', turf_id=review.turf_id))

    try:
        turf_id = review.turf_id # Save ID before deletion for redirection
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting review: {e}")
        flash('An error occurred during deletion.', 'danger')

    return redirect(url_for('turf_details', turf_id=turf_id))

@app.route('/book/<int:turf_id>',methods=['GET', 'POST'])
@login_required
def book_turf(turf_id):
    """Booking form page"""
    turf = Turf.query.get_or_404(turf_id)
    date = request.args.get('date')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    if not all([date, start_time, end_time]):
        flash('Please select a valid time slot')
        return redirect(url_for('turf_details', turf_id=turf_id))
    
    # Calculate total amount
    total_amount = turf.price_per_hour
    
    return render_template('booking_form.html', 
                         turf=turf, 
                         date=date, 
                         start_time=start_time, 
                         end_time=end_time,
                         total_amount=total_amount,
                         stripe_public_key=STRIPE_PUBLISHABLE_KEY)

#--------------------------------------- PAYMENT SUCCESS------------------------------------------
@app.route('/payment_success', methods=['GET', 'POST'])
@login_required
def payment_success():
    """Handles successful payment callback and updates booking status."""
    
    booking_id = request.args.get('booking_id')
    pi_id = request.args.get('pi') #new added 7th feb

    if not booking_id:
        flash('Invalid payment confirmation link.', 'danger')
        return redirect(url_for('homepage'))

    try:
        # Find the booking belonging to the current user
        # We use .one() to ensure we get exactly one result
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).one()
        
        # 1. Update Statuses 
        
        booking.payment_status = 'completed'
        booking.booking_status = 'confirmed'
        booking.stripe_payment_intent_id = pi_id #new added 7th feb
        
        if not booking.created_at:
             booking.created_at = datetime.now() 
        
        
        print(f"DEBUG PRE-COMMIT: Booking Date={booking.booking_date}, Start Time={booking.start_time}, Total Amount={booking.total_amount}")
        print(f"DEBUG PRE-COMMIT: User ID={booking.user_id}, Turf ID={booking.turf_id}")
     

        
        db.session.commit()
        
        # 2. Send Confirmation Email
        if not booking.email_sent:
            booking_details = {
                'turf_name': booking.turf.name,
                'date': booking.booking_date.strftime('%Y-%m-%d'),
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M'),
                'amount': booking.total_amount
            }
            
            
            if send_confirmation_email(current_user.email, booking_details): 
                booking.email_sent = True
                
                
                try:
                    db.session.commit() 
                except Exception as e:
                    db.session.rollback()
                    print(f"ERROR: Failed to save email_sent flag: {e}")
        
        flash('Payment confirmed and booking saved successfully!', 'success')
        
        
        return render_template('confirmation.html', booking=booking)

    except NoResultFound:
        # This catches if the booking ID is invalid or doesn't belong to the user
        flash('Booking record not found or access denied.', 'danger')
        return redirect(url_for('order_history'))
        
    except Exception as e:
        # This catches the critical database transaction failure
        db.session.rollback()
        
        # Print the detailed error to your terminal for debugging 
        print(f"CRITICAL DB COMMIT FAILURE on payment success: {e}") 
        
        # Flash message to user
        flash('Payment confirmed, but a critical database error occurred saving the record. Please contact support.', 'danger')
        return redirect(url_for('order_history'))
    

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, 'whsec_your_webhook_secret'  
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Handle the payment_intent.succeeded event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Update booking status
        booking = Booking.query.filter_by(
            stripe_payment_intent_id=payment_intent['id']
        ).first()
        
        if booking:
            booking.payment_status = 'completed'
            db.session.commit()

    # REFUND HANDLED 
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        payment_intent_id = charge['payment_intent']

        booking = Booking.query.filter_by(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if booking:
            booking.payment_status = 'refunded'
            booking.booking_status = 'cancelled'
            booking.refunded_at = datetime.utcnow()
            db.session.commit()
    
    return 'Success', 200

@app.route('/create_payment_intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        data = request.get_json()
        print("DEBUG DATA RECEIVED:", data)

        amount = data.get("amount")
        booking_id = data.get("booking_id")

        if not amount or int(amount) <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        intent = stripe.PaymentIntent.create(
            amount=int(amount) * 100,  # INR → paise
            currency="inr",
            automatic_payment_methods={"enabled": True},
            metadata={
                "booking_id": booking_id,
                "user_id": current_user.id
            }
        )

        print("DEBUG INTENT CREATED:", intent.id)

        return jsonify({
            "client_secret": intent.client_secret
        })

    except Exception as e:
        print(" STRIPE ERROR:", str(e))
        return jsonify({"error": str(e)}), 500 


#---------------------------------------Refund Support ----------------------------------------
@app.route("/refund/<int:booking_id>", methods=["POST"])
@login_required
def refund_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        abort(403)

    if booking.payment_status != "completed":
        return jsonify({"error": "Payment not completed"}), 400

    if booking.stripe_refund_id:
        return jsonify({"error": "Already refunded"}), 400

    now = datetime.utcnow()

    if booking.created_at and (now - booking.created_at) > timedelta(hours=24):
        return jsonify({"error": "Refund allowed only within 24 hours"}), 400
    
    try:
        refund = stripe.Refund.create(
            payment_intent=booking.stripe_payment_intent_id,
            reason="requested_by_customer"
        )

        booking.payment_status = "refunded"
        booking.booking_status = "cancelled"
        booking.stripe_refund_id = refund.id
        booking.refunded_at = datetime.utcnow()

        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        print(" REFUND ERROR:", repr(e))
        return jsonify({"error": str(e)}), 500
   

#----------------------------------------------------------------------------- BOOKING PROCESS--------------------------------------------   

@app.route('/process_booking', methods=['POST'])
@login_required
def process_booking():
    """
    Creates a pending booking and redirects user to payment page.
    Stripe PaymentIntent is created on frontend via /create_payment_intent
    """

    try:
        # 1. Read & validate form data
        turf_id = int(request.form.get('turf_id'))
        total_amount = float(request.form.get('total_amount'))
        phone = request.form.get("customerPhone")
        players = request.form.get("players")
        special_request = request.form.get("specialRequests")
        booking_date_str = request.form.get('booking_date')
        start_time_str = request.form.get('start_time') or request.args.get('start_time')
        end_time_str = request.form.get('end_time') or request.args.get('end_time')

        if not all([booking_date_str, start_time_str, end_time_str]):
            flash('Invalid booking data', 'danger')
            return redirect(url_for('homepage'))

        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()

        # 2. Prevent double booking
        conflict = Booking.query.filter_by(
            turf_id=turf_id,
            booking_date=booking_date,
            start_time=start_time
        ).first()

        if conflict and conflict.booking_status != 'cancelled':
            flash('This time slot is no longer available!', 'danger')
            return redirect(url_for('turf_details', turf_id=turf_id))

        # 3. Create booking (PENDING)
        booking = Booking(
            user_id=current_user.id,
            turf_id=turf_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            payment_status='pending',
            booking_status='pending',
            phone_number=phone,
            number_of_players=players,
            special_requests=special_request
        )

        db.session.add(booking)
        db.session.commit()

        # 4. Redirect to payment page
        return render_template(
            'payment_test.html',
            booking=booking,
            stripe_public_key=STRIPE_PUBLISHABLE_KEY
        )

    except Exception as e:
        db.session.rollback()
        print("PROCESS BOOKING ERROR:", e)
        flash('Booking failed. Please try again.', 'danger')
        return redirect(url_for('homepage'))


@app.route('/get_booking_details/<int:booking_id>')
@login_required
def get_booking_details(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Security check: ensure user can only view their own booking details
    if booking.user_id != current_user.id:
        # Prevent unauthorized access
        return abort(403) 
    
    
    return render_template('bookiing_details.html', booking=booking)


@app.route('/all_bookings')
@login_required
def all_bookings():
    """Display all available turfs for booking"""
    search_query = request.args.get('search', '')
    location_filter = request.args.get('location', '')
    
    # Base query
    turfs_query = Turf.query
    
    # Apply filters
    if search_query:
        turfs_query = turfs_query.filter(
            Turf.name.contains(search_query) | 
            Turf.description.contains(search_query)
        )
    
    if location_filter:
        turfs_query = turfs_query.filter(Turf.location.contains(location_filter))
    
    turfs = turfs_query.all()
    raw_locations = db.session.query(Turf.location).all()
    locations = sorted(
        set(
                loc.location.split(",")[0].strip().title()
                for loc in raw_locations
                if loc.location
            )
    )

    #  Calculate rating + review count for each turf
    for turf in turfs:
        avg_rating_result = db.session.query(sa_func.avg(Review.rating)) \
                                      .filter(Review.turf_id == turf.id).scalar()

        avg_rating_final = round(avg_rating_result, 1) if avg_rating_result else 0

        turf.avg_rating = avg_rating_final
        turf.reviews_count = Review.query.filter_by(turf_id=turf.id).count()
    
    return render_template('all_bookings.html', 
                         turfs=turfs, 
                         locations=locations,
                         search_query=search_query,
                         location_filter=location_filter)

@app.route('/order_history')
@login_required
def order_history():
    """User's booking history with sorting and filtering options"""
    
    # 1. Get filter and sort parameters from the URL
    current_status = request.args.get('status', 'all')  # Get status filter (default: 'all')
    current_sort = request.args.get('sort_by', 'newest') # Get sort choice (default: 'newest')
    
    # 2. Build the base query
    query = Booking.query.filter_by(user_id=current_user.id)
    
    #  Apply Status Filter 
    if current_status != 'all':
        query = query.filter(Booking.booking_status == current_status)
        
    # 3. --- Apply Sorting Logic ---
    if current_sort == 'oldest':
        query = query.order_by(asc(Booking.created_at))
    elif current_sort == 'amount-high':
        query = query.order_by(desc(Booking.total_amount))
    elif current_sort == 'amount-low':
        query = query.order_by(asc(Booking.total_amount))
    else: # Default: 'newest'
        query = query.order_by(desc(Booking.created_at))
        
    bookings = query.all()
    
    return render_template('order_history.html', 
                           bookings=bookings, 
                           current_sort=current_sort, 
                           current_status=current_status,
                           now = datetime.utcnow())


@app.route('/cancel_booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        flash('Unauthorized access')
        return redirect(url_for('order_history'))

    # Combine booking date and time for comparison
    booking_datetime = datetime.combine(booking.booking_date, booking.start_time)

    # Check if the booking is more than 24 hours in the future
    if booking_datetime > datetime.now() + timedelta(hours=24):
        
        booking.booking_status = 'cancelled'
        db.session.commit()
        flash('Booking cancelled successfully!', 'success')
    else:
        
        flash('Bookings can only be canceled at least 24 hours in advance.', 'danger')

    return redirect(url_for('order_history'))

#-------------------------------------ADMIN ROUTES-----------------------------------------

#--------------------- ADMIN DASHBOARD---------------------------------
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    owners = User.query.filter_by(is_owner=True).all()
    users = User.query.filter_by(is_owner=False, is_admin=False).all()
    turfs = Turf.query.all()
    total_bookings = Booking.query.count()

    # Group bookings by location
    bookings_by_location = (
        db.session.query(Turf.location, db.func.count(Booking.id))
        .join(Booking, Booking.turf_id == Turf.id)
        .group_by(Turf.location)
        .all()
    )

    return render_template(
        "admin_dashboard.html",
        owners=owners,
        users=users,
        turfs=turfs,
        total_bookings=total_bookings,
        bookings_by_location=bookings_by_location,
        active="dashboard"
    )

# ------------------------------------ VIEW OWNERS---------------------------------
@app.route('/admin/owners')
@login_required
@admin_required
def admin_owners():
    owners = (
        User.query
        .filter_by(is_owner=True)
        .order_by(User.created_at.desc())  # newest first
        .all()
    )

    # Create a list with "time ago"
    owner_data = []
    for o in owners:
        if o.created_at:
            time_ago = humanize.naturaltime(datetime.utcnow() - o.created_at)
        else:
            time_ago = "—"
        owner_data.append({
            "id": o.id,
            "username": o.username,
            "email": o.email,
            "created_at": o.created_at,
            "time_ago": time_ago
        })

    return render_template("admin_owners.html", owners=owner_data)

#-------------------------- APPROVE OWNER-----------------------
@app.route('/admin/owner/approve/<int:owner_id>')
@admin_required
def approve_owner(owner_id):
    owner = User.query.get_or_404(owner_id)
    owner.is_owner = True
    db.session.commit()
    return redirect(url_for("admin_owners"))
#---------------------------------------APPROVE USER------------------------------
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = (
        User.query
        .filter_by(is_owner=False,is_admin=False)
        .order_by(User.created_at.desc())
        .all()
    )

    user_data = []
    for u in users:
        if u.created_at:
            time_ago = humanize.naturaltime(datetime.utcnow() - u.created_at)
        else:
            time_ago = "—"

        user_data.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "created_at": u.created_at,
            "time_ago": time_ago,
            "active": u.active  
        })

    return render_template("admin_users.html", users=user_data,show_flash=True)

#----------------------------------------------------Block Owner-------------------------------------
@app.route('/admin/owner/block/<int:owner_id>')
@admin_required
def block_owner(owner_id):
    owner = User.query.get_or_404(owner_id)
    owner.is_owner = False
    db.session.commit()
    return redirect(url_for("admin_owners"))

#----------------------------------------- View All Turfs------------------------
@app.route('/admin/turfs')
@login_required
@admin_required
def admin_turfs():
    name = request.args.get("name", "")
    location = request.args.get("location", "")
    sort = request.args.get("sort", "newest")

    query = Turf.query

    if name:
        query = query.filter(Turf.name.ilike(f"%{name}%"))
    
    if location:
        query = query.filter(Turf.location.ilike(f"%{location}%"))

    
    # Sorting logic
    if sort == "newest":
        query = query.order_by(Turf.created_at.desc(),Turf.id.desc())
    elif sort == "oldest":
        query = query.order_by(Turf.created_at.asc(),Turf.id.asc())
    elif sort == "price_high":
        query = query.order_by(Turf.price_per_hour.desc())
    elif sort == "price_low":
        query = query.order_by(Turf.price_per_hour.asc())
    elif sort == "rating_high":
        query = query.order_by(Turf.average_rating.desc())

    turfs = query.all()

    turf_data = []
    for t in turfs:
        turf_data.append({
            "id": t.id,
            "name": t.name,
            "owner_name": t.owner.username if t.owner else "-",
            "owner_id": t.owner_id,
            "location": t.location,
            "price_per_hour": t.price_per_hour,
            "created_at": t.created_at.strftime('%d %b %Y'),
            "time_ago": humanize.naturaltime(datetime.utcnow() - t.created_at)
        })

    return render_template("admin_turfs.html", turfs=turf_data)

#------------------------------------ APPROVE TURFS---------------------------------------
@app.route('/admin/turf/approve/<int:turf_id>')
@admin_required
def approve_turf(turf_id):
    turf = Turf.query.get_or_404(turf_id)
    turf.approved = True
    db.session.commit()
    return redirect(url_for("admin_turfs"))

#------------------------------------------ USER MANAGEMENT BY ADMIN------------------------------------------
@app.route('/admin/turf/delete/<int:turf_id>')
@admin_required
def admin_delete_turf(turf_id):
    turf = Turf.query.get_or_404(turf_id)
    # bookings = Booking.query.filter_by(turf_id=turf_id).all()
    # for booking in bookings:
    #     db.session.delete(booking)

    # reviews = Review.query.filter_by(turf_id=turf_id).all()
    # for r in reviews:
    #     db.session.delete(r)

    # db.session.flush()  
    db.session.delete(turf)
    db.session.commit()
    return redirect(url_for("admin_turfs"))

#--------------------------------------------------- BLOCK USER--------------------------------
@app.route('/admin/user/block/<int:user_id>')
@login_required
@admin_required
def block_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash("You cannot block an admin.", "danger")
        return redirect(url_for('admin_users'))

    user.active = False
    db.session.commit()

    flash(f"User '{user.username}' has been blocked.", "success")
    return redirect(url_for('admin_users'))


#-------------------------------------------------------------------------------UNBLOCK USER----------------------------
@app.route('/admin/user/unblock/<int:user_id>')
@login_required
@admin_required
def unblock_user(user_id):
    user = User.query.get_or_404(user_id)

    user.active = True
    db.session.commit()

    flash(f"User '{user.username}' has been unblocked.", "success")
    return redirect(url_for('admin_users'))



#-------------------------------------- REVIEW MODERATION BY ADMIN-----------------------------
@app.route('/admin/reviews')
@login_required
@admin_required
def admin_reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()

    review_data = []
    for r in reviews:
        if r.created_at:
            time_ago = humanize.naturaltime(datetime.utcnow() - r.created_at)
        else:
            time_ago = "—"

        review_data.append({
            "id": r.id,
            "username": r.user.username,
            "turf": r.turf.name,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at,
            "time_ago": time_ago
        })

    return render_template("admin_reviews.html", reviews=review_data)

#------------------------------------- DELETE REVIEW  By ADMIN -----------------------
@app.route('/admin/reviews/delete/<int:review_id>')
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for("admin_reviews"))

#----------------------------------------------- ANALYTICS BY ADMIN------------------------------
@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():

    # --------------------------- Revenue by Month ---------------------------
    revenue_data = (
        db.session.query(
            db.extract('month', Booking.booking_date).label('month'),
            db.func.sum(Booking.total_amount).label('revenue')
        )
        .group_by('month')
        .order_by('month')
        .all()
    )
    revenue_by_month = {int(m): float(r) for m, r in revenue_data}


    # --------------------------- Peak Booking Hour ---------------------------
    peak_hours = (
        db.session.query(
            db.extract('hour', Booking.start_time).label('hour'),
            db.func.count(Booking.id)
        )
        .group_by('hour')
        .order_by('hour')
        .all()
    )
    bookings_per_hour = {int(h): c for h, c in peak_hours}


    # --------------------------- Most Booked Turfs ---------------------------
    most_booked = (
        db.session.query(
            Turf.name,
            db.func.count(Booking.id).label('total')
        )
        .join(Booking, Booking.turf_id == Turf.id)
        .group_by(Turf.name)
        .order_by(db.desc('total'))
        .limit(5)
        .all()
    )

    # --------------------------- Dashboard Summary Count ---------------------------
    total_users = User.query.filter_by(is_owner=False,is_admin=False).count()
    total_owners = User.query.filter_by(is_owner=True).count()
    total_turfs = Turf.query.count()
    total_bookings = Booking.query.count()


    return render_template(
        "admin_analytics.html",
        revenue_by_month=revenue_by_month,
        bookings_per_hour=bookings_per_hour,
        most_booked=most_booked,
        total_users=total_users,
        total_owners=total_owners,
        total_turfs=total_turfs,
        total_bookings=total_bookings
    )

@app.route('/admin/fix-status')
@login_required
def admin_fix_status():
    # Update all bookings to completed
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    for booking in bookings:
        booking.payment_status = 'completed'
        booking.booking_status = 'confirmed'
    db.session.commit()
    flash('Payment statuses updated')
    return redirect(url_for('order_history'))



# ------------------------------OWNER ROUTES--------------------------------------------------

@app.route('/owner/dashboard')
@login_required
def owner_dashboard():
    """Owner dashboard - Fetches and calculates correct turf statistics."""

    if not current_user.is_owner:
        flash('Access denied', 'danger')
        return redirect(url_for('homepage'))

    #  Fetch all turfs owned by this user
    owner_turfs = Turf.query.filter_by(owner_id=current_user.id).all()
    turf_ids = [turf.id for turf in owner_turfs]

    #  Fetch ALL bookings for these turfs (NOT just recent 10)
    all_bookings = Booking.query.filter(
        Booking.turf_id.in_(turf_ids)
    ).all()

    #  Fetch recent bookings (only for table display)
    recent_bookings = Booking.query.filter(
        Booking.turf_id.in_(turf_ids)
    ).order_by(
        desc(Booking.created_at)
    ).limit(10).all()

    #  Calculate total confirmed bookings
    total_bookings_count = sum(
        1 for booking in all_bookings
        if booking.booking_status == 'confirmed'
    )

    #  Calculate total revenue correctly
    total_revenue_count = sum(
        booking.total_amount
        for booking in all_bookings
        if booking.payment_status == 'completed'
    ) 

    #  Calculate per-turf stats (VERY IMPORTANT)
    for turf in owner_turfs:

        turf.confirmed_count = sum(
            1 for b in turf.bookings
            if b.booking_status == 'confirmed'
        )

        turf.total_revenue = sum(
            b.total_amount
            for b in turf.bookings
            if b.payment_status == 'completed'
        )

        total_refunded = sum(
            b.total_amount
            for b in all_bookings
            if b.payment_status == 'refunded'
        )

    #  Average rating
    overall_avg_rating_result = db.session.query(
        sa_func.avg(Review.rating)
    ).filter(
        Review.turf_id.in_(turf_ids)
    ).scalar()

    overall_avg_rating = (
        "{:.1f}".format(overall_avg_rating_result)
        if overall_avg_rating_result else "0.0"
    )

    #  Chart data
    chart_data_json = {
        'labels': ['Total Turfs', 'Total Bookings', 'Total Revenue'],
        'counts': [
            len(owner_turfs),
            total_bookings_count,
            total_revenue_count
        ]
    }

    return render_template(
        'owner_dashboard.html',
        turfs=owner_turfs,
        recent_bookings=recent_bookings,
        total_bookings_count=total_bookings_count,
        total_revenue_count=total_revenue_count,
        overall_avg_rating=overall_avg_rating,
        chart_data_json=chart_data_json
    )

# ---------------------------------------------- WEEKEND MULTIPLIER ----------------------------

@app.route('/owner/apply_weekend_multiplier/<int:turf_id>', methods=['POST'])
@login_required
def apply_weekend_multiplier(turf_id):

    multiplier = float(request.form['multiplier'])

    weekend_slots = TimeSlot.query.filter(
        TimeSlot.turf_id == turf_id,
        TimeSlot.is_weekend == True
    ).all()

    for slot in weekend_slots:
        slot.final_price = slot.base_price * multiplier

    db.session.commit()

    flash("Weekend multiplier applied!", "success")
    return redirect(request.referrer)

#---------------------------------- SLOT DELETE SLOT-------------------------------
@app.route('/owner/delete_slot/<int:slot_id>', methods=['POST'])
@login_required
def delete_slot(slot_id):

    slot = TimeSlot.query.get_or_404(slot_id)

    db.session.delete(slot)
    db.session.commit()

    flash("Slot deleted", "success")
    return redirect(request.referrer)

#---------------------------------- SLOT EDIT ROUTE--------------------------------
@app.route('/owner/edit_slot/<int:slot_id>', methods=['GET', 'POST'])
@login_required
def edit_slot(slot_id):

    slot = TimeSlot.query.get_or_404(slot_id)
    turf = Turf.query.get_or_404(slot.turf_id)

    if turf.owner_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        slot.base_price = float(request.form['base_price'])
        slot.is_holiday = bool(request.form.get('is_holiday'))

        final_price = slot.base_price

        if slot.date.weekday() >= 5:
            final_price *= 1.2

        if slot.is_holiday:
            final_price *= 0.7

        slot.final_price = round(final_price, 2)

        db.session.commit()

        flash("Slot updated successfully", "success")
        return redirect(url_for('manage_slots', turf_id=slot.turf_id))

    return render_template("edit_slot.html", slot=slot)


#------------------------- SLOT WITH ( HOLIDAY & WEEKEND LOGIC)------------------------

@app.route('/owner/create_slot/<int:turf_id>', methods=['GET', 'POST'])
@login_required
def create_slot(turf_id):

    turf = Turf.query.get_or_404(turf_id)

    if turf.owner_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        try:
            date = datetime.strptime(request.form['date'], "%Y-%m-%d").date()
            start_time = datetime.strptime(request.form['start_time'], "%H:%M").time()
            end_time = datetime.strptime(request.form['end_time'], "%H:%M").time()
            base_price = float(request.form['base_price'])

            # Auto weekend detection
            is_weekend = date.weekday() >= 5

            # Manual holiday checkbox
            is_holiday = bool(request.form.get("is_holiday"))

            final_price = base_price

            if start_time >= end_time:
                flash("End time must be after start time", "danger")
                return redirect(request.referrer)

            if date < datetime.now().date():
                flash("Cannot create slot for past date", "danger")
                return redirect(request.referrer)


            # Weekend multiplier
            if is_weekend:
                final_price *= 1.2

            # Holiday multiplier
            if is_holiday:
                final_price *= 0.7

            slot = TimeSlot(
                turf_id=turf_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                base_price=base_price,
                final_price=round(final_price, 2),
                is_weekend=is_weekend,
                is_holiday=is_holiday
            )

            db.session.add(slot)
            db.session.commit()

            flash("Slot created successfully", "success")
            return redirect(url_for('manage_slots', turf_id=turf_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating slot: {e}", "danger")

    return render_template("create_slot.html", turf=turf)

#----------------------------------------------- GENERATE 7 DAYS SLOT AUTO ---------------------
@app.route("/owner/generate_slots/<int:turf_id>", methods=['GET', 'POST'])
@login_required
def generate_slots(turf_id):

    turf = Turf.query.get_or_404(turf_id)

    if turf.owner_id != current_user.id:
        abort(403)

    today = datetime.now().date()

    created_count = 0

    for i in range(7):
        date = today + timedelta(days=i)

        for hour in range(9, 21):  # 9AM to 9PM

            start = time(hour, 0)
            end = time(hour + 1, 0)

            #  Prevent duplicate
            existing = TimeSlot.query.filter_by(
                turf_id=turf_id,
                date=date,
                start_time=start
            ).first()

            if existing:
                continue

            base_price = turf.price_per_hour

            is_weekend = date.weekday() in [5, 6]
            is_holiday = False  

            final_price = base_price

            if is_weekend:
                final_price *= 1.2

            if is_holiday:
                final_price *= 1.5

            slot = TimeSlot(
                turf_id=turf_id,
                date=date,
                start_time=start,
                end_time=end,
                base_price=base_price,
                final_price=round(final_price, 0),
                is_weekend=is_weekend,
                is_holiday=is_holiday
            )

            db.session.add(slot)
            created_count += 1

    db.session.commit()
    print("METHOD USED:", request.method)


    flash(f"{created_count} slots generated successfully!", "success")
    return redirect(request.referrer)


#-------------------------------------OWNER MANAGE Slot ----------------------------------

@app.route('/owner/slots/<int:turf_id>')
@login_required
def manage_slots(turf_id):

    turf = Turf.query.get_or_404(turf_id)

    if turf.owner_id != current_user.id:
        abort(403)

    slots = TimeSlot.query.filter_by(turf_id=turf_id).order_by(TimeSlot.date).all()

    return render_template('owner_manage_slots.html',
                           turf=turf,
                           slots=slots)

#---------------------------------------- OWNER REFUND SUPPORT -------------------------------------------

@app.route('/owner/refund/<int:booking_id>', methods=['POST'])
@login_required
def owner_refund_booking(booking_id):

    if not current_user.is_owner:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    booking = Booking.query.get_or_404(booking_id)

    # Safety check: booking belongs to this owner
    if booking.turf.owner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    # Already refunded?
    if booking.payment_status == 'refunded':
        return jsonify({'success': False, 'message': 'Already refunded'}), 400

    # Only completed payments can be refunded
    if booking.payment_status != 'completed':
        return jsonify({'success': False, 'message': 'Payment not completed'}), 400

    try:
        #  Stripe refund
        refund = stripe.Refund.create(
            payment_intent=booking.stripe_payment_intent_id
        )

        #  Update DB
        booking.payment_status = 'refunded'
        booking.booking_status = 'cancelled'
        booking.stripe_refund_id = refund.id
        booking.refunded_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'success': True})

    except stripe.error.StripeError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Server error'}), 500


#--------------------------------------------------------------- OWNER SETTINGS (UPDATE PROFILE )-------------------------------


#--------------------------------------------------------- OWNER SETTINGS( CHANGE PASSWORD)--------------------------------------------------
@app.route('/owner/settings/change_password', methods=['POST'])
@login_required
@owner_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        
        if not new_password:
            flash('Password field cannot be empty.', 'danger')
            return redirect(url_for('owner_settings'))
        
        # Hash and save the password directly
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Account secured successfully! You can now log in using this password.', 'success')
        return redirect(url_for('owner_settings'))


@app.route('/get_owner_booking_details/<int:booking_id>')
@login_required
@owner_required # Ensure only owners can access this route
def get_owner_booking_details(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # CRITICAL SECURITY CHECK for OWNER: 
    # Ensure the booking belongs to a turf owned by the current user
    if booking.turf.owner_id != current_user.id:
        return abort(403) # Prevent unauthorized access to other turfs' data
    
    # Render the same booking detail snippet
    return render_template('bookiing_details.html', booking=booking)


    
@app.route('/all_owner_bookings')
@login_required
def all_owner_bookings():
    # 1. Access Check (optional, but good practice)
    if not current_user.is_owner:
        flash('Access denied', 'danger')
        return redirect(url_for('homepage'))

    # 2. Fetch all turfs owned by the current user
    owner_turfs = Turf.query.filter_by(owner_id=current_user.id).all()
    turf_ids = [turf.id for turf in owner_turfs]

    # 3. Fetch all bookings associated with those turfs
    all_bookings = Booking.query.filter(Booking.turf_id.in_(turf_ids)).all()

    # 4. Render a template to display the list
    return render_template('order_history.html',
                            bookings=all_bookings,
                            now = datetime.utcnow())


@app.route('/owner/settings')
@login_required
@owner_required # Assuming only owners can access this settings page
def owner_settings():
    """Renders the owner settings and preferences page."""
    
   
    return render_template('owner_settings.html')

@app.route('/owner/bookings')
@login_required
@owner_required
def owner_view_bookings():
    """Fetches and displays bookings filtered by turf ID."""
    
    turf_id = request.args.get('turf_id', type=int)
    
    # 1. Start the base query by verifying the owner
    query = Booking.query.join(Turf).filter(Turf.owner_id == current_user.id)
    
    # 2. Apply the turf filter if the ID is provided
    if turf_id:
        query = query.filter(Booking.turf_id == turf_id)
        
    # 3. Fetch all filtered bookings
    bookings = query.order_by(Booking.created_at.desc()).all()
    
    # 4. Render the booking list template 
    return render_template('order_history.html', bookings=bookings,now=datetime.utcnow())

@app.route('/owner/add_turf', methods=['GET', 'POST'])
@login_required
@owner_required
def add_turf():

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            location = request.form.get('location')
            location = location.split(",")[0].strip().title()
            latitude = request.form.get("latitude")
            longitude = request.form.get("longitude")
            description = request.form.get('description')
            price = float(request.form.get('price_per_hour'))
            address = request.form.get('address')
            image_file = request.files.get('image')
            image_url = None
            opening_time = datetime.strptime(request.form.get("opening_time"), "%H:%M").time()
            closing_time = datetime.strptime( request.form.get("closing_time"), "%H:%M").time()
            contact_phone = request.form.get("contact_phone")
            contact_email = request.form.get("contact_email")
            surface_type = request.form.get("surface_type")
            length = request.form.get("length")
            width = request.form.get("width")
            player_capacity = request.form.get("player_capacity")
            available_days = request.form.getlist("available_days")
            available_days_str = ",".join(available_days)

            # Upload logic
            if image_file and image_file.filename != "" and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                save_path = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
                image_file.save(save_path)

                image_url = f"/static/images/{filename}"  

            else:
                image_url = "/static/images/default.jpg"

            new_turf = Turf(
                name=name,
                location=location,
                description=description,
                price_per_hour=price,
                image_url=image_url,
                owner_id=current_user.id,
                address=address,
                available_days=available_days_str,
                opening_time=opening_time,
                closing_time=closing_time,
                contact_phone=contact_phone,
                contact_email=contact_email,
                surface_type=surface_type,
                length=length,
                width=width,
                player_capacity=player_capacity,
                latitude=latitude,
                longitude=longitude,
                # Facilities 
                floodlights = 'floodlights' in request.form,
                parking = 'parking' in request.form,
                wifi = 'wifi' in request.form,
                restrooms = 'restrooms' in request.form,
                refreshments = 'refreshments' in request.form
            )

            db.session.add(new_turf)
            db.session.commit()

            flash('Turf added successfully!', 'success')
            return redirect(url_for('owner_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", 'danger')

    return render_template('add_turf.html')

@app.route('/owner/turf/edit/<int:turf_id>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_turf(turf_id):
    turf = Turf.query.get_or_404(turf_id)

    if request.method == 'POST':
        try:
            new_name = request.form.get('turf_name')
            new_price = request.form.get('price')

            new_image = request.files.get('image')
            new_image_url = turf.image_url  # keeps old image

            if new_image and new_image.filename != "" and allowed_file(new_image.filename):
                filename = secure_filename(new_image.filename)
                save_path = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
                new_image.save(save_path)

                new_image_url = f"/static/images/{filename}"

            turf.name = new_name
            turf.price_per_hour = float(new_price)
            turf.image_url = new_image_url

            db.session.commit()
            flash("Turf updated successfully!", 'success')
            return redirect(url_for('owner_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating turf: {e}", 'danger')

    return render_template('edit_turf.html', turf=turf)

@app.route('/owner/analytics/<int:turf_id>')
@login_required
@owner_required
def turf_analytics(turf_id):
    """Fetches and displays detailed analytics for a specific turf, including trend data."""
    
    turf = Turf.query.get_or_404(turf_id)
    
    # Critical security check 
    if turf.owner_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('owner_dashboard'))

    # --- 1. Fetch Confirmed/Completed Bookings ---
    confirmed_bookings = Booking.query.filter(
        Booking.turf_id == turf_id,
        Booking.booking_status == 'confirmed',
        Booking.payment_status == 'completed'
    ).all()

    # Calculate Summary Metrics
    total_revenue = sum(
        float(b.total_amount) for b in confirmed_bookings if b.total_amount is not None
    )
    total_bookings = len(confirmed_bookings)
    
    # Calculate Average Rating (Existing logic)
    avg_rating_result = db.session.query(sa_func.avg(Review.rating)).filter(
        Review.turf_id == turf_id
    ).scalar()
    avg_rating = "{:.1f}".format(avg_rating_result) if avg_rating_result else "0.0"
    utilization_rate = "{:.1f}".format(total_bookings / 100 * 100)
    
    # --- 2. CRITICAL: Fetch Booking Trends Data (Last 7 Days) ---
    date_range = [datetime.now().date() - timedelta(days=i) for i in range(7)]
    date_range.reverse() # Order from oldest to newest day
    
    # Query database to count confirmed bookings per day
    daily_bookings_data = db.session.query(
        Booking.booking_date, 
        sa_func.count(Booking.id)
    ).filter(
        Booking.turf_id == turf_id,
        Booking.booking_status == 'confirmed',
        Booking.booking_date >= date_range[0] # Filter for the date range
    ).group_by(
        Booking.booking_date
    ).all()
    
    # Convert query results into Chart.js friendly format
    db_map = {}
    for date_obj, count in daily_bookings_data:
    # Use string format 'YYYY-MM-DD' as the map key
        db_map[date_obj.strftime('%Y-%m-%d')] = count
    
    # 2. Convert date_range objects into string keys for lookup
    chart_keys = [d.strftime('%Y-%m-%d') for d in date_range]

    chart_data = {
        'labels': [d.strftime('%b %d') for d in date_range],
        'counts': [db_map.get(key, 0) for key in chart_keys] # Use 0 if no bookings on that day
    }
    
  
    return render_template(
        'turf_analytics.html', 
        turf=turf, 
        total_revenue=total_revenue,
        total_bookings=total_bookings,
        avg_rating=avg_rating,
        utilization_rate=utilization_rate,
        chart_data=chart_data # Pass the trend data for the chart
    )



@app.route('/generate_report')
@login_required
def generate_report():
    # 1. Access Check
    if not current_user.is_owner:
        flash('Access denied', 'danger')
        return redirect(url_for('homepage'))
        
    # 2. Fetch Data (Example: Fetch all bookings for the owner's turfs)
    owner_turfs = Turf.query.filter_by(owner_id=current_user.id).all()
    turf_ids = [turf.id for turf in owner_turfs]
    
    # Fetch bookings for those turfs
    bookings = Booking.query.filter(Booking.turf_id.in_(turf_ids)).all()

    # 3. Create the CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write Header Row
    writer.writerow([
        'Booking ID', 'Turf Name', 'Booking Date', 'Start Time', 
        'Total Amount', 'Payment Status', 'Customer ID'
    ])
    
    # Write Data Rows
    for booking in bookings:
        writer.writerow([
            booking.id,
            booking.turf.name,
            booking.booking_date.strftime('%Y-%m-%d'),
            booking.start_time.strftime('%H:%M'),
            f"Rs {booking.total_amount}",
            booking.payment_status,
            booking.user_id
        ])

    # 4. Serve the file for download
    output.seek(0)
    
    # Convert StringIO content to bytes for send_file
    buffer = io.BytesIO(output.getvalue().encode('utf-8'))

    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'revenue_report_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/delete_turf/<int:turf_id>')
@login_required
@owner_required
def delete_turf(turf_id):
    """Handles deletion of a turf and its associated records."""
    
    # 1. Fetch the turf or abort if not found
    turf = Turf.query.get_or_404(turf_id)

    # 2. CRITICAL SECURITY CHECK: Ensure the current user owns this turf
    if turf.owner_id != current_user.id:
        flash('Unauthorized access: You can only delete your own turfs.', 'danger')
        return redirect(url_for('owner_dashboard'))

    try:
        # 3. Delete related records (Crucial step for database integrity)
        reviews = Review.query.filter_by(turf_id=turf_id).all()
        for r in reviews:
            db.session.delete(r)

        db.session.flush()

        #  To delete all bookings associated with this turf:
        bookings = Booking.query.filter_by(turf_id=turf_id).all()
        for b in bookings:
            db.session.delete(b)

        TimeSlot.query.filter_by(turf_id=turf_id).delete()

        db.session.flush()

        
        # 4. Delete the turf itself
        db.session.delete(turf)
        
        # 5. Commit the transaction
        db.session.commit()
        
        flash(f'Turf "{turf.name}" and all associated data have been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error during turf deletion: {e}")
        print("DELETE ERROR >>>", type(e).__name__, str(e)) 
        flash('Error deleting turf. Please check the terminal log.', 'danger')

    return redirect(url_for('owner_dashboard'))


    
@app.route("/fix-dates")
def fix_dates():
    import datetime
    fixed = 0

    models = [User, Turf, Booking, Review]

    for model in models:
        rows = model.query.all()
        for row in rows:
            if hasattr(row, "created_at"):
                value = row.created_at

                if not isinstance(value, datetime.datetime):
                    row.created_at = datetime.datetime.utcnow()
                    fixed += 1

    db.session.commit()
    return f"Fixed {fixed} bad datetime entries."

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
   
    # Create sample turfs if none exist
    # if not Turf.query.first():
    #     # Create a sample owner
    #     owner = User(
    #         username='owner1',
    #         email='owner@example.com',
    #         password_hash=generate_password_hash('password123'),
    #         is_owner=True
    #     )
    #     db.session.add(owner)
    #     db.session.commit()
    # existing_owner = User.query.filter_by(username="owner1").first()

    # if not existing_owner:
    #     owner = User(
    #         username='owner1',
    #         email='owner@example.com',
    #         password_hash=generate_password_hash('password123'),
    #         is_owner=True
    #     )
    #     db.session.add(owner)
    #     db.session.commit()
    # else:
    #     owner = existing_owner
        
    #     # Create sample turfs
    #     sample_turfs = [
    #         {
    #             'name': ' FC Football Turf',
    #             'location': 'Goregaon, Mumbai',
    #             'description': 'Premium artificial turf with floodlights. Perfect for football matches.',
    #             'price_per_hour': 1200,
    #             'image_url':  '/static/images/football.webp'
    #         },
    #         {
    #             'name': 'Kandivali Turf Zone',
    #             'location': 'Kandivali,Mumbai',
    #             'description': 'Multi-sport facility with cricket and football options.',
    #             'price_per_hour': 1000,
    #             'image_url': '/static/images/cricket.webp'  
    #         },
    #         {
    #             'name': 'JP Turf',
    #             'location': 'Malad,Mumbai',
    #             'description': 'Professional ground for cricket and football.',
    #             'price_per_hour': 1200,
    #             'image_url':'/static/images/c&f.jpg' 
    #         },
    #         {
    #             'name': 'Eksar Cricket Ground',
    #             'location': 'Borivali,Mumbai',
    #             'description': 'Professional cricket ground with all facilities.',
    #             'price_per_hour': 2000,
    #             'image_url':'/static/images/professionalcricket.jpg' 
    #         }
    #     ]
        
    #     for turf_data in sample_turfs:
    #         turf = Turf(owner_id=owner.id, **turf_data)
    #         db.session.add(turf)
        
    #     db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)

def handler(request):
    return app