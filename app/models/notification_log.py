"""
Notification Log Model
Tracks all SMS, Voice, and WhatsApp notifications sent via Twilio
"""
from datetime import datetime
from app import db


class NotificationLog(db.Model):
    """Log of all notifications sent via Twilio (SMS, Voice, WhatsApp)"""
    __tablename__ = 'notification_log'

    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(20), nullable=False, index=True)  # 'sms', 'voice', 'whatsapp'
    site_type = db.Column(db.String(20), index=True)  # 'public', 'residential'
    site_identifier = db.Column(db.String(50), index=True)  # site_code or device_id
    recipient_phone = db.Column(db.String(20))
    message_content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, queued, sent, delivered, failed
    twilio_message_sid = db.Column(db.String(100), unique=True, index=True)
    twilio_error_code = db.Column(db.String(10))
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    failed_at = db.Column(db.DateTime)

    # Retry tracking
    retry_count = db.Column(db.Integer, default=0)
    last_retry_at = db.Column(db.DateTime)

    # Optional: Link to related entities
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f'<NotificationLog {self.id} {self.notification_type} to {self.recipient_phone} status={self.status}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'site_type': self.site_type,
            'site_identifier': self.site_identifier,
            'recipient_phone': self.recipient_phone,
            'message_content': self.message_content,
            'status': self.status,
            'twilio_message_sid': self.twilio_message_sid,
            'twilio_error_code': self.twilio_error_code,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'retry_count': self.retry_count,
            'last_retry_at': self.last_retry_at.isoformat() if self.last_retry_at else None,
        }

    @staticmethod
    def get_recent_logs(limit=100, notification_type=None, status=None):
        """Get recent notification logs with optional filters"""
        query = NotificationLog.query

        if notification_type:
            query = query.filter_by(notification_type=notification_type)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_logs_by_site(site_identifier, site_type=None, limit=50):
        """Get notification logs for a specific site"""
        query = NotificationLog.query.filter_by(site_identifier=site_identifier)

        if site_type:
            query = query.filter_by(site_type=site_type)

        return query.order_by(NotificationLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_failed_logs(limit=100):
        """Get failed notifications that may need retry"""
        return NotificationLog.query.filter_by(status='failed').order_by(
            NotificationLog.created_at.desc()
        ).limit(limit).all()

    @staticmethod
    def get_statistics(days=7):
        """Get notification statistics for the last N days"""
        from sqlalchemy import func
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stats = db.session.query(
            NotificationLog.notification_type,
            NotificationLog.status,
            func.count(NotificationLog.id).label('count')
        ).filter(
            NotificationLog.created_at >= cutoff_date
        ).group_by(
            NotificationLog.notification_type,
            NotificationLog.status
        ).all()

        # Format statistics
        result = {}
        for notification_type, status, count in stats:
            if notification_type not in result:
                result[notification_type] = {}
            result[notification_type][status] = count

        return result
