"""IoT Sensor models for real-time monitoring"""
from datetime import datetime
from app import db


class IoTSensor(db.Model):
    """IoT sensor devices installed at sites"""
    __tablename__ = 'iot_sensors'

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)

    # Sensor info
    sensor_type = db.Column(db.String(50))  # multi-parameter, single-parameter
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))

    # Parameters measured
    measures_ph = db.Column(db.Boolean, default=True)
    measures_tds = db.Column(db.Boolean, default=True)
    measures_turbidity = db.Column(db.Boolean, default=True)
    measures_chlorine = db.Column(db.Boolean, default=False)
    measures_temperature = db.Column(db.Boolean, default=True)
    measures_dissolved_oxygen = db.Column(db.Boolean, default=False)

    # Installation
    installation_date = db.Column(db.Date)
    installation_depth_meters = db.Column(db.Float)
    location_description = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Configuration
    reading_interval_minutes = db.Column(db.Integer, default=15)
    transmission_interval_minutes = db.Column(db.Integer, default=60)
    battery_type = db.Column(db.String(50))
    power_source = db.Column(db.String(50))  # solar, battery, grid

    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_reading_time = db.Column(db.DateTime)
    battery_level_percent = db.Column(db.Float)
    signal_strength = db.Column(db.Integer)  # 0-100

    # Calibration
    last_calibration_date = db.Column(db.Date)
    next_calibration_date = db.Column(db.Date)
    calibration_status = db.Column(db.String(20))  # valid, due, overdue

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    readings = db.relationship('SensorReading', backref='sensor', lazy='dynamic')
    alerts = db.relationship('SensorAlert', backref='sensor', lazy='dynamic')
    wqi_readings = db.relationship('WQIReading', backref='sensor', lazy='dynamic')
    anomalies = db.relationship('AnomalyDetection', backref='sensor', lazy='dynamic')

    def get_latest_reading(self):
        """Get most recent reading"""
        return self.readings.order_by(SensorReading.reading_timestamp.desc()).first()

    def is_online(self):
        """Check if sensor is online (reading in last hour)"""
        if not self.last_reading_time:
            return False
        from datetime import timedelta
        return (datetime.utcnow() - self.last_reading_time) < timedelta(hours=1)

    def __repr__(self):
        return f'<IoTSensor {self.sensor_id}>'


class SensorReading(db.Model):
    """Individual sensor readings"""
    __tablename__ = 'sensor_readings'

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('iot_sensors.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    reading_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Measurements
    ph = db.Column(db.Float)
    tds_ppm = db.Column(db.Float)
    turbidity_ntu = db.Column(db.Float)
    temperature_celsius = db.Column(db.Float)
    free_chlorine_mg_l = db.Column(db.Float)
    dissolved_oxygen_mg_l = db.Column(db.Float)
    conductivity_us_cm = db.Column(db.Float)

    # Quality flags
    is_valid = db.Column(db.Boolean, default=True)
    quality_flag = db.Column(db.String(20))  # good, suspect, invalid
    error_code = db.Column(db.String(50))

    # Sensor status at reading
    battery_level = db.Column(db.Float)
    signal_strength = db.Column(db.Integer)

    # Processing
    is_processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime)
    wqi_calculated = db.Column(db.Boolean, default=False)
    anomaly_checked = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<SensorReading {self.sensor_id} @ {self.reading_timestamp}>'


class SensorAlert(db.Model):
    """Alerts generated from sensor readings"""
    __tablename__ = 'sensor_alerts'

    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('iot_sensors.id'), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    reading_id = db.Column(db.Integer, db.ForeignKey('sensor_readings.id'))
    alert_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Alert details
    alert_type = db.Column(db.String(50), nullable=False)  # threshold_exceeded, anomaly, sensor_offline, low_battery
    severity = db.Column(db.String(20), nullable=False)  # critical, warning, info
    parameter = db.Column(db.String(50))  # Which parameter triggered alert
    threshold_value = db.Column(db.Float)
    observed_value = db.Column(db.Float)

    # Alert message
    title = db.Column(db.String(200))
    message = db.Column(db.Text)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)

    # Notifications
    email_sent = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    notification_recipients = db.Column(db.Text)  # JSON list

    def __repr__(self):
        return f'<SensorAlert {self.alert_type}: {self.severity}>'
