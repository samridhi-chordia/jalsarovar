"""Site model for water monitoring locations"""
from datetime import datetime
from app import db


class Site(db.Model):
    """Water monitoring site - Amrit Sarovar water bodies"""
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    site_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    site_name = db.Column(db.String(200), nullable=False)

    # Location
    country = db.Column(db.String(100), nullable=False, default='India', index=True)
    state = db.Column(db.String(100), nullable=False, index=True)
    district = db.Column(db.String(100), nullable=False)
    block = db.Column(db.String(100))
    village = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Site characteristics
    site_type = db.Column(db.String(50), nullable=False)  # pond, lake, tank, reservoir, stepwell
    site_category = db.Column(db.String(20), default='public')  # 'public' or 'residential'
    water_source = db.Column(db.String(50))  # groundwater, surface, mixed
    surface_area_hectares = db.Column(db.Float)
    storage_capacity_mcm = db.Column(db.Float)  # Million Cubic Meters
    catchment_area_sqkm = db.Column(db.Float)

    # Environmental factors
    is_coastal = db.Column(db.Boolean, default=False)
    is_industrial_nearby = db.Column(db.Boolean, default=False)
    is_agricultural_nearby = db.Column(db.Boolean, default=False)
    is_urban = db.Column(db.Boolean, default=False)
    population_served = db.Column(db.Integer)

    # Amrit Sarovar specific
    amrit_sarovar_id = db.Column(db.String(50), index=True)
    rejuvenation_status = db.Column(db.String(50))  # planned, in_progress, completed
    rejuvenation_date = db.Column(db.Date)

    # Risk assessment (from ML model)
    current_risk_level = db.Column(db.String(20))  # critical, high, medium, low
    risk_score = db.Column(db.Float)  # 0-100
    last_risk_assessment = db.Column(db.DateTime)

    # Testing schedule
    testing_frequency = db.Column(db.String(20), default='monthly')  # weekly, bi-weekly, monthly
    last_tested = db.Column(db.DateTime)
    next_scheduled_test = db.Column(db.DateTime)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    samples = db.relationship('WaterSample', backref='site', lazy='dynamic')
    iot_sensors = db.relationship('IoTSensor', backref='site', lazy='dynamic')
    risk_predictions = db.relationship('SiteRiskPrediction', backref='site', lazy='dynamic')
    cost_optimizations = db.relationship('CostOptimizationResult', backref='site', lazy='dynamic')

    def get_latest_sample(self):
        """Get most recent water sample"""
        return self.samples.order_by(WaterSample.collection_date.desc()).first()

    def get_contamination_rate(self, days=30):
        """Calculate contamination rate over given days"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        total = self.samples.filter(WaterSample.collection_date >= cutoff).count()
        if total == 0:
            return 0
        contaminated = self.samples.join(Analysis).filter(
            WaterSample.collection_date >= cutoff,
            Analysis.is_contaminated == True
        ).count()
        return (contaminated / total) * 100

    def __repr__(self):
        return f'<Site {self.site_code}: {self.site_name}>'


# Import at bottom to avoid circular imports
from app.models.water_sample import WaterSample
from app.models.analysis import Analysis
