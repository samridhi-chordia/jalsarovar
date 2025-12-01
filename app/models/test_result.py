"""
Test Result Model - Laboratory test measurements
"""
from app import db
from datetime import datetime

class TestResult(db.Model):
    """Test results for water quality parameters"""

    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=False)

    # Test Information
    test_date = db.Column(db.Date, nullable=False)
    test_time = db.Column(db.Time, nullable=False)
    tested_by = db.Column(db.String(100))
    test_batch_id = db.Column(db.String(50))

    # Physical Parameters
    turbidity_ntu = db.Column(db.Float)  # Nephelometric Turbidity Units
    temperature_celsius = db.Column(db.Float)
    color_pcu = db.Column(db.Float)  # Platinum-Cobalt Units
    odor_intensity = db.Column(db.Integer)  # 0-5 scale

    # Chemical Parameters
    ph_value = db.Column(db.Float)
    tds_ppm = db.Column(db.Float)  # Total Dissolved Solids (parts per million)
    salinity_ppm = db.Column(db.Float)
    conductivity_us_cm = db.Column(db.Float)  # microsiemens per cm

    # Chlorine
    free_chlorine_mg_l = db.Column(db.Float)  # mg/L
    total_chlorine_mg_l = db.Column(db.Float)
    chloride_mg_l = db.Column(db.Float)

    # Metals
    iron_mg_l = db.Column(db.Float)
    manganese_mg_l = db.Column(db.Float)
    copper_mg_l = db.Column(db.Float)
    lead_mg_l = db.Column(db.Float)
    arsenic_mg_l = db.Column(db.Float)

    # Hardness
    total_hardness_mg_l = db.Column(db.Float)  # as CaCO3
    calcium_hardness_mg_l = db.Column(db.Float)
    magnesium_hardness_mg_l = db.Column(db.Float)

    # Nutrients
    nitrate_mg_l = db.Column(db.Float)
    nitrite_mg_l = db.Column(db.Float)
    ammonia_mg_l = db.Column(db.Float)
    phosphate_mg_l = db.Column(db.Float)

    # Biological
    coliform_status = db.Column(db.String(20))  # positive, negative, pending
    e_coli_status = db.Column(db.String(20))
    coliform_count_cfu_100ml = db.Column(db.Float)  # Colony Forming Units per 100ml

    # Dissolved Oxygen
    dissolved_oxygen_mg_l = db.Column(db.Float)
    bod_mg_l = db.Column(db.Float)  # Biochemical Oxygen Demand
    cod_mg_l = db.Column(db.Float)  # Chemical Oxygen Demand

    # Other Parameters
    alkalinity_mg_l = db.Column(db.Float)  # as CaCO3
    sulfate_mg_l = db.Column(db.Float)
    fluoride_mg_l = db.Column(db.Float)

    # Quality Control
    qc_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    qc_notes = db.Column(db.Text)
    qc_approved_by = db.Column(db.String(100))
    qc_approved_at = db.Column(db.DateTime)

    # Test Metadata
    test_method = db.Column(db.String(100))  # Standard method used
    lab_equipment_id = db.Column(db.String(50))
    test_duration_minutes = db.Column(db.Integer)
    retest_required = db.Column(db.Boolean, default=False)
    retest_reason = db.Column(db.Text)

    # Notes
    test_notes = db.Column(db.Text)
    anomalies_observed = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TestResult sample={self.sample.sample_id} date={self.test_date}>'

    def to_dict(self):
        """Convert test result to dictionary"""
        return {
            'id': self.id,
            'sample_id': self.sample.sample_id if self.sample else None,
            'test_date': self.test_date.isoformat() if self.test_date else None,
            'turbidity_ntu': self.turbidity_ntu,
            'ph_value': self.ph_value,
            'tds_ppm': self.tds_ppm,
            'free_chlorine_mg_l': self.free_chlorine_mg_l,
            'iron_mg_l': self.iron_mg_l,
            'coliform_status': self.coliform_status,
            'qc_status': self.qc_status
        }

    def get_parameters_dict(self):
        """Get all test parameters as dictionary for ML analysis"""
        return {
            'turbidity_ntu': self.turbidity_ntu,
            'ph_value': self.ph_value,
            'tds_ppm': self.tds_ppm,
            'salinity_ppm': self.salinity_ppm,
            'free_chlorine_mg_l': self.free_chlorine_mg_l,
            'iron_mg_l': self.iron_mg_l,
            'coliform_status': self.coliform_status,
            'chloride_mg_l': self.chloride_mg_l,
            'dissolved_oxygen_mg_l': self.dissolved_oxygen_mg_l,
            'nitrate_mg_l': self.nitrate_mg_l,
            'conductivity_us_cm': self.conductivity_us_cm
        }
