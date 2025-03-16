import os
from app import create_app, db, login_manager
from models import User

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import and register blueprints
from routes import main as main_blueprint
app.register_blueprint(main_blueprint)

# Create tables and admin user
with app.app_context():
    db.create_all()

    # Create admin user if not exists
    admin = User.query.filter_by(username="atha").first()
    if not admin:
        admin_user = User(
            username="atha",
            email="gameeater36@gmail.com",  # Set admin PayPal email
            is_admin=True
        )
        admin_user.set_password("teamo")
        db.session.add(admin_user)
        db.session.commit()

if __name__ == "__main__":
    # Use environment variable PORT if available (for deployment)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)