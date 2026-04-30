# Turf Booking System

A comprehensive online turf booking system built with Python Flask, featuring real-time slot management, secure payments, and responsive design.

## Features

### Core Features
-  **Real-time Slot Management** - Live availability updates with conflict prevention
-  **Secure Payment Integration** - Stripe API for safe online transactions  
-  **Email Confirmations** - Automated booking confirmations via email
- 📱 **Mobile-Friendly Design** - Fully responsive UI for all devices
-  **User Authentication** - Secure login/signup with role-based access
- 🔍 **Advanced Search & Filters** - Find turfs by location, name, and features
- 📅 **Advance Booking** - Book slots up to 7 days in advance
- 📊 **Booking Management** - Track and manage all reservations

### User Types
- **Customers** - Browse, book, and manage turf reservations
- **Turf Owners** - Add and manage turf listings

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **Authentication**: Flask-Login
- **Payments**: Stripe API
- **Email**: SMTP (Gmail)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Icons**: Font Awesome

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Stripe account (for payment processing)
- Gmail account (for email notifications)

### Step 1: Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configuration

Open `app.py` and update the following configuration variables:

```python
# Secret key for session management
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Stripe Configuration
stripe.api_key = "sk_test_your_stripe_secret_key"  # Your Stripe Secret Key
STRIPE_PUBLISHABLE_KEY = "pk_test_your_stripe_publishable_key"  # Your Stripe Publishable Key

# Email Configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'your-email@gmail.com'  # Your email
EMAIL_PASS = 'your-app-password'     # Your Gmail app password
```

### Step 3: Get API Keys

#### Stripe Setup:
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Create an account or login
3. Go to Developers > API Keys
4. Copy your Publishable Key and Secret Key
5. Update the keys in `app.py`

#### Gmail Setup:
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password for the application
3. Use your Gmail address and app password in the configuration

### Step 4: Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage Guide

### For Customers

1. **Registration**: Create an account using the signup page
2. **Browse Turfs**: Use the search and filter options to find suitable turfs
3. **View Details**: Check turf information, facilities, and available time slots
4. **Book Slot**: Select preferred time and complete the booking form
5. **Payment**: Securely pay using credit/debit cards via Stripe
6. **Confirmation**: Receive email confirmation and booking details
7. **Manage Bookings**: View history and cancel bookings (24hr+ advance notice)

### For Turf Owners

1. **Register as Owner**: Select "I am a turf owner" during signup
2. **Dashboard**: Access owner dashboard to manage turfs
3. **Add Turf**: Create listings with details, images, and pricing
4. **View Bookings**: Monitor reservations and revenue

### Default Login Credentials

The system creates sample data on first run:
- **Sample Owner**: username: `owner1`, password: `password123`




## Code Explanation

### app.py (Main Application)
- **Database Models**: User, Turf, TimeSlot, Booking models with relationships
- **Authentication**: Login/logout functionality with Flask-Login
- **Routes**: All page routes and API endpoints
- **Payment Processing**: Stripe integration for secure payments
- **Email System**: SMTP email sending for confirmations
- **Business Logic**: Booking validation, conflict management

### Templates
- **base.html**: Common layout with responsive navigation, authentication states
- **index.html**: Attractive landing page with features and call-to-action
- **login/signup.html**: User authentication forms with validation
- **homepage.html**: Dashboard with search functionality and turf grid
- **all_bookings.html**: Enhanced turf browsing with filters and search
- **turf_details.html**: Detailed turf view with time slot selection
- **booking_form.html**: Comprehensive checkout form with customer details
- **payment.html**: Secure Stripe payment integration
- **confirmation.html**: Booking success page with next steps
- **order_history.html**: Complete booking management with filters

## Security Features

- Password hashing with Werkzeug
- CSRF protection via Flask
- Secure payment processing with Stripe
- Session management with Flask-Login
- SQL injection prevention with SQLAlchemy ORM
- Email confirmation system

## Customization

### Adding New Features
- Extend database models in `app.py`
- Add new routes and templates as needed
- Update navigation in `base.html`

### Styling
- Modify CSS in template `<style>` sections
- Update Bootstrap classes for different themes
- Add custom CSS files if needed

### Payment Methods
- Integrate additional payment gateways
- Add UPI, wallet, or other local payment options
- Modify payment.html template accordingly

## Production Deployment

### Database
Replace SQLite with PostgreSQL or MySQL:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@host:port/dbname'
```

### Environment Variables
Use environment variables for sensitive data:
```python
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
```

### Web Server
Deploy with Gunicorn, uWSGI, or similar WSGI server.

## Troubleshooting

### Common Issues

1. **Email not sending**: Verify Gmail app password and 2FA settings
2. **Stripe payments failing**: Check API keys and test mode settings  
3. **Database errors**: Ensure SQLite file permissions are correct
4. **Import errors**: Verify all dependencies are installed in virtual environment

### Getting Help

- Check Flask documentation: https://flask.palletsprojects.com/
- Stripe documentation: https://stripe.com/docs
- Bootstrap documentation: https://getbootstrap.com/docs/

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with proper testing
4. Submit pull request with description

---

**Note**: This is a complete, functional turf booking system suitable for learning and small-scale deployment. For production use, consider additional security measures, error handling, and scalability optimizations.