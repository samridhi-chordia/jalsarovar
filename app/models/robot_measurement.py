"""
Robot Measurement Model - Autonomous robot data collection
"""
from app import db
from datetime import datetime


class RobotMeasurement(db.Model):
    """Measurements collected by autonomous water quality robots"""

    __tablename__ = 'robot_measurements'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Robot Information
    robot_id = db.Column(db.String(50), nullable=False)  # Unique robot identifier
    robot_model = db.Column(db.String(100))  # 'LEGOLAS-WFLOW-v1', etc.
    firmware_version = db.Column(db.String(20))

    # Measurement Session
    session_id = db.Column(db.String(100))  # Unique session identifier
    measurement_date = db.Column(db.Date, nullable=False)
    measurement_time = db.Column(db.Time, nullable=False)
    session_duration_seconds = db.Column(db.Integer)

    # Location
    gps_latitude = db.Column(db.Float)
    gps_longitude = db.Column(db.Float)
    gps_altitude_meters = db.Column(db.Float)
    gps_accuracy_meters = db.Column(db.Float)
    location_verified = db.Column(db.Boolean, default=False)  # GPS matches expected site location

    # Real-time Sensor Measurements (from sensor_controller.py)
    ph_value = db.Column(db.Float)
    temperature_celsius = db.Column(db.Float)
    tds_ppm = db.Column(db.Float)
    turbidity_ntu = db.Column(db.Float)
    conductivity_us_cm = db.Column(db.Float)
    dissolved_oxygen_mg_l = db.Column(db.Float)

    # Sensor Quality Metrics
    ph_uncertainty = db.Column(db.Float)  # Standard deviation from averaging
    temperature_uncertainty = db.Column(db.Float)
    tds_uncertainty = db.Column(db.Float)
    turbidity_uncertainty = db.Column(db.Float)
    conductivity_uncertainty = db.Column(db.Float)
    do_uncertainty = db.Column(db.Float)

    num_sensor_samples = db.Column(db.Integer, default=10)  # Number of readings averaged

    # Water Level (from water_level_monitor.py)
    water_level_meters = db.Column(db.Float)
    water_depth_meters = db.Column(db.Float)
    water_level_uncertainty = db.Column(db.Float)

    # Visual Observations (from camera_controller.py)
    water_surface_photo_id = db.Column(db.Integer, db.ForeignKey('visual_observations.id'))
    test_strip_photo_id = db.Column(db.Integer, db.ForeignKey('visual_observations.id'))
    documentation_photo_id = db.Column(db.Integer, db.ForeignKey('visual_observations.id'))

    # Test Strip Results (camera-assisted)
    strip_ph_value = db.Column(db.Float)
    strip_chlorine_mg_l = db.Column(db.Float)
    strip_nitrate_mg_l = db.Column(db.Float)
    strip_nitrite_mg_l = db.Column(db.Float)
    strip_hardness_mg_l = db.Column(db.Float)

    # Sample Collection (if robot has sampling capability)
    sample_collected = db.Column(db.Boolean, default=False)
    sample_volume_ml = db.Column(db.Float)
    sample_stored_in_carousel = db.Column(db.Boolean, default=False)
    carousel_position = db.Column(db.Integer)  # 1-12 for 12-port carousel

    # Robot Health
    battery_voltage = db.Column(db.Float)
    battery_percent = db.Column(db.Float)
    solar_charging = db.Column(db.Boolean)
    sensor_health_status = db.Column(db.String(20), default='healthy')  # 'healthy', 'warning', 'degraded'
    sensor_health_details = db.Column(db.JSON)  # {'ph': 'healthy', 'turbidity': 'warning', ...}

    # Data Upload
    upload_method = db.Column(db.String(20))  # '4G', 'WiFi', 'offline'
    upload_timestamp = db.Column(db.DateTime)
    upload_status = db.Column(db.String(20), default='pending')  # 'pending', 'uploaded', 'failed'
    upload_retry_count = db.Column(db.Integer, default=0)

    # Bayesian Optimization Context (WFLOW-OPT)
    selected_by_optimizer = db.Column(db.Boolean, default=False)
    optimization_score = db.Column(db.Float)  # Acquisition function score
    predicted_contamination_risk = db.Column(db.Float)  # GP model prediction
    prediction_uncertainty = db.Column(db.Float)  # GP uncertainty

    # Quality Control
    qc_status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    qc_flags = db.Column(db.JSON)  # List of QC issues detected
    qc_reviewed_by = db.Column(db.String(100))
    qc_reviewed_at = db.Column(db.DateTime)

    # Metadata
    notes = db.Column(db.Text)
    error_log = db.Column(db.Text)  # Robot errors during measurement
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sample = db.relationship('WaterSample', backref='robot_measurements', lazy=True)
    site = db.relationship('Site', backref='robot_measurements', lazy=True)
    water_surface_photo = db.relationship('VisualObservation', foreign_keys=[water_surface_photo_id], backref='robot_water_surface', lazy=True)
    test_strip_photo = db.relationship('VisualObservation', foreign_keys=[test_strip_photo_id], backref='robot_test_strip', lazy=True)
    documentation_photo = db.relationship('VisualObservation', foreign_keys=[documentation_photo_id], backref='robot_documentation', lazy=True)

    def __repr__(self):
        return f'<RobotMeasurement {self.id}: Robot {self.robot_id} at Site {self.site_id}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'robot_id': self.robot_id,
            'session_id': self.session_id,
            'site_id': self.site_id,
            'measurement_date': self.measurement_date.isoformat() if self.measurement_date else None,
            'measurement_time': self.measurement_time.isoformat() if self.measurement_time else None,
            'gps_latitude': self.gps_latitude,
            'gps_longitude': self.gps_longitude,
            'ph_value': self.ph_value,
            'temperature_celsius': self.temperature_celsius,
            'tds_ppm': self.tds_ppm,
            'turbidity_ntu': self.turbidity_ntu,
            'conductivity_us_cm': self.conductivity_us_cm,
            'dissolved_oxygen_mg_l': self.dissolved_oxygen_mg_l,
            'water_level_meters': self.water_level_meters,
            'water_depth_meters': self.water_depth_meters,
            'sample_collected': self.sample_collected,
            'battery_percent': self.battery_percent,
            'upload_status': self.upload_status,
            'selected_by_optimizer': self.selected_by_optimizer,
            'optimization_score': self.optimization_score,
            'predicted_contamination_risk': self.predicted_contamination_risk,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def get_all_measurements(self):
        """Get all parameter measurements as dictionary"""
        return {
            'ph_value': self.ph_value,
            'temperature_celsius': self.temperature_celsius,
            'tds_ppm': self.tds_ppm,
            'turbidity_ntu': self.turbidity_ntu,
            'conductivity_us_cm': self.conductivity_us_cm,
            'dissolved_oxygen_mg_l': self.dissolved_oxygen_mg_l,
            'water_level_meters': self.water_level_meters,
            'strip_ph_value': self.strip_ph_value,
            'strip_chlorine_mg_l': self.strip_chlorine_mg_l,
            'strip_nitrate_mg_l': self.strip_nitrate_mg_l,
        }

    def calculate_completeness(self):
        """
        Calculate measurement completeness (% of parameters measured)

        Returns:
            Completeness percentage (0-100)
        """
        total_params = 10  # Total possible parameters
        measured_params = 0

        if self.ph_value is not None:
            measured_params += 1
        if self.temperature_celsius is not None:
            measured_params += 1
        if self.tds_ppm is not None:
            measured_params += 1
        if self.turbidity_ntu is not None:
            measured_params += 1
        if self.conductivity_us_cm is not None:
            measured_params += 1
        if self.dissolved_oxygen_mg_l is not None:
            measured_params += 1
        if self.water_level_meters is not None:
            measured_params += 1
        if self.water_surface_photo_id is not None:
            measured_params += 1
        if self.sample_collected:
            measured_params += 1
        if self.strip_ph_value is not None:
            measured_params += 1

        return round((measured_params / total_params) * 100, 1)

    def check_sensor_health(self):
        """
        Check sensor health based on uncertainty metrics

        Returns:
            (status, issues) tuple
        """
        issues = []

        # Check uncertainties (flag if > 10% of value)
        if self.ph_value and self.ph_uncertainty:
            if self.ph_uncertainty / self.ph_value > 0.1:
                issues.append('pH sensor: high uncertainty')

        if self.tds_ppm and self.tds_uncertainty:
            if self.tds_uncertainty / self.tds_ppm > 0.1:
                issues.append('TDS sensor: high uncertainty')

        if self.turbidity_ntu and self.turbidity_uncertainty:
            if self.turbidity_uncertainty / max(self.turbidity_ntu, 1) > 0.2:
                issues.append('Turbidity sensor: high uncertainty')

        # Check battery
        if self.battery_percent and self.battery_percent < 20:
            issues.append('Low battery (<20%)')

        # Determine overall status
        if len(issues) == 0:
            status = 'healthy'
        elif len(issues) <= 2:
            status = 'warning'
        else:
            status = 'degraded'

        return (status, issues)


