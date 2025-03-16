from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import stripe
import os
import requests
import threading
import time
from models import db, User, UnclaimedFund, Transaction, AuditLog
from utils import requires_auth, requires_admin, log_action
import paypalrestsdk # Added import for PayPal

main = Blueprint('main', __name__)

# Payment configurations
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
paypalrestsdk.configure({
    "mode": "sandbox", # Change to "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})


# Global flag for auto-search
auto_search_active = False

def auto_search_worker():
    """Background worker for automated fund searching"""
    global auto_search_active
    while auto_search_active:
        try:
            # Search various unclaimed fund databases
            search_unclaimed_funds_automated()
            time.sleep(3600)  # Sleep for 1 hour
        except Exception as e:
            print(f"Auto-search error: {str(e)}")
            time.sleep(300)  # On error, wait 5 minutes before retrying

def search_unclaimed_funds_automated():
    """Automated search for unclaimed funds across multiple sources"""
    # This would integrate with various unclaimed funds databases
    # For demonstration, we'll simulate finding random funds
    new_fund = UnclaimedFund(
        name="Auto Found Fund",
        amount=float(1000 + time.time() % 1000),  # Random amount
        source="Automated Search",
        original_owner_name="John Doe",
        original_owner_address="123 Main St, Any City",
        last_known_date=datetime.utcnow() - timedelta(days=365),
        jurisdiction="Various",
        fund_type="Bank Account",
        recovery_fee_percentage=10.0
    )

    db.session.add(new_fund)
    db.session.commit()

@main.route('/')
@requires_auth
def dashboard():
    """Redirect admin to admin dashboard, show regular dashboard for others"""
    user_id = session.get('user_id')
    username = User.query.get(user_id).username

    if username == "atha":
        return redirect(url_for('main.admin_dashboard'))

    # Regular users only see their claimed funds
    funds = UnclaimedFund.query.filter_by(claimed_by=user_id).all()
    return render_template('dashboard.html', funds=funds)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # Can be email or username
        password = request.form.get('password')

        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['stripe_account_id'] = user.stripe_account_id # Added this line
            log_action(user.id, 'login', f'User logged in from {request.remote_addr}')
            return redirect(url_for('main.dashboard'))

        flash('Invalid credentials', 'error')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    session.pop('stripe_account_id', None) # Added this line
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists', 'error')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        log_action(user.id, 'register', 'New user registration')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@main.route('/admin/dashboard')
@requires_admin
def admin_dashboard():
    """Admin dashboard with full fund management capabilities"""
    # Only allow access to user 'atha'
    user_id = session.get('user_id')
    username = User.query.get(user_id).username
    if username != "atha":
        flash("Access restricted to administrator.", "error")
        return redirect(url_for('main.dashboard'))

    funds = UnclaimedFund.query.all()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10)
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(20)
    now = datetime.utcnow()

    aged_funds = UnclaimedFund.query.filter(
        UnclaimedFund.status == "Pending",
        UnclaimedFund.created_at <= datetime.utcnow() - timedelta(days=90)
    ).all()

    return render_template('admin_dashboard.html',
                         funds=funds,
                         transactions=transactions,
                         audit_logs=audit_logs,
                         aged_funds=aged_funds,
                         now=now,
                         timedelta=timedelta,
                         auto_search_active=auto_search_active)

@main.route('/admin/start-auto-search', methods=['POST'])
@requires_admin
def start_auto_search():
    """Start the automated fund search process - restricted to admin only"""
    # Verify it's the admin user
    user_id = session.get('user_id')
    username = User.query.get(user_id).username
    if username != "atha":
        return jsonify({"error": "Access denied"}), 403

    global auto_search_active
    if not auto_search_active:
        auto_search_active = True
        thread = threading.Thread(target=auto_search_worker)
        thread.daemon = True
        thread.start()
        log_action(user_id, 'auto_search', 'Started automated fund search')
        return jsonify({"status": "success", "message": "Auto-search started"})
    return jsonify({"status": "success", "message": "Auto-search already running"})

@main.route('/admin/check-new-funds')
@requires_admin
def check_new_funds():
    """Check if new funds have been found in the last minute"""
    recent_funds = UnclaimedFund.query.filter(
        UnclaimedFund.created_at >= datetime.utcnow() - timedelta(minutes=1)
    ).count()
    return jsonify({"newFunds": recent_funds > 0})

@main.route('/admin/manual-search-funds', methods=['POST'])
@requires_admin
def manual_search_funds():
    """Manual search for unclaimed funds - restricted to admin only"""
    # Verify it's the admin user
    user_id = session.get('user_id')
    username = User.query.get(user_id).username
    if username != "atha":
        return jsonify({"error": "Access denied"}), 403

    name = request.form.get('name')
    location = request.form.get('location')

    try:
        # Simulate finding a fund matching the search criteria
        new_fund = UnclaimedFund(
            name=f"Fund for {name}",
            amount=1000.00,
            source="Manual Search",
            original_owner_name=name,
            original_owner_address=location,
            last_known_date=datetime.utcnow() - timedelta(days=365),
            jurisdiction=location,
            fund_type="Bank Account",
            recovery_fee_percentage=10.0
        )

        db.session.add(new_fund)
        db.session.commit()

        log_action(session['user_id'], 'fund_search', 
                  f'New fund found for {name} in {location}')

        flash('New unclaimed fund has been added to the database', 'success')
    except Exception as e:
        flash(f'Error searching for funds: {str(e)}', 'error')

    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/withdraw', methods=['POST'])
@requires_admin
def admin_withdraw():
    """Process fund withdrawal by admin"""
    fund_id = request.form.get('fund_id')
    fund = UnclaimedFund.query.get_or_404(fund_id)

    if fund.status != "Pending":
        return jsonify({"error": "Fund is not available for withdrawal"}), 400

    try:
        # Create PayPal payout
        payout = paypalrestsdk.Payout({
            "sender_batch_header": {
                "sender_batch_id": f"batch_{fund.id}_{int(time.time())}",
                "email_subject": "You have a payout!",
            },
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {
                    "value": str(fund.amount),
                    "currency": "USD"
                },
                "receiver": "gameeater36@gmail.com", # Replace with actual recipient email
                "note": f"Unclaimed fund withdrawal: {fund.id}",
                "sender_item_id": str(fund.id)
            }]
        })

        if payout.create():
            # Record transaction
            transaction = Transaction(
                fund_id=fund.id,
                user_id=session['user_id'],
                amount=fund.amount,
                type="withdrawal",
                status="completed",
                payment_method="paypal",
                payment_id=payout.batch_header.payout_batch_id
            )

            fund.status = "Claimed"
            fund.claimed_by = session['user_id']
            fund.claimed_at = datetime.utcnow()

            db.session.add(transaction)
            db.session.commit()

            log_action(session['user_id'], 'admin_withdrawal', 
                      f'Admin withdrew fund {fund.id} via PayPal')

            return jsonify({
                "status": "success",
                "message": "Fund withdrawn successfully to PayPal"
            })
        else:
            return jsonify({"error": payout.error}), 400

    except Exception as e:
        log_action(session['user_id'], 'withdrawal_error', str(e))
        return jsonify({"error": str(e)}), 400

