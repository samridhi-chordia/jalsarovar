"""
Authentication Controller - Login, Logout, Registration
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact admin.', 'error')
                return redirect(url_for('auth.login'))

            login_user(user, remember=remember)
            user.last_login = db.func.now()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration - restricted to admin or first user"""
    # Allow first user registration without authentication
    user_count = User.query.count()

    if user_count > 0 and (not current_user.is_authenticated or not current_user.is_admin()):
        flash('Only administrators can register new users', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'technician')

        # Validate input
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))

        # Create user - first user is admin
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role='admin' if user_count == 0 else role
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(f'User {username} registered successfully', 'success')

        if user_count == 0:
            # First user - log them in
            login_user(new_user)
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('main.users'))

    return render_template('auth/register.html')
