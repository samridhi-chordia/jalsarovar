"""Water Sample model"""
from datetime import datetime
from app import db


class WaterSample(db.Model):
    """Water sample collection record"""
    __tablename__ = 'water_samples'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)

    # Collection details
    collection_date = db.Column(db.Date, nullable=False, index=True)
    collection_time = db.Column(db.Time)
    collected_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Sample source
    source_point = db.Column(db.String(100))  # inlet, center, outlet, tap, borewell
    depth_meters = db.Column(db.Float)
    water_level_meters = db.Column(db.Float)

    # Field observations
    weather_condition = db.Column(db.String(50))  # sunny, cloudy, rainy, stormy
    rained_recently = db.Column(db.Boolean, default=False)
    rainfall_mm_24h = db.Column(db.Float)
    air_temperature_celsius = db.Column(db.Float)

    # Visual observations
    apparent_color = db.Column(db.String(50))  # clear, yellow, brown, green, milky
    odor = db.Column(db.String(50))  # none, earthy, chlorine, sewage, chemical
    visible_algae = db.Column(db.Boolean, default=False)
    floating_matter = db.Column(db.Boolean, default=False)
    oil_sheen = db.Column(db.Boolean, default=False)

    # Sample handling
    preservation_method = db.Column(db.String(50))  # ice, chemical, none
    transport_time_hours = db.Column(db.Float)
    lab_received_date = db.Column(db.DateTime)

    # Status
    status = db.Column(db.String(20), default='collected')  # collected, in_transit, in_lab, tested, analyzed
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    test_results = db.relationship('TestResult', backref='sample', lazy='dynamic')
    analyses = db.relationship('Analysis', backref='sample', lazy='dynamic')
    interventions = db.relationship('Intervention', backref='sample', lazy='dynamic')

    def get_latest_test(self):
        """Get most recent test result"""
        return self.test_results.order_by(TestResult.tested_date.desc()).first()

    def get_latest_analysis(self):
        """Get most recent analysis"""
        return self.analyses.order_by(Analysis.analysis_date.desc()).first()

    def __repr__(self):
        return f'<WaterSample {self.sample_id}>'


# Import at bottom
from app.models.test_result import TestResult
from app.models.analysis import Analysis
