"""
Analysis Model - Contamination analysis and root cause determination
"""
from app import db
from datetime import datetime
import json

class Analysis(db.Model):
    """Contamination analysis and classification"""

    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=False)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'))

    # Analysis Information
    analysis_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    analyzed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    analysis_type = db.Column(db.String(50), default='automated')  # automated, manual, hybrid

    # Primary Classification
    contamination_detected = db.Column(db.Boolean, default=False)
    primary_cause = db.Column(db.String(100))  # runoff_sediment, sewage_ingress, salt_intrusion, pipe_corrosion, disinfectant_decay
    confidence_level = db.Column(db.Float)  # 0.0 to 1.0
    severity = db.Column(db.String(20))  # low, medium, high, critical

    # Rule-Based Classification Results
    runoff_sediment_score = db.Column(db.Float)
    runoff_sediment_indicators = db.Column(db.Text)  # JSON array of indicators

    sewage_ingress_score = db.Column(db.Float)
    sewage_ingress_indicators = db.Column(db.Text)

    salt_intrusion_score = db.Column(db.Float)
    salt_intrusion_indicators = db.Column(db.Text)

    pipe_corrosion_score = db.Column(db.Float)
    pipe_corrosion_indicators = db.Column(db.Text)

    disinfectant_decay_score = db.Column(db.Float)
    disinfectant_decay_indicators = db.Column(db.Text)

    # ML Model Results
    ml_prediction = db.Column(db.String(100))
    ml_confidence = db.Column(db.Float)
    ml_model_version = db.Column(db.String(50))
    ml_response_data = db.Column(db.Text)  # Full JSON response from ML API
    ml_api_error = db.Column(db.Text)

    # Compliance Check
    who_compliant = db.Column(db.Boolean)
    bis_compliant = db.Column(db.Boolean)  # Bureau of Indian Standards
    non_compliant_parameters = db.Column(db.Text)  # JSON array

    # Recommendations
    immediate_actions = db.Column(db.Text)  # JSON array of immediate actions
    short_term_solutions = db.Column(db.Text)  # JSON array
    long_term_solutions = db.Column(db.Text)  # JSON array
    estimated_cost = db.Column(db.String(50))
    implementation_priority = db.Column(db.String(20))  # immediate, urgent, normal, low

    # Follow-up
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    follow_up_completed = db.Column(db.Boolean, default=False)
    follow_up_notes = db.Column(db.Text)

    # Review Status
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, approved, archived
    reviewed_by = db.Column(db.String(100))
    review_date = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)

    # Additional Analysis
    historical_comparison = db.Column(db.Text)  # JSON comparison with previous tests
    trend_analysis = db.Column(db.Text)  # JSON trend data
    seasonal_factors = db.Column(db.Text)

    # Metadata
    analysis_duration_seconds = db.Column(db.Integer)
    data_quality_score = db.Column(db.Float)  # 0.0 to 1.0
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Analysis sample={self.sample.sample_id} cause={self.primary_cause}>'

    def set_indicators(self, cause_type, indicators_list):
        """Set indicators as JSON string"""
        field_name = f"{cause_type}_indicators"
        if hasattr(self, field_name):
            setattr(self, field_name, json.dumps(indicators_list))

    def get_indicators(self, cause_type):
        """Get indicators as Python list"""
        field_name = f"{cause_type}_indicators"
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            return json.loads(value) if value else []
        return []

    def set_recommendations(self, immediate=None, short_term=None, long_term=None):
        """Set recommendations as JSON"""
        if immediate:
            self.immediate_actions = json.dumps(immediate)
        if short_term:
            self.short_term_solutions = json.dumps(short_term)
        if long_term:
            self.long_term_solutions = json.dumps(long_term)

    def get_recommendations(self):
        """Get all recommendations as dictionary"""
        return {
            'immediate': json.loads(self.immediate_actions) if self.immediate_actions else [],
            'short_term': json.loads(self.short_term_solutions) if self.short_term_solutions else [],
            'long_term': json.loads(self.long_term_solutions) if self.long_term_solutions else []
        }

    def to_dict(self):
        """Convert analysis to dictionary"""
        return {
            'id': self.id,
            'sample_id': self.sample.sample_id if self.sample else None,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'contamination_detected': self.contamination_detected,
            'primary_cause': self.primary_cause,
            'confidence_level': self.confidence_level,
            'severity': self.severity,
            'ml_prediction': self.ml_prediction,
            'ml_confidence': self.ml_confidence,
            'who_compliant': self.who_compliant,
            'bis_compliant': self.bis_compliant,
            'recommendations': self.get_recommendations(),
            'status': self.status
        }
