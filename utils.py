from functools import wraps
from flask import session, redirect, url_for, request
from models import db, AuditLog

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def log_action(user_id, action, details):
    """Record an action in the audit log"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
