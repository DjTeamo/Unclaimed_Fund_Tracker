from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
import os

# Set up base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize Flask-SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configure the Flask application
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

    # Database configuration
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # Initialize PayPal in production mode
    if os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_CLIENT_SECRET"):
        import paypalrestsdk
        paypalrestsdk.configure({
            "mode": "live",
            "client_id": os.environ.get("PAYPAL_CLIENT_ID"),
            "client_secret": os.environ.get("PAYPAL_CLIENT_SECRET")
        })

    # Initialize Stripe
    if os.environ.get("STRIPE_SECRET_KEY"):
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    return app