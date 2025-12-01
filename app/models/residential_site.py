"""
Residential Site Model - Homes and apartment water monitoring
Extends the Jal Sarovar system to residential use cases
"""
from app import db
from datetime import datetime


class ResidentialSite(db.Model):
    """Residential water monitoring locations"""

    __tablename__ = 'residential_sites'

    id = db.Column(db.Integer, primary_key=True)

    # Site Classification
    site_type = db.Column(db.String(50), nullable=False)  # 'individual_home', 'apartment_unit', 'apartment_building', 'commercial'
    installation_type = db.Column(db.String(50))  # 'tap_inline', 'tank_mounted', 'ro_system', 'borewell'

    # Location
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # For Apartments
    building_name = db.Column(db.String(200))
    flat_number = db.Column(db.String(20))
    floor_number = db.Column(db.Integer)
    total_flats_in_building = db.Column(db.Integer)
    is_community_monitor = db.Column(db.Boolean, default=False)  # True if this is building-wide sensor

    # Household Info
    household_size = db.Column(db.Integer)
    occupancy_type = db.Column(db.String(30))  # 'owner', 'tenant', 'commercial'

    # Water Infrastructure
    water_source = db.Column(db.String(50))  # 'municipal', 'borewell', 'tanker', 'mixed'
    municipal_connection_number = db.Column(db.String(50))
    has_ro_system = db.Column(db.Boolean, default=False)
    ro_brand = db.Column(db.String(50))
    ro_installation_date = db.Column(db.Date)
    has_water_softener = db.Column(db.Boolean, default=False)
    has_uv_filter = db.Column(db.Boolean, default=False)
    storage_tank_capacity_liters = db.Column(db.Integer)

    # Sensor Hardware
    device_id = db.Column(db.String(50), unique=True)  # Unique sensor device identifier
    device_model = db.Column(db.String(50))  # 'WFLOW-Home-Basic', 'WFLOW-Home-Premium'
    installation_date = db.Column(db.Date)
    last_calibration_date = db.Column(db.Date)
    next_calibration_due = db.Column(db.Date)

    # Subscription & Billing
    subscription_tier = db.Column(db.String(30), default='free')  # 'free', 'premium', 'community'
    subscription_start_date = db.Column(db.Date)
    subscription_end_date = db.Column(db.Date)
    subscription_status = db.Column(db.String(20), default='active')  # 'active', 'expired', 'cancelled'
    monthly_fee = db.Column(db.Float, default=0.0)

    # Privacy Settings
    data_sharing_consent = db.Column(db.Boolean, default=False)  # Allow anonymous data for public health research
    public_dashboard_visible = db.Column(db.Boolean, default=False)  # Show on public map

    # Owner/Manager
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    contact_phone = db.Column(db.String(15))
    contact_email = db.Column(db.String(120))

    # Alert Preferences
    alert_phone_enabled = db.Column(db.Boolean, default=True)
    alert_email_enabled = db.Column(db.Boolean, default=True)
    alert_sms_enabled = db.Column(db.Boolean, default=False)
    alert_whatsapp_enabled = db.Column(db.Boolean, default=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    owner = db.relationship('User', backref='residential_sites', lazy=True)
    measurements = db.relationship('ResidentialMeasurement', backref='site', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('ResidentialAlert', backref='site', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ResidentialSite {self.id}: {self.address_line1}, {self.city}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'site_type': self.site_type,
            'installation_type': self.installation_type,
            'address': f"{self.address_line1}, {self.city}, {self.state} {self.pincode}",
            'building_name': self.building_name,
            'flat_number': self.flat_number,
            'water_source': self.water_source,
            'has_ro_system': self.has_ro_system,
            'device_id': self.device_id,
            'subscription_tier': self.subscription_tier,
            'subscription_status': self.subscription_status,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ResidentialMeasurement(db.Model):
    """Continuous water quality measurements for residential sites"""

    __tablename__ = 'residential_measurements'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('residential_sites.id'), nullable=False)

    # Measurement Info
    measurement_datetime = db.Column(db.DateTime, nullable=False, index=True)
    measurement_type = db.Column(db.String(30))  # 'continuous', 'scheduled', 'on_demand'

    # Water Quality Parameters
    ph_value = db.Column(db.Float)
    tds_ppm = db.Column(db.Float)
    temperature_celsius = db.Column(db.Float)
    turbidity_ntu = db.Column(db.Float)
    conductivity_us_cm = db.Column(db.Float)
    free_chlorine_mg_l = db.Column(db.Float)
    orp_mv = db.Column(db.Float)  # Oxidation-Reduction Potential (millivolts)

    # Flow & Consumption (if flow sensor present)
    flow_rate_lpm = db.Column(db.Float)  # Liters per minute
    cumulative_flow_liters = db.Column(db.Float)  # Total flow since installation
    daily_consumption_liters = db.Column(db.Float)

    # RO System Metrics (if applicable)
    ro_inlet_tds = db.Column(db.Float)  # TDS before RO
    ro_outlet_tds = db.Column(db.Float)  # TDS after RO
    ro_rejection_rate_percent = db.Column(db.Float)  # (inlet - outlet) / inlet * 100
    ro_membrane_health_percent = db.Column(db.Float)  # 0-100 (estimated from rejection rate decline)

    # Quality Indicators
    water_quality_index = db.Column(db.Float)  # 0-100 (composite score)
    is_safe_to_drink = db.Column(db.Boolean)
    compliance_status = db.Column(db.String(30))  # 'compliant', 'warning', 'unsafe'

    # Anomaly Detection
    anomaly_detected = db.Column(db.Boolean, default=False)
    anomaly_type = db.Column(db.String(50))  # 'sudden_tds_spike', 'chlorine_drop', 'ph_shift', 'flow_anomaly'
    anomaly_severity = db.Column(db.String(20))  # 'low', 'medium', 'high', 'critical'

    # Device Health
    device_battery_percent = db.Column(db.Float)
    device_signal_strength = db.Column(db.Integer)  # WiFi RSSI
    sensor_health_status = db.Column(db.String(20))  # 'healthy', 'degraded', 'failed'

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploaded_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<ResidentialMeasurement {self.id}: Site {self.site_id} at {self.measurement_datetime}>'

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'measurement_datetime': self.measurement_datetime.isoformat() if self.measurement_datetime else None,
            'ph_value': self.ph_value,
            'tds_ppm': self.tds_ppm,
            'temperature_celsius': self.temperature_celsius,
            'turbidity_ntu': self.turbidity_ntu,
            'free_chlorine_mg_l': self.free_chlorine_mg_l,
            'water_quality_index': self.water_quality_index,
            'is_safe_to_drink': self.is_safe_to_drink,
            'compliance_status': self.compliance_status,
            'anomaly_detected': self.anomaly_detected,
            'ro_rejection_rate_percent': self.ro_rejection_rate_percent,
        }

    def calculate_water_quality_index(self):
        """
        Calculate composite water quality index (0-100)
        Based on WHO/BIS standards for drinking water
        """
        score = 100.0

        # pH penalty (ideal: 6.5-8.5)
        if self.ph_value:
            if self.ph_value < 6.5:
                score -= min(20, (6.5 - self.ph_value) * 10)
            elif self.ph_value > 8.5:
                score -= min(20, (self.ph_value - 8.5) * 10)

        # TDS penalty (ideal: <500 ppm for drinking)
        if self.tds_ppm:
            if self.tds_ppm > 500:
                score -= min(30, (self.tds_ppm - 500) / 20)

        # Turbidity penalty (ideal: <1 NTU)
        if self.turbidity_ntu:
            if self.turbidity_ntu > 1:
                score -= min(20, (self.turbidity_ntu - 1) * 5)

        # Chlorine penalty (ideal: 0.2-1.0 mg/L)
        if self.free_chlorine_mg_l:
            if self.free_chlorine_mg_l < 0.2:
                score -= 15  # Insufficient disinfection
            elif self.free_chlorine_mg_l > 1.0:
                score -= min(15, (self.free_chlorine_mg_l - 1.0) * 10)

        self.water_quality_index = max(0, round(score, 1))
        self.is_safe_to_drink = score >= 70

        if score >= 90:
            self.compliance_status = 'excellent'
        elif score >= 70:
            self.compliance_status = 'compliant'
        elif score >= 50:
            self.compliance_status = 'warning'
        else:
            self.compliance_status = 'unsafe'

        return self.water_quality_index


class ResidentialAlert(db.Model):
    """Water quality alerts for residential users"""

    __tablename__ = 'residential_alerts'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('residential_sites.id'), nullable=False)
    measurement_id = db.Column(db.Integer, db.ForeignKey('residential_measurements.id'))

    # Alert Details
    alert_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    alert_type = db.Column(db.String(50), nullable=False)  # 'high_tds', 'low_chlorine', 'ph_abnormal', 'contamination', 'ro_failure', 'leak_detected'
    alert_severity = db.Column(db.String(20), nullable=False)  # 'info', 'warning', 'critical'
    alert_title = db.Column(db.String(200), nullable=False)
    alert_message = db.Column(db.Text, nullable=False)

    # Parameters that triggered alert
    trigger_parameter = db.Column(db.String(50))
    trigger_value = db.Column(db.Float)
    threshold_value = db.Column(db.Float)

    # Recommendations
    recommended_action = db.Column(db.Text)
    estimated_cost = db.Column(db.Float)

    # Notification Status
    notification_sent_sms = db.Column(db.Boolean, default=False)
    notification_sent_email = db.Column(db.Boolean, default=False)
    notification_sent_push = db.Column(db.Boolean, default=False)
    notification_sent_whatsapp = db.Column(db.Boolean, default=False)

    # User Actions
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    measurement = db.relationship('ResidentialMeasurement', backref='alerts', lazy=True)
    acknowledged_by = db.relationship('User', backref='acknowledged_alerts', lazy=True)

    def __repr__(self):
        return f'<ResidentialAlert {self.id}: {self.alert_type} at Site {self.site_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'alert_datetime': self.alert_datetime.isoformat() if self.alert_datetime else None,
            'alert_type': self.alert_type,
            'alert_severity': self.alert_severity,
            'alert_title': self.alert_title,
            'alert_message': self.alert_message,
            'trigger_parameter': self.trigger_parameter,
            'trigger_value': self.trigger_value,
            'recommended_action': self.recommended_action,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
        }


