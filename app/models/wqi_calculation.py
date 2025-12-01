"""
WQI Calculation Model
Stores Water Quality Index calculations and results
"""
from app import db
from datetime import datetime
from sqlalchemy import desc


class WQICalculation(db.Model):
    """
    Water Quality Index calculation results

    Stores both input parameters and calculated WQI scores
    with penalty breakdowns for analysis
    """

    __tablename__ = 'wqi_calculations'

    id = db.Column(db.Integer, primary_key=True)

    # Link to water sample or sensor reading
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    residential_site_id = db.Column(db.Integer, db.ForeignKey('residential_sites.id'), nullable=True)
    device_id = db.Column(db.String(50), nullable=True, index=True)  # For IoT sensors

    # Input Parameters
    ph_value = db.Column(db.Float)
    tds_ppm = db.Column(db.Float)
    turbidity_ntu = db.Column(db.Float)
    free_chlorine = db.Column(db.Float)
    temperature_c = db.Column(db.Float)
    total_coliform = db.Column(db.Float)

    # WQI Results
    wqi_score = db.Column(db.Float, nullable=False, index=True)
    compliance_class = db.Column(db.String(20), nullable=False, index=True)  # excellent/compliant/warning/unsafe
    is_safe = db.Column(db.Boolean, nullable=False, index=True)

    # Penalty Breakdown
    ph_penalty = db.Column(db.Float, default=0.0)
    tds_penalty = db.Column(db.Float, default=0.0)
    turbidity_penalty = db.Column(db.Float, default=0.0)
    chlorine_penalty = db.Column(db.Float, default=0.0)
    temperature_penalty = db.Column(db.Float, default=0.0)
    coliform_penalty = db.Column(db.Float, default=0.0)
    total_penalty = db.Column(db.Float, default=0.0)

    # Metadata
    calculation_type = db.Column(db.String(20), default='manual')  # manual, sensor, batch
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    calculated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    sample = db.relationship('WaterSample', backref='wqi_calculations', lazy=True)
    site = db.relationship('Site', backref='wqi_calculations', lazy=True)
    residential_site = db.relationship('ResidentialSite', backref='wqi_calculations', lazy=True)
    calculated_by = db.relationship('User', backref='wqi_calculations', lazy=True)

    def __repr__(self):
        return f'<WQICalculation {self.id}: {self.wqi_score:.2f} ({self.compliance_class})>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'site_id': self.site_id,
            'device_id': self.device_id,
            'wqi_score': round(self.wqi_score, 2) if self.wqi_score else None,
            'compliance_class': self.compliance_class,
            'is_safe': self.is_safe,
            'penalties': {
                'ph': round(self.ph_penalty, 2),
                'tds': round(self.tds_penalty, 2),
                'turbidity': round(self.turbidity_penalty, 2),
                'chlorine': round(self.chlorine_penalty, 2),
                'temperature': round(self.temperature_penalty, 2),
                'coliform': round(self.coliform_penalty, 2)
            },
            'total_penalty': round(self.total_penalty, 2),
            'input_parameters': {
                'ph_value': self.ph_value,
                'tds_ppm': self.tds_ppm,
                'turbidity_ntu': self.turbidity_ntu,
                'free_chlorine': self.free_chlorine,
                'temperature_c': self.temperature_c,
                'total_coliform': self.total_coliform
            },
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'calculation_type': self.calculation_type
        }

    @staticmethod
    def get_latest_for_device(device_id: str):
        """Get most recent WQI calculation for a device"""
        return WQICalculation.query.filter_by(device_id=device_id).order_by(
            desc(WQICalculation.calculated_at)
        ).first()

    @staticmethod
    def get_latest_for_site(site_id: int):
        """Get most recent WQI calculation for a site"""
        return WQICalculation.query.filter_by(site_id=site_id).order_by(
            desc(WQICalculation.calculated_at)
        ).first()

    @staticmethod
    def get_history_for_device(device_id: str, limit=100):
        """Get historical WQI calculations for a device"""
        return WQICalculation.query.filter_by(device_id=device_id).order_by(
            desc(WQICalculation.calculated_at)
        ).limit(limit).all()

    @staticmethod
    def get_history_for_site(site_id: int, limit=100):
        """Get historical WQI calculations for a site"""
        return WQICalculation.query.filter_by(site_id=site_id).order_by(
            desc(WQICalculation.calculated_at)
        ).limit(limit).all()

    @staticmethod
    def get_summary_statistics(days=30):
        """
        Get summary statistics for WQI calculations

        Args:
            days: Number of days to include in statistics

        Returns:
            Dictionary with statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        recent_calculations = WQICalculation.query.filter(
            WQICalculation.calculated_at >= cutoff_date
        ).all()

        if not recent_calculations:
            return {
                'total_calculations': 0,
                'average_wqi': None,
                'excellent_count': 0,
                'compliant_count': 0,
                'warning_count': 0,
                'unsafe_count': 0,
                'safe_percentage': None
            }

        total = len(recent_calculations)
        wqi_scores = [calc.wqi_score for calc in recent_calculations if calc.wqi_score is not None]
        avg_wqi = sum(wqi_scores) / len(wqi_scores) if wqi_scores else None

        excellent = sum(1 for calc in recent_calculations if calc.compliance_class == 'excellent')
        compliant = sum(1 for calc in recent_calculations if calc.compliance_class == 'compliant')
        warning = sum(1 for calc in recent_calculations if calc.compliance_class == 'warning')
        unsafe = sum(1 for calc in recent_calculations if calc.compliance_class == 'unsafe')

        safe_count = sum(1 for calc in recent_calculations if calc.is_safe)
        safe_percentage = (safe_count / total * 100) if total > 0 else None

        return {
            'total_calculations': total,
            'average_wqi': round(avg_wqi, 2) if avg_wqi else None,
            'excellent_count': excellent,
            'compliant_count': compliant,
            'warning_count': warning,
            'unsafe_count': unsafe,
            'safe_percentage': round(safe_percentage, 1) if safe_percentage else None,
            'period_days': days
        }
