"""Authentication routes"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth, limiter
from app.models import User
from app.services.email_service import (
    send_verification_email, send_welcome_email, send_password_reset_email
)
import secrets

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        # Allow login with username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            # Check if account can login
            can_login, message = user.can_login()
            if not can_login:
                flash(message, 'error')
                if 'Email not verified' in message:
                    flash('Please check your email for verification link.', 'info')
                    return render_template('auth/login.html', show_resend=True, user_email=user.email)
                elif 'Role approval pending' in message:
                    return redirect(url_for('auth.pending_approval'))
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username/email or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'viewer')  # User-selected role

        # Organization fields (for institutional roles)
        organization_name = request.form.get('organization_name')
        organization_type = request.form.get('organization_type')
        job_title = request.form.get('job_title')

        # Check existing user
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register.html')

        # Determine if role requires approval
        restricted_roles = ['field_collector', 'analyst', 'lab_partner', 'industry_partner',
                          'government_official', 'site_manager', 'admin']

        # Roles that require organization details
        org_required_roles = ['lab_partner', 'industry_partner', 'government_official']

        # Validate organization fields for institutional roles
        if role in org_required_roles:
            if not organization_name or not organization_type or not job_title:
                flash('Organization details are required for this role.', 'error')
                return render_template('auth/register.html')

        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role='viewer' if role in restricted_roles else role,  # Start as viewer if restricted
            role_requested=role if role in restricted_roles else None,
            role_status='pending' if role in restricted_roles else 'active',
            email_verified=False,
            # Organization details (if provided)
            organization_name=organization_name if organization_name else None,
            organization_type=organization_type if organization_type else None,
            job_title=job_title if job_title else None
        )
        user.set_password(password)

        # Generate verification token
        user.generate_verification_token()

        db.session.add(user)
        db.session.commit()

        # Send verification email
        try:
            send_verification_email(user)
            flash('Registration successful! Please check your email to verify your account.', 'success')
        except Exception as e:
            flash('Registration successful, but email verification failed. Please contact support.', 'warning')

        return redirect(url_for('auth.verify_email_sent'))

    return render_template('auth/register.html')


# ============ GOOGLE OAUTH ROUTES ============

@auth_bp.route('/google')
def google_login():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user information from Google.', 'error')
            return redirect(url_for('auth.login'))

        email = user_info.get('email')
        google_id = user_info.get('sub')
        full_name = user_info.get('name')
        picture = user_info.get('picture')

        # Check if user exists by OAuth ID
        user = User.query.filter_by(oauth_provider='google', oauth_id=google_id).first()

        if not user:
            # Check if email exists
            user = User.query.filter_by(email=email).first()
            if user:
                # Link OAuth to existing account
                user.oauth_provider = 'google'
                user.oauth_id = google_id
                user.oauth_data = {'picture': picture}
                user.email_verified = True  # Google verified
                user.email_verified_at = datetime.utcnow()
            else:
                # Create new user
                user = User(
                    username=email.split('@')[0] + '_' + secrets.token_hex(4),  # Generate unique username
                    email=email,
                    full_name=full_name,
                    oauth_provider='google',
                    oauth_id=google_id,
                    oauth_data={'picture': picture},
                    role='viewer',
                    role_status='active',
                    email_verified=True,
                    email_verified_at=datetime.utcnow()
                )
                db.session.add(user)

        db.session.commit()

        # Check if user can login
        can_login, message = user.can_login()
        if not can_login:
            if 'Role approval pending' in message:
                flash('Your account is pending role approval. You will be notified via email.', 'info')
                return redirect(url_for('auth.pending_approval'))
            flash(message, 'error')
            return redirect(url_for('auth.login'))

        # Login user
        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Send welcome email for new users
        if user.created_at and (datetime.utcnow() - user.created_at).seconds < 60:
            try:
                send_welcome_email(user)
            except:
                pass

        flash(f'Welcome back, {user.full_name or user.username}!', 'success')
        return redirect(url_for('dashboard.index'))

    except Exception as e:
        flash(f'OAuth error: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


# ============ EMAIL VERIFICATION ROUTES ============

@auth_bp.route('/verify-email-sent')
def verify_email_sent():
    """Show email verification sent page"""
    return render_template('auth/verify_email_sent.html')


@auth_bp.route('/verify-email')
def verify_email():
    """Verify email with token"""
    token = request.args.get('token')
    if not token:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(verification_token=token).first()
    if not user:
        flash('Invalid or expired verification token.', 'error')
        return redirect(url_for('auth.login'))

    if user.verify_email_token(token):
        db.session.commit()

        # Send welcome email
        try:
            send_welcome_email(user)
        except:
            pass

        flash('Email verified successfully! You can now log in.', 'success')

        # Check if role approval is pending
        if user.role_status == 'pending':
            flash('Your role request is pending admin approval. You will be notified via email.', 'info')
            return redirect(url_for('auth.pending_approval'))

        return redirect(url_for('auth.login'))
    else:
        flash('Invalid or expired verification token.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/resend-verification', methods=['POST'])
@limiter.limit("10 per hour")
def resend_verification():
    """Resend verification email"""
    email = request.form.get('email')
    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists
        flash('If an account with that email exists, a verification email has been sent.', 'info')
        return redirect(url_for('auth.verify_email_sent'))

    if user.email_verified:
        flash('Email is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    # Generate new token
    user.generate_verification_token()
    db.session.commit()

    # Send email
    try:
        send_verification_email(user)
        flash('Verification email sent! Please check your inbox.', 'success')
    except Exception as e:
        flash('Failed to send verification email. Please try again later.', 'error')

    return redirect(url_for('auth.verify_email_sent'))


# ============ PASSWORD RESET ROUTES ============

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def forgot_password():
    """Forgot password page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email')

        # Always show success message (no email enumeration)
        flash('If an account with that email exists, a password reset link has been sent.', 'info')

        user = User.query.filter_by(email=email).first()
        if user and not user.is_oauth_user():
            # Generate reset token
            user.generate_password_reset_token()
            db.session.commit()

            # Send reset email
            try:
                send_password_reset_email(user)
            except:
                pass

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password with token"""
    token = request.args.get('token')
    if not token:
        flash('Invalid password reset link.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(password_reset_token=token).first()
    if not user:
        flash('Invalid or expired password reset token.', 'error')
        return redirect(url_for('auth.login'))

    if not user.verify_password_reset_token(token):
        flash('Password reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('auth/reset_password.html', token=token)

        # Reset password
        user.reset_password(password)
        db.session.commit()

        flash('Password reset successfully! Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


# ============ PENDING APPROVAL PAGE ============

@auth_bp.route('/pending-approval')
def pending_approval():
    """Show pending role approval page"""
    return render_template('auth/pending_approval.html')


# ============ AJAX ENDPOINTS ============

@auth_bp.route('/check-username')
def check_username():
    """Check if username is available (AJAX endpoint)"""
    username = request.args.get('username', '').strip()

    if not username or len(username) < 3:
        return {'available': False, 'message': 'Username too short'}

    # Check if username exists
    user = User.query.filter_by(username=username).first()

    return {
        'available': user is None,
        'message': 'Available' if user is None else 'Username already taken'
    }
