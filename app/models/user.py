"""User model for authentication"""
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app
from itsdangerous import URLSafeTimedSerializer
from app import db, login_manager
import secrets


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for OAuth users
    full_name = db.Column(db.String(150))

    # OAuth Support
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', null for manual
    oauth_id = db.Column(db.String(256), nullable=True, index=True)
    oauth_data = db.Column(db.JSON, nullable=True)  # Store profile pic, etc.

    # Email Verification
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    verification_token = db.Column(db.String(256), nullable=True, index=True)
    verification_token_expiry = db.Column(db.DateTime, nullable=True)

    # Password Reset
    password_reset_token = db.Column(db.String(256), nullable=True, index=True)
    password_reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Enhanced Role Management (10 roles)
    role = db.Column(db.String(30), default='viewer', index=True)
    # Roles: viewer, citizen_contributor, researcher, field_collector, analyst,
    # lab_partner, industry_partner, government_official, site_manager, admin
    role_status = db.Column(db.String(20), default='active', nullable=False)  # active, pending, rejected
    role_requested = db.Column(db.String(30), nullable=True)
    role_approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role_approved_date = db.Column(db.DateTime, nullable=True)

    # Organization Details (for Lab/Industry/Govt roles)
    organization_name = db.Column(db.String(200), nullable=True)
    organization_type = db.Column(db.String(50), nullable=True)  # lab, industry, government, ngo
    job_title = db.Column(db.String(100), nullable=True)

    # Site Assignments (for Site Manager, Industry Partner)
    assigned_sites = db.Column(db.JSON, nullable=True)  # Array of site IDs

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    samples = db.relationship('WaterSample', backref='collector', lazy='dynamic',
                              foreign_keys='WaterSample.collected_by_id')
    tests = db.relationship('TestResult', backref='tester', lazy='dynamic',
                            foreign_keys='TestResult.tested_by_id')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify password"""
        if not self.password_hash:
            return False  # OAuth users don't have passwords
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_oauth_user(self):
        """Check if user registered via OAuth"""
        return self.oauth_provider is not None

    def can_login(self):
        """Check if user can login (active, email verified, role approved)"""
        if not self.is_active:
            return False, "Account is inactive"
        if not self.email_verified and not self.is_oauth_user():
            return False, "Email not verified"
        if self.role_status == 'pending':
            return False, "Role approval pending"
        return True, None

    # Email Verification Methods
    def generate_verification_token(self):
        """Generate email verification token (24hr expiry)"""
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.verification_token

    def verify_email_token(self, token):
        """Verify email verification token"""
        if not self.verification_token or not self.verification_token_expiry:
            return False
        if self.verification_token != token:
            return False
        if datetime.utcnow() > self.verification_token_expiry:
            return False
        # Mark as verified
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.verification_token = None
        self.verification_token_expiry = None
        return True

    # Password Reset Methods
    def generate_password_reset_token(self):
        """Generate password reset token (2hr expiry)"""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_token_expiry = datetime.utcnow() + timedelta(hours=2)
        return self.password_reset_token

    def verify_password_reset_token(self, token):
        """Verify password reset token"""
        if not self.password_reset_token or not self.password_reset_token_expiry:
            return False
        if self.password_reset_token != token:
            return False
        if datetime.utcnow() > self.password_reset_token_expiry:
            return False
        return True

    def reset_password(self, new_password):
        """Reset password and clear reset token"""
        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_token_expiry = None

    # Permission Methods
    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        # Import here to avoid circular dependency
        from app.models.role_permission import RolePermission

        perm = RolePermission.query.filter_by(role=self.role).first()
        if not perm:
            return False

        return getattr(perm, permission_name, False)

    def get_accessible_sites(self):
        """Get list of site IDs this user can access"""
        if self.role in ['admin', 'analyst', 'government_official', 'researcher', 'field_collector']:
            return 'all'  # Access to all sites
        elif self.role in ['site_manager', 'industry_partner']:
            return self.assigned_sites or []
        else:
            return 'public'  # Only public sites

    def can_access_site(self, site_id):
        """Check if user can access a specific site"""
        accessible = self.get_accessible_sites()
        if accessible == 'all':
            return True
        elif accessible == 'public':
            # Check if site is public (need to query site)
            from app.models import Site
            site = Site.query.get(site_id)
            return site and site.site_category == 'public'
        else:
            # Check if site is in assigned list
            return site_id in (accessible or [])

    def can_edit_site(self, site_id):
        """Check if user can edit a specific site"""
        if not self.has_permission('can_edit_sites'):
            return False
        return self.can_access_site(site_id)

    def can_create_sample_for_site(self, site_id):
        """Check if user can create samples for a specific site"""
        if not self.has_permission('can_create_samples'):
            return False
        return self.can_access_site(site_id)

    def filter_sites_query(self, query):
        """Apply site filtering to a SQLAlchemy query based on user's access"""
        from app.models import Site

        accessible = self.get_accessible_sites()
        if accessible == 'all':
            return query  # No filtering needed
        elif accessible == 'public':
            return query.filter(Site.site_category == 'public')
        else:
            # Filter by assigned site IDs
            if accessible:
                return query.filter(Site.id.in_(accessible))
            else:
                # No assigned sites - return empty query
                return query.filter(Site.id == -1)  # No site has ID -1

    def request_role_upgrade(self, requested_role, reason, organization_name=None):
        """Request role upgrade (requires admin approval for restricted roles)"""
        restricted_roles = ['field_collector', 'analyst', 'lab_partner', 'industry_partner',
                          'government_official', 'site_manager', 'admin']

        if requested_role in restricted_roles:
            self.role_requested = requested_role
            self.role_status = 'pending'
            if organization_name:
                self.organization_name = organization_name
        else:
            # Public roles can be auto-approved
            self.role = requested_role
            self.role_status = 'active'

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))