class RobotFleet(db.Model):
    """Fleet management for water quality robots"""

    __tablename__ = 'robot_fleet'

    id = db.Column(db.Integer, primary_key=True)
    robot_id = db.Column(db.String(50), unique=True, nullable=False)
    robot_name = db.Column(db.String(100))

    # Robot Configuration
    robot_model = db.Column(db.String(100))
    firmware_version = db.Column(db.String(20))
    deployment_date = db.Column(db.Date)
    assigned_region = db.Column(db.String(100))  # State, district, etc.

    # Hardware Configuration
    has_ultrasonic_sensor = db.Column(db.Boolean, default=True)
    has_pressure_sensor = db.Column(db.Boolean, default=False)
    has_camera = db.Column(db.Boolean, default=True)
    has_sample_collector = db.Column(db.Boolean, default=False)
    has_gps = db.Column(db.Boolean, default=True)
    has_4g_modem = db.Column(db.Boolean, default=True)

    # Status
    operational_status = db.Column(db.String(20), default='active')  # 'active', 'maintenance', 'retired'
    last_measurement_date = db.Column(db.DateTime)
    last_upload_date = db.Column(db.DateTime)
    total_measurements = db.Column(db.Integer, default=0)
    total_samples_collected = db.Column(db.Integer, default=0)

    # Maintenance
    last_maintenance_date = db.Column(db.Date)
    next_maintenance_due = db.Column(db.Date)
    calibration_due_date = db.Column(db.Date)
    maintenance_notes = db.Column(db.Text)

    # Performance Metrics
    avg_measurement_completeness = db.Column(db.Float)
    avg_upload_success_rate = db.Column(db.Float)
    avg_battery_health = db.Column(db.Float)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<RobotFleet {self.robot_id}: {self.robot_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'robot_id': self.robot_id,
            'robot_name': self.robot_name,
            'robot_model': self.robot_model,
            'firmware_version': self.firmware_version,
            'operational_status': self.operational_status,
            'assigned_region': self.assigned_region,
            'total_measurements': self.total_measurements,
            'total_samples_collected': self.total_samples_collected,
            'last_measurement_date': self.last_measurement_date.isoformat() if self.last_measurement_date else None,
            'calibration_due_date': self.calibration_due_date.isoformat() if self.calibration_due_date else None,
        }
