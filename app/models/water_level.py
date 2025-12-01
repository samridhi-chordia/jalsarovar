"""
Water Level Model - Climate monitoring and drought/flood tracking
"""
from app import db
from datetime import datetime


class WaterLevel(db.Model):
    """Water level measurements for climate monitoring"""

    __tablename__ = 'water_levels'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Measurement Information
    measurement_date = db.Column(db.Date, nullable=False)
    measurement_time = db.Column(db.Time, nullable=False)
    measured_by = db.Column(db.String(100))  # User or 'Robot-{id}'
    measurement_method = db.Column(db.String(50))  # 'ultrasonic', 'pressure', 'manual'

    # Water Level Measurements
    water_level_meters = db.Column(db.Float, nullable=False)  # Level from bottom (ultrasonic)
    water_depth_meters = db.Column(db.Float)  # Total depth (pressure sensor, if available)
    baseline_height_meters = db.Column(db.Float)  # Sensor height above bottom
    distance_to_surface_meters = db.Column(db.Float)  # Raw ultrasonic reading

    # Temperature (from pressure sensor or separate)
    water_temperature_celsius = db.Column(db.Float)

    # Seasonal Status
    historical_avg_meters = db.Column(db.Float)  # Historical average for this month
    seasonal_status = db.Column(db.String(20))  # 'normal', 'low', 'very_low', 'high', 'flood'
    deviation_percent = db.Column(db.Float)  # % deviation from historical average

    # Sensor Quality Metrics
    measurement_uncertainty = db.Column(db.Float)  # Standard deviation of multiple readings
    num_samples_averaged = db.Column(db.Integer, default=5)
    sensor_health_status = db.Column(db.String(20), default='healthy')  # 'healthy', 'warning', 'failed'

    # Environmental Context
    weather_condition = db.Column(db.String(50))  # 'clear', 'rain', 'storm', etc.
    rainfall_mm_last_24h = db.Column(db.Float)  # Recent rainfall (if available)
    evaporation_mm_last_24h = db.Column(db.Float)  # Estimated evaporation

    # Alert Flags
    drought_alert = db.Column(db.Boolean, default=False)  # True if below drought threshold
    flood_alert = db.Column(db.Boolean, default=False)  # True if above flood threshold
    rapid_change_alert = db.Column(db.Boolean, default=False)  # True if >20% change in 24h

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    sample = db.relationship('WaterSample', backref='water_levels', lazy=True)
    site = db.relationship('Site', backref='water_levels', lazy=True)

    def __repr__(self):
        return f'<WaterLevel {self.id}: {self.water_level_meters}m on {self.measurement_date}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'site_id': self.site_id,
            'measurement_date': self.measurement_date.isoformat() if self.measurement_date else None,
            'measurement_time': self.measurement_time.isoformat() if self.measurement_time else None,
            'measured_by': self.measured_by,
            'measurement_method': self.measurement_method,
            'water_level_meters': self.water_level_meters,
            'water_depth_meters': self.water_depth_meters,
            'water_temperature_celsius': self.water_temperature_celsius,
            'seasonal_status': self.seasonal_status,
            'deviation_percent': self.deviation_percent,
            'drought_alert': self.drought_alert,
            'flood_alert': self.flood_alert,
            'rapid_change_alert': self.rapid_change_alert,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def calculate_seasonal_status(current_level: float, historical_avg: float) -> tuple:
        """
        Calculate seasonal status and deviation

        Args:
            current_level: Current water level (meters)
            historical_avg: Historical average for this month (meters)

        Returns:
            (status, deviation_percent) tuple
        """
        if historical_avg == 0:
            return ('unknown', 0.0)

        deviation = ((current_level - historical_avg) / historical_avg) * 100

        if current_level < historical_avg * 0.5:
            status = 'very_low'
        elif current_level < historical_avg * 0.8:
            status = 'low'
        elif current_level > historical_avg * 1.5:
            status = 'flood'
        elif current_level > historical_avg * 1.2:
            status = 'high'
        else:
            status = 'normal'

        return (status, round(deviation, 2))

    def set_alerts(self, drought_threshold: float = 0.5, flood_threshold: float = 1.5):
        """
        Set alert flags based on thresholds

        Args:
            drought_threshold: Fraction of historical avg to trigger drought (default 0.5)
            flood_threshold: Fraction of historical avg to trigger flood (default 1.5)
        """
        if self.historical_avg_meters:
            ratio = self.water_level_meters / self.historical_avg_meters

            self.drought_alert = ratio < drought_threshold
            self.flood_alert = ratio > flood_threshold


class WaterLevelTrend(db.Model):
    """Time series trends for water level analysis"""

    __tablename__ = 'water_level_trends'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Time Period
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12

    # Aggregated Statistics
    avg_level_meters = db.Column(db.Float)
    min_level_meters = db.Column(db.Float)
    max_level_meters = db.Column(db.Float)
    std_dev_meters = db.Column(db.Float)

    # Trend Analysis
    num_measurements = db.Column(db.Integer)
    trend_direction = db.Column(db.String(20))  # 'increasing', 'decreasing', 'stable'
    trend_slope = db.Column(db.Float)  # Linear regression slope (meters/day)
    trend_r_squared = db.Column(db.Float)  # Goodness of fit

    # Climate Indicators
    drought_days = db.Column(db.Integer)  # Days below drought threshold
    flood_days = db.Column(db.Integer)  # Days above flood threshold
    normal_days = db.Column(db.Integer)  # Days in normal range

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = db.relationship('Site', backref='water_level_trends', lazy=True)

    def __repr__(self):
        return f'<WaterLevelTrend {self.site_id}: {self.year}-{self.month:02d}>'

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'year': self.year,
            'month': self.month,
            'avg_level_meters': self.avg_level_meters,
            'min_level_meters': self.min_level_meters,
            'max_level_meters': self.max_level_meters,
            'trend_direction': self.trend_direction,
            'drought_days': self.drought_days,
            'flood_days': self.flood_days,
            'normal_days': self.normal_days,
        }
