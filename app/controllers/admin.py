"""Admin routes - User and system management"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import csv
import io
from app import db
from app.models import User, Site
from app.services.email_service import send_role_approval_email, send_role_rejection_email

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_sites': Site.query.count(),
        'active_sites': Site.query.filter_by(is_active=True).count()
    }
    return render_template('admin/index.html', stats=stats)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management"""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """Create new user"""
    if request.method == 'POST':
        user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            full_name=request.form.get('full_name'),
            role=request.form.get('role', 'viewer')
        )
        user.set_password(request.form.get('password'))

        db.session.add(user)
        db.session.commit()

        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=None)


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        user.role = request.form.get('role')
        user.is_active = request.form.get('is_active') == 'on'

        # Handle site assignments for site_manager, industry_partner, and lab_partner
        assigned_site_ids = request.form.getlist('assigned_sites')
        if user.role in ['site_manager', 'industry_partner', 'lab_partner']:
            if assigned_site_ids:
                user.assigned_sites = [int(site_id) for site_id in assigned_site_ids]
            else:
                user.assigned_sites = None
        else:
            # Clear site assignments for other roles
            user.assigned_sites = None

        if request.form.get('password'):
            user.set_password(request.form.get('password'))

        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))

    # Load sites for the form
    sites = Site.query.filter_by(is_active=True).order_by(Site.site_name).all()
    return render_template('admin/user_form.html', user=user, sites=sites)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    return jsonify({
        'success': True,
        'is_active': user.is_active
    })


@admin_bp.route('/system')
@login_required
@admin_required
def system():
    """System settings and status"""
    from flask import current_app

    config_info = {
        'database': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1] if '@' in current_app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'configured',
        'debug': current_app.config.get('DEBUG'),
        'ml_models_path': current_app.config.get('ML_MODELS_PATH')
    }

    return render_template('admin/system.html', config=config_info)


@admin_bp.route('/download-template')
@login_required
@admin_required
def download_template():
    """Download CSV template for data import"""
    # Create a CSV with headers and sample data
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row with all required fields
    headers = [
        # Site information
        'site_code',
        'site_name',
        'state',
        'district',
        'block',
        'village',
        'latitude',
        'longitude',
        'site_type',
        'site_category',
        'water_source',
        # Sample information
        'collection_date',
        # Core water quality parameters
        'ph',
        'turbidity_ntu',
        'tds_ppm',
        'total_coliform_mpn',
        'temperature_celsius',
        'iron_mg_l',
        'chloride_mg_l'
    ]
    writer.writerow(headers)

    # Sample data rows (example data)
    sample_rows = [
        [
            'AS-TN-0001',
            'Village Pond Kanchipuram',
            'Tamil Nadu',
            'Kanchipuram',
            'Sriperumbudur',
            'Oragadam',
            '12.8234',
            '79.9876',
            'pond',
            'public',
            'groundwater',
            '2024-01-15',
            '7.2',
            '4.5',
            '320',
            '12',
            '28.5',
            '0.15',
            '180'
        ],
        [
            'AS-TN-0002',
            'Community Tank Chennai',
            'Tamil Nadu',
            'Chennai',
            'Ambattur',
            'Korattur',
            '13.1023',
            '80.1547',
            'tank',
            'residential',
            'surface',
            '2024-01-20',
            '6.8',
            '8.2',
            '450',
            '28',
            '30.1',
            '0.25',
            '210'
        ]
    ]
    for row in sample_rows:
        writer.writerow(row)

    # Create the response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=jal_sarovar_import_template.csv',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )


# ============ ROLE APPROVAL ROUTES ============

@admin_bp.route('/role-requests')
@login_required
@admin_required
def role_requests():
    """List all pending role requests"""
    status_filter = request.args.get('status', 'pending')

    # Build query
    query = User.query

    if status_filter == 'pending':
        query = query.filter_by(role_status='pending')
    elif status_filter == 'approved':
        query = query.filter(User.role_approved_date.isnot(None))
    elif status_filter == 'all':
        query = query.filter(User.role_requested.isnot(None))

    # Order by submission date (most recent first)
    users = query.order_by(User.created_at.desc()).all()

    # Calculate stats
    stats = {
        'pending': User.query.filter_by(role_status='pending').count(),
        'approved_today': User.query.filter(
            User.role_approved_date >= datetime.utcnow().date()
        ).count() if User.query.filter(User.role_approved_date.isnot(None)).count() > 0 else 0,
        'total_requests': User.query.filter(User.role_requested.isnot(None)).count()
    }

    return render_template('admin/role_requests.html',
                         users=users,
                         stats=stats,
                         status_filter=status_filter)


@admin_bp.route('/role-requests/<int:user_id>')
@login_required
@admin_required
def role_request_detail(user_id):
    """View detailed role request"""
    user = User.query.get_or_404(user_id)

    # Get all sites for site assignment (for site_manager role)
    sites = Site.query.filter_by(is_active=True).order_by(Site.site_name).all()

    return render_template('admin/role_request_detail.html',
                         user=user,
                         sites=sites)


@admin_bp.route('/role-requests/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_role_request(user_id):
    """Approve a role request"""
    user = User.query.get_or_404(user_id)

    if not user.role_requested:
        flash('No role request found for this user.', 'error')
        return redirect(url_for('admin.role_requests'))

    # Get assigned sites for site_manager or industry_partner
    assigned_site_ids = request.form.getlist('assigned_sites')

    # Update user role
    user.role = user.role_requested
    user.role_status = 'active'
    user.role_approved_by_id = current_user.id
    user.role_approved_date = datetime.utcnow()

    # Assign sites if applicable
    if user.role in ['site_manager', 'industry_partner'] and assigned_site_ids:
        user.assigned_sites = [int(site_id) for site_id in assigned_site_ids]

    # Clear the request
    user.role_requested = None

    db.session.commit()

    # Send approval email
    try:
        send_role_approval_email(user)
    except Exception as e:
        flash(f'Role approved, but email notification failed: {str(e)}', 'warning')

    flash(f'Role request approved! {user.username} is now a {user.role.replace("_", " ").title()}.', 'success')
    return redirect(url_for('admin.role_requests'))


@admin_bp.route('/role-requests/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_role_request(user_id):
    """Reject a role request"""
    user = User.query.get_or_404(user_id)

    if not user.role_requested:
        flash('No role request found for this user.', 'error')
        return redirect(url_for('admin.role_requests'))

    rejection_reason = request.form.get('rejection_reason', '').strip()

    if not rejection_reason:
        flash('Please provide a reason for rejection.', 'error')
        return redirect(url_for('admin.role_request_detail', user_id=user_id))

    # Store the requested role for email
    requested_role = user.role_requested

    # Clear the request and set status to active (keeps current role)
    user.role_requested = None
    user.role_status = 'active'
    user.role_approved_by_id = current_user.id
    user.role_approved_date = datetime.utcnow()

    db.session.commit()

    # Send rejection email
    try:
        # Temporarily set role_requested for email template
        user.role_requested = requested_role
        send_role_rejection_email(user, rejection_reason)
        user.role_requested = None
    except Exception as e:
        flash(f'Role rejected, but email notification failed: {str(e)}', 'warning')

    flash(f'Role request rejected. User will keep their current {user.role} role.', 'info')
    return redirect(url_for('admin.role_requests'))


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)

    if user.is_admin() and User.query.filter_by(role='admin', is_active=True).count() == 1:
        flash('Cannot deactivate the last admin user.', 'error')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('admin.users'))