class ResidentialSubscription(db.Model):
    """Subscription and billing for residential users"""

    __tablename__ = 'residential_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('residential_sites.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Subscription Details
    tier = db.Column(db.String(30), nullable=False)  # 'free', 'basic', 'premium', 'community'
    billing_cycle = db.Column(db.String(20))  # 'monthly', 'quarterly', 'yearly'
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='INR')

    # Dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    next_billing_date = db.Column(db.Date)

    # Status
    status = db.Column(db.String(20), default='active')  # 'active', 'paused', 'cancelled', 'expired'
    auto_renew = db.Column(db.Boolean, default=True)

    # Payment
    payment_method = db.Column(db.String(50))  # 'credit_card', 'upi', 'net_banking', 'razorpay'
    last_payment_date = db.Column(db.Date)
    last_payment_amount = db.Column(db.Float)
    last_payment_status = db.Column(db.String(20))  # 'success', 'failed', 'pending'

    # Features
    features_json = db.Column(db.JSON)  # Store tier-specific features
    # Example: {"max_alerts_per_month": 100, "historical_data_days": 365, "lab_tests_included": 2}

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = db.relationship('ResidentialSite', backref='subscriptions', lazy=True)
    user = db.relationship('User', backref='subscriptions', lazy=True)

    def __repr__(self):
        return f'<ResidentialSubscription {self.id}: {self.tier} for Site {self.site_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'tier': self.tier,
            'billing_cycle': self.billing_cycle,
            'amount': self.amount,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'auto_renew': self.auto_renew,
        }
