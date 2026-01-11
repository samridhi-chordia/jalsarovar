"""Intervention and Treatment models"""
from datetime import datetime
from app import db


class TreatmentMethod(db.Model):
    """Reference data for treatment methods"""
    __tablename__ = 'treatment_methods'

    id = db.Column(db.Integer, primary_key=True)
    method_name = db.Column(db.String(200), nullable=False)
    method_code = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)

    # Applicability
    contamination_types = db.Column(db.Text)  # JSON list: runoff, sewage, salt, corrosion, decay
    water_body_types = db.Column(db.Text)  # JSON list: pond, lake, tank, etc.

    # Cost
    estimated_cost_min_inr = db.Column(db.Float)
    estimated_cost_max_inr = db.Column(db.Float)
    cost_per_kl = db.Column(db.Float)  # Cost per kiloliter

    # Effectiveness
    average_effectiveness_percent = db.Column(db.Float)
    time_to_effect_days = db.Column(db.Integer)
    duration_effectiveness_months = db.Column(db.Integer)

    # Implementation
    implementation_time_days = db.Column(db.Integer)
    requires_specialist = db.Column(db.Boolean, default=False)
    requires_equipment = db.Column(db.Boolean, default=False)
    equipment_list = db.Column(db.Text)

    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    interventions = db.relationship('Intervention', backref='treatment_method', lazy='dynamic')

    def get_cost_estimate(self, volume_kl=None):
        """Get cost estimate"""
        if volume_kl and self.cost_per_kl:
            return volume_kl * self.cost_per_kl
        return (self.estimated_cost_min_inr + self.estimated_cost_max_inr) / 2

    def __repr__(self):
        return f'<TreatmentMethod {self.method_name}>'


class Intervention(db.Model):
    """Treatment/intervention records"""
    __tablename__ = 'interventions'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), index=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'))
    treatment_method_id = db.Column(db.Integer, db.ForeignKey('treatment_methods.id'))

    # Intervention details
    intervention_date = db.Column(db.Date, nullable=False)
    intervention_type = db.Column(db.String(100))  # treatment, repair, cleaning, replacement
    description = db.Column(db.Text)

    # Cost
    actual_cost_inr = db.Column(db.Float)
    labor_cost_inr = db.Column(db.Float)
    material_cost_inr = db.Column(db.Float)

    # Before/After measurements
    parameter_targeted = db.Column(db.String(50))  # ph, turbidity, chlorine, etc.
    before_value = db.Column(db.Float)
    after_value = db.Column(db.Float)
    improvement_percent = db.Column(db.Float)

    # Effectiveness
    effectiveness_rating = db.Column(db.Integer)  # 1-10
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)

    # Status
    status = db.Column(db.String(20), default='planned')  # planned, in_progress, completed, verified
    completed_date = db.Column(db.Date)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    verification_date = db.Column(db.Date)

    # Metadata
    implemented_by = db.Column(db.String(200))
    contractor = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    site = db.relationship('Site', foreign_keys=[site_id])

    def calculate_effectiveness(self):
        """Calculate improvement percentage"""
        if self.before_value and self.after_value and self.before_value != 0:
            return ((self.before_value - self.after_value) / self.before_value) * 100
        return None

    def __repr__(self):
        return f'<Intervention {self.id}: {self.intervention_type}>'
