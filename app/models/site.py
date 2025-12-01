"""
Site Model - Geographical location and site information
"""
from app import db
from datetime import datetime

class Site(db.Model):
    """Site/Location model for water sampling"""

    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(200), nullable=False)
    site_code = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Location details
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.Text)
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='India')
    postal_code = db.Column(db.String(20))

    # Environment classification
    environment_type = db.Column(db.String(50))  # urban, rural, marshland, river, ocean, industrial
    is_coastal = db.Column(db.Boolean, default=False)

    # Site characteristics
    population_density = db.Column(db.String(20))  # low, medium, high
    industrial_nearby = db.Column(db.Boolean, default=False)
    agricultural_nearby = db.Column(db.Boolean, default=False)

    # Metadata
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    samples = db.relationship('WaterSample', backref='site', lazy='dynamic')

    def __repr__(self):
        return f'<Site {self.site_code}: {self.site_name}>'

    def to_dict(self):
        """Convert site to dictionary"""
        return {
            'id': self.id,
            'site_name': self.site_name,
            'site_code': self.site_code,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'district': self.district,
            'state': self.state,
            'environment_type': self.environment_type,
            'is_coastal': self.is_coastal
        }
