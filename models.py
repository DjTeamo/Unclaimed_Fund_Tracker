from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    stripe_account_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class UnclaimedFund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="Pending")
    original_owner_name = db.Column(db.String(200))
    original_owner_address = db.Column(db.String(500))
    original_owner_contact = db.Column(db.String(200))
    last_known_date = db.Column(db.DateTime)
    jurisdiction = db.Column(db.String(100))
    fund_type = db.Column(db.String(100))
    recovery_fee_percentage = db.Column(db.Float, default=10.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    claimed_at = db.Column(db.DateTime)
    claimed_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    @property
    def is_aged(self):
        """Check if the fund is over 90 days old"""
        age_threshold = datetime.utcnow() - timedelta(days=90)
        return self.created_at <= age_threshold

    @property
    def recovery_fee(self):
        """Calculate the recovery fee amount"""
        return (self.amount * self.recovery_fee_percentage) / 100

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fund_id = db.Column(db.Integer, db.ForeignKey('unclaimed_fund.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # withdrawal, transfer, recovery
    status = db.Column(db.String(50), default="Pending")
    payment_method = db.Column(db.String(50))  # stripe
    payment_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