@main.route('/admin/process-aged-funds', methods=['POST'])
@requires_admin
def process_aged_funds():
    """Process funds that have been unclaimed for over 90 days"""
    aged_funds = UnclaimedFund.query.filter(
        UnclaimedFund.status == "Pending",
        UnclaimedFund.created_at <= datetime.utcnow() - timedelta(days=90)
    ).all()

    admin = User.query.filter_by(username="atha").first()

    for fund in aged_funds:
        try:
            # Create Stripe transfer
            transfer = stripe.Transfer.create(
                amount=int(fund.amount * 100),  # Convert to cents
                currency="usd",
                destination=admin.stripe_account_id,
                transfer_group=f"aged_fund_{fund.id}"
            )

            # Record transaction
            transaction = Transaction(
                fund_id=fund.id,
                user_id=admin.id,
                amount=fund.amount,
                type="transfer",
                status="completed",
                payment_method="stripe",
                payment_id=transfer.id
            )

            fund.status = "Transferred"
            fund.claimed_by = admin.id
            fund.claimed_at = datetime.utcnow()

            db.session.add(transaction)
            log_action(admin.id, 'aged_fund_transfer', f'Processed aged fund {fund.id}')

        except stripe.error.StripeError as e:
            log_action(admin.id, 'transfer_error', str(e))
            return jsonify({"error": str(e)}), 400

    db.session.commit()
    return jsonify({"message": "Aged funds processed successfully"})

@main.route('/withdraw', methods=['POST'])
@requires_auth
def withdraw_funds():
    """Handle fund withdrawal requests"""
    fund_id = request.form.get('fund_id')

    fund = UnclaimedFund.query.get_or_404(fund_id)

    if fund.status != "Pending":
        return jsonify({"error": "Fund is not available for withdrawal"}), 400

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(fund.amount * 100),
            currency="usd",
            payment_method_types=["card"],
            metadata={"fund_id": fund_id}
        )

        transaction = Transaction(
            fund_id=fund_id,
            user_id=session['user_id'],
            amount=fund.amount,
            type="withdrawal",
            payment_method="stripe",
            payment_id=payment_intent.id
        )

        db.session.add(transaction)
        fund.status = "Processing"
        db.session.commit()

        log_action(session['user_id'], 'withdrawal_initiated', 
                  f'Withdrawal initiated for fund {fund_id}')

        return jsonify({
            "status": "success",
            "payment_id": transaction.payment_id
        })

    except Exception as e:
        log_action(session['user_id'], 'withdrawal_error', str(e))
        return jsonify({"error": str(e)}), 400