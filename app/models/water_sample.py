"""
Water Sample Model - Core sample tracking
"""
from app import db
from datetime import datetime
import hashlib
import time

class WaterSample(db.Model):
    """Water sample collection model"""

    __tablename__ = 'water_samples'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Site and Location
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    sub_site_details = db.Column(db.String(200))  # Specific location within site
    exact_latitude = db.Column(db.Float)
    exact_longitude = db.Column(db.Float)

    # Collection Details
    collection_date = db.Column(db.Date, nullable=False, index=True)
    collection_time = db.Column(db.Time, nullable=False)
    collected_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Water Source Characteristics
    source_type = db.Column(db.String(50))  # groundwater, surface, municipal, well, borewell
    source_depth_meters = db.Column(db.Float)  # For groundwater
    storage_type = db.Column(db.String(50))  # tank, running, direct_source, reservoir
    storage_material = db.Column(db.String(50))  # concrete, plastic, metal, none

    # Discharge/Collection Point
    discharge_type = db.Column(db.String(50))  # tap, hand_pump, running, direct
    discharge_material = db.Column(db.String(50))  # metal, plastic, pvc

    # Source Information
    water_source_root = db.Column(db.String(100))  # municipality, private_well, river, lake
    is_recycled = db.Column(db.Boolean, default=False)
    source_age_years = db.Column(db.Integer)

    # Pipe/Infrastructure
    pipe_material = db.Column(db.String(20))  # GI, PVC, HDPE, copper, none
    pipe_age_years = db.Column(db.Integer)
    distance_from_source_meters = db.Column(db.Float)

    # Environmental Conditions
    weather_condition = db.Column(db.String(50))  # clear, rainy, cloudy
    rained_recently = db.Column(db.Boolean, default=False)
    days_since_rain = db.Column(db.Integer)
    ambient_temperature_celsius = db.Column(db.Float)

    # Physical Observations
    water_appearance = db.Column(db.String(50))  # clear, cloudy, colored
    odor_present = db.Column(db.Boolean, default=False)
    odor_description = db.Column(db.String(100))
    visible_particles = db.Column(db.Boolean, default=False)

    # Sample Status
    status = db.Column(db.String(20), default='collected')  # collected, tested, analyzed, archived
    priority = db.Column(db.String(20), default='normal')  # urgent, high, normal, low

    # Notes
    collection_notes = db.Column(db.Text)
    special_observations = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    test_results = db.relationship('TestResult', backref='sample', lazy='dynamic', cascade='all, delete-orphan')
    analyses = db.relationship('Analysis', backref='sample', lazy='dynamic', cascade='all, delete-orphan')

    @staticmethod
    def generate_sample_id(site_code, date):
        """Generate unique sample ID"""
        timestamp = int(time.time() * 1000)
        raw = f"{site_code}{date.strftime('%Y%m%d')}{timestamp}"
        hash_val = hashlib.md5(raw.encode()).hexdigest()[:8].upper()
        return f"WS-{site_code}-{date.strftime('%Y%m%d')}-{hash_val}"

    @property
    def latest_analysis(self):
        """Get the most recent analysis for this sample"""
        from app.models.analysis import Analysis
        return self.analyses.order_by(Analysis.analysis_date.desc()).first()

    def __repr__(self):
        return f'<WaterSample {self.sample_id}>'

    def to_dict(self):
        """Convert sample to dictionary"""
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'site_name': self.site.site_name if self.site else None,
            'collection_date': self.collection_date.isoformat() if self.collection_date else None,
            'collection_time': self.collection_time.isoformat() if self.collection_time else None,
            'source_type': self.source_type,
            'status': self.status,
            'priority': self.priority
        }
