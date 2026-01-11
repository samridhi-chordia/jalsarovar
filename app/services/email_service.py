"""Email service for sending notifications"""
from flask import current_app, render_template, url_for
from flask_mail import Message
from threading import Thread
from app import mail


def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")


def send_email(subject, recipients, template, **kwargs):
    """
    Send email using template

    Args:
        subject: Email subject line
        recipients: Email address or list of addresses
        template: Template path (without extension)
        **kwargs: Template variables
    """
    app = current_app._get_current_object()

    # Ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [recipients]

    msg = Message(
        subject=subject,
        recipients=recipients,
        sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@jalsarovar.com')
    )

    # Render HTML and text versions
    try:
        msg.html = render_template(f'email/{template}.html', **kwargs)
    except:
        msg.html = None

    try:
        msg.body = render_template(f'email/{template}.txt', **kwargs)
    except:
        # Fallback to simple text
        msg.body = f"Jal Sarovar Notification: {subject}"

    # Send asynchronously
    Thread(target=send_async_email, args=(app, msg)).start()


def send_verification_email(user):
    """
    Send email verification link

    Args:
        user: User object with verification_token
    """
    app = current_app._get_current_object()
    site_url = app.config.get('SITE_URL', 'https://jalsarovar.com')

    # Try to use url_for if in request context, otherwise build URL manually
    try:
        verification_url = url_for('auth.verify_email',
                                  token=user.verification_token,
                                  _external=True)
    except RuntimeError:
        # Outside request context, build URL manually
        verification_url = f"{site_url}/auth/verify-email?token={user.verification_token}"

    send_email(
        subject='Verify Your Email - Jal Sarovar',
        recipients=user.email,
        template='verification_email',
        user_name=user.full_name or user.username,
        verification_url=verification_url,
        expiry_hours=24
    )


def send_welcome_email(user):
    """
    Send welcome email after successful registration

    Args:
        user: User object
    """
    app = current_app._get_current_object()
    site_url = app.config.get('SITE_URL', 'https://jalsarovar.com')

    # Try to use url_for if in request context, otherwise build URL manually
    try:
        dashboard_url = url_for('dashboard.index', _external=True)
    except RuntimeError:
        dashboard_url = f"{site_url}/dashboard"

    send_email(
        subject='Welcome to Jal Sarovar!',
        recipients=user.email,
        template='welcome_email',
        user_name=user.full_name or user.username,
        role=user.role.replace('_', ' ').title(),
        dashboard_url=dashboard_url
    )


def send_password_reset_email(user):
    """
    Send password reset link

    Args:
        user: User object with password_reset_token
    """
    app = current_app._get_current_object()
    site_url = app.config.get('SITE_URL', 'https://jalsarovar.com')

    # Try to use url_for if in request context, otherwise build URL manually
    try:
        reset_url = url_for('auth.reset_password',
                           token=user.password_reset_token,
                           _external=True)
    except RuntimeError:
        reset_url = f"{site_url}/auth/reset-password?token={user.password_reset_token}"

    send_email(
        subject='Reset Your Password - Jal Sarovar',
        recipients=user.email,
        template='password_reset_email',
        user_name=user.full_name or user.username,
        reset_url=reset_url,
        expiry_hours=2
    )


def send_role_approval_email(user):
    """
    Notify user that their role request was approved

    Args:
        user: User object with approved role
    """
    send_email(
        subject='Role Approved - Jal Sarovar',
        recipients=user.email,
        template='role_approved',
        user_name=user.full_name or user.username,
        role=user.role.replace('_', ' ').title(),
        dashboard_url=url_for('main.dashboard', _external=True)
    )


def send_role_rejection_email(user, reason):
    """
    Notify user that their role request was rejected

    Args:
        user: User object
        reason: Rejection reason text
    """
    send_email(
        subject='Role Request Not Approved - Jal Sarovar',
        recipients=user.email,
        template='role_rejected',
        user_name=user.full_name or user.username,
        requested_role=user.role_requested.replace('_', ' ').title() if user.role_requested else 'Unknown',
        reason=reason,
        contact_url=url_for('portfolio.contact', _external=True)
    )


def send_revision_request_email(user, notes):
    """
    Notify user that revision is needed for their submission

    Args:
        user: User object
        notes: Revision notes from admin
    """
    send_email(
        subject='Revision Needed - Jal Sarovar',
        recipients=user.email,
        template='submission_revision',
        user_name=user.full_name or user.username,
        revision_notes=notes,
        submissions_url=url_for('submissions.history', _external=True)
    )


def send_submission_approval_email(user):
    """
    Notify user that their data submission was approved

    Args:
        user: User object
    """
    send_email(
        subject='Submission Approved - Jal Sarovar',
        recipients=user.email,
        template='submission_approved',
        user_name=user.full_name or user.username,
        dashboard_url=url_for('main.dashboard', _external=True)
    )


def send_submission_rejection_email(user, reason):
    """
    Notify user that their data submission was rejected

    Args:
        user: User object
        reason: Rejection reason
    """
    send_email(
        subject='Submission Not Approved - Jal Sarovar',
        recipients=user.email,
        template='submission_rejected',
        user_name=user.full_name or user.username,
        reason=reason,
        submissions_url=url_for('submissions.history', _external=True)
    )
