"""
Visitor tracking models for analytics
"""
from datetime import datetime
from app import db


class VisitorStats(db.Model):
    """Track visitor statistics"""
    __tablename__ = 'visitor_stats'

    id = db.Column(db.Integer, primary_key=True)
    total_visits = db.Column(db.Integer, default=0, nullable=False)
    unique_visitors = db.Column(db.Integer, default=0, nullable=False)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_stats(cls):
        """Get current visitor statistics"""
        stats = cls.query.first()
        if not stats:
            stats = cls(total_visits=0, unique_visitors=0)
            db.session.add(stats)
            db.session.commit()
        return stats

    @classmethod
    def increment_visit(cls):
        """Increment total visit count"""
        stats = cls.get_stats()
        stats.total_visits += 1
        db.session.commit()
        return stats.total_visits

    @classmethod
    def increment_unique(cls):
        """Increment unique visitor count"""
        stats = cls.get_stats()
        stats.unique_visitors += 1
        db.session.commit()
        return stats.unique_visitors

    def __repr__(self):
        return f'<VisitorStats total={self.total_visits} unique={self.unique_visitors}>'


class Visit(db.Model):
    """Track individual visits"""
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), index=True)  # IPv6 support
    user_agent = db.Column(db.String(500))
    referer = db.Column(db.String(500))
    path = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100), index=True)

    def __repr__(self):
        return f'<Visit {self.ip_address} at {self.timestamp}>'
