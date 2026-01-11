"""Analysis model - Contamination detection results"""
from datetime import datetime
from app import db


class Analysis(db.Model):
    """Contamination analysis results from rule-based and ML models"""
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=False, index=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'), index=True)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Overall Assessment
    is_contaminated = db.Column(db.Boolean, default=False)
    contamination_type = db.Column(db.String(50))  # Primary contamination type
    severity_level = db.Column(db.String(20))  # critical, high, medium, low
    confidence_score = db.Column(db.Float)  # 0-100%

    # Water Quality Index
    wqi_score = db.Column(db.Float)  # 0-100
    wqi_class = db.Column(db.String(20))  # Excellent, Compliant, Warning, Unsafe

    # Data Quality Metrics
    data_coverage_pct = db.Column(db.Float)  # Percentage of parameters measured
    parameters_measured = db.Column(db.Integer)  # Total count of measured params
    key_parameters_measured = db.Column(db.Integer)  # Count of 5 key params
    has_sufficient_data = db.Column(db.Boolean, default=True)  # ≥3 key params
    data_quality_tier = db.Column(db.String(20))  # 'full', 'partial', 'insufficient'

    # Contamination Type Scores (0-1 each)
    runoff_sediment_score = db.Column(db.Float, default=0)
    sewage_ingress_score = db.Column(db.Float, default=0)
    salt_intrusion_score = db.Column(db.Float, default=0)
    pipe_corrosion_score = db.Column(db.Float, default=0)
    disinfectant_decay_score = db.Column(db.Float, default=0)

    # Compliance
    is_compliant_who = db.Column(db.Boolean)
    is_compliant_bis = db.Column(db.Boolean)
    who_violations = db.Column(db.Text)  # JSON list of violations
    bis_violations = db.Column(db.Text)  # JSON list of violations

    # Analysis source
    analysis_method = db.Column(db.String(50), default='rule_based')  # rule_based, ml_xgboost, ml_rf
    model_version = db.Column(db.String(50))

    # Recommendations (JSON)
    primary_recommendation = db.Column(db.Text)
    secondary_recommendations = db.Column(db.Text)  # JSON list
    estimated_treatment_cost_inr = db.Column(db.Float)
    treatment_urgency = db.Column(db.String(20))  # immediate, within_week, within_month

    # Metadata
    analyzed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    contamination_predictions = db.relationship('ContaminationPrediction', backref='analysis', lazy='dynamic')

    def get_contamination_breakdown(self):
        """Get breakdown of all contamination scores"""
        return {
            'Runoff/Sediment': self.runoff_sediment_score or 0,
            'Sewage Ingress': self.sewage_ingress_score or 0,
            'Salt Intrusion': self.salt_intrusion_score or 0,
            'Pipe Corrosion': self.pipe_corrosion_score or 0,
            'Disinfectant Decay': self.disinfectant_decay_score or 0
        }

    def get_primary_cause(self):
        """Get primary contamination cause"""
        scores = self.get_contamination_breakdown()
        if max(scores.values()) == 0:
            return None, 0
        primary = max(scores, key=scores.get)
        return primary, scores[primary]

    def __repr__(self):
        return f'<Analysis {self.id}: {self.contamination_type} ({self.severity_level})>'
