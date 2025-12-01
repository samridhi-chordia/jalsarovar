"""
Intervention Model
Tracks remediation efforts and treatment implementations for water quality issues
"""
from datetime import datetime
from app import db
import json


class Intervention(db.Model):
    """
    Represents a water treatment intervention or remediation effort.

    Tracks the implementation of treatment methods at specific sites
    and measures their effectiveness.
    """
    __tablename__ = 'interventions'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Scope - at least one must be specified
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)  # Site-wide intervention
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)  # Sample-specific

    # Treatment Method
    treatment_method_id = db.Column(db.Integer, db.ForeignKey('treatment_methods.id'), nullable=False)

    # Basic Information
    intervention_type = db.Column(db.String(100), nullable=False)  # pipe_replacement, chlorination, filtration, etc.
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)

    # Timeline
    planned_date = db.Column(db.Date)
    implementation_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)

    # Implementation Details
    implemented_by = db.Column(db.String(200))  # Organization or person
    funding_source = db.Column(db.String(200))
    cost = db.Column(db.Float)
    cost_currency = db.Column(db.String(10), default='INR')

    # Expected vs Actual Outcomes
    expected_outcomes = db.Column(db.Text)  # JSON: {parameter: expected_value}
    actual_outcomes = db.Column(db.Text)  # JSON: {parameter: actual_value}, populated after follow-up

    # Success Tracking
    followup_sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    followup_scheduled_date = db.Column(db.Date)
    followup_completed_date = db.Column(db.Date)

    # Status
    status = db.Column(
        db.String(50),
        nullable=False,
        default='planned'
    )  # planned, in_progress, completed, failed, abandoned

    # Analysis
    improvement_percentage = db.Column(db.Float)  # Overall quality improvement
    was_effective = db.Column(db.Boolean)  # Did it achieve goals?
    lessons_learned = db.Column(db.Text)

    # Documentation
    photos_before = db.Column(db.Text)  # JSON array of photo URLs
    photos_after = db.Column(db.Text)  # JSON array of photo URLs
    documentation = db.Column(db.Text)  # Additional docs, reports, etc.

    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = db.relationship('Site', foreign_keys=[site_id], backref='interventions')
    sample = db.relationship('WaterSample', foreign_keys=[sample_id], backref='interventions_for_sample')
    followup_sample = db.relationship('WaterSample', foreign_keys=[followup_sample_id])
    treatment_method = db.relationship('TreatmentMethod', backref='interventions')
    created_by = db.relationship('User', backref='interventions_created')

    def __repr__(self):
        return f'<Intervention {self.title} ({self.status})>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'intervention_type': self.intervention_type,
            'treatment_method': self.treatment_method.name if self.treatment_method else None,
            'site': self.site.name if self.site else None,
            'status': self.status,
            'implementation_date': self.implementation_date.isoformat() if self.implementation_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'cost': self.cost,
            'cost_currency': self.cost_currency,
            'was_effective': self.was_effective,
            'improvement_percentage': self.improvement_percentage,
            'implemented_by': self.implemented_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def get_expected_outcomes(self):
        """Parse and return expected outcomes"""
        if not self.expected_outcomes:
            return {}
        try:
            return json.loads(self.expected_outcomes)
        except:
            return {}

    def set_expected_outcomes(self, outcomes_dict):
        """Store expected outcomes as JSON"""
        self.expected_outcomes = json.dumps(outcomes_dict, indent=2)

    def get_actual_outcomes(self):
        """Parse and return actual outcomes"""
        if not self.actual_outcomes:
            return {}
        try:
            return json.loads(self.actual_outcomes)
        except:
            return {}

    def set_actual_outcomes(self, outcomes_dict):
        """Store actual outcomes as JSON"""
        self.actual_outcomes = json.dumps(outcomes_dict, indent=2)

    def get_photos_before(self):
        """Parse and return before photos list"""
        if not self.photos_before:
            return []
        try:
            return json.loads(self.photos_before)
        except:
            return []

    def get_photos_after(self):
        """Parse and return after photos list"""
        if not self.photos_after:
            return []
        try:
            return json.loads(self.photos_after)
        except:
            return []

    @property
    def duration_days(self):
        """Calculate duration of intervention"""
        if not self.implementation_date or not self.completion_date:
            return None
        return (self.completion_date - self.implementation_date).days

    @property
    def cost_display(self):
        """Get human-readable cost"""
        if not self.cost:
            return "Cost not recorded"
        return f"{self.cost_currency} {self.cost:,.2f}"

    @property
    def effectiveness_display(self):
        """Get human-readable effectiveness"""
        if self.was_effective is None:
            return "Not yet evaluated"
        elif self.was_effective:
            return f"Effective ({self.improvement_percentage:.1f}% improvement)" if self.improvement_percentage else "Effective"
        else:
            return "Not effective"

    def was_successful(self):
        """
        Determine if intervention was successful
        Used for calculating treatment method effectiveness
        """
        if self.status != 'completed':
            return False

        if self.was_effective is not None:
            return self.was_effective

        # If not explicitly marked, consider successful if improvement > 20%
        if self.improvement_percentage and self.improvement_percentage > 20:
            return True

        return False

    def calculate_effectiveness(self):
        """
        Calculate effectiveness by comparing before/after water quality
        Requires both baseline sample and followup sample
        """
        if not self.sample or not self.followup_sample:
            return None

        # Get test results for baseline sample
        baseline_tests = {tr.parameter_name: tr.value for tr in self.sample.test_results}

        # Get test results for followup sample
        followup_tests = {tr.parameter_name: tr.value for tr in self.followup_sample.test_results}

        if not baseline_tests or not followup_tests:
            return None

        # Calculate improvement for each parameter
        improvements = []
        for param, baseline_value in baseline_tests.items():
            if param in followup_tests:
                followup_value = followup_tests[param]

                if baseline_value > 0:  # Avoid division by zero
                    # For contaminants, lower is better (negative change is improvement)
                    # For pH and DO, closer to ideal is better (handled separately)
                    change_pct = ((baseline_value - followup_value) / baseline_value) * 100
                    improvements.append(change_pct)

        if improvements:
            # Average improvement across all parameters
            self.improvement_percentage = sum(improvements) / len(improvements)

            # Mark as effective if average improvement > 20%
            self.was_effective = self.improvement_percentage > 20

            return self.improvement_percentage

        return None

    @staticmethod
    def get_status_choices():
        """Return list of valid status values"""
        return [
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('abandoned', 'Abandoned')
        ]

    @staticmethod
    def get_status_color(status):
        """Get Bootstrap color class for status"""
        colors = {
            'planned': 'secondary',
            'in_progress': 'info',
            'completed': 'success',
            'failed': 'danger',
            'abandoned': 'warning'
        }
        return colors.get(status, 'secondary')

    @staticmethod
    def get_intervention_types():
        """Return common intervention types"""
        return [
            ('pipe_replacement', 'Pipe Replacement'),
            ('chlorination', 'Chlorination'),
            ('filtration_system', 'Filtration System Installation'),
            ('reverse_osmosis', 'Reverse Osmosis System'),
            ('source_protection', 'Source Water Protection'),
            ('well_cleaning', 'Well Cleaning/Rehabilitation'),
            ('storage_tank_cleaning', 'Storage Tank Cleaning'),
            ('pump_repair', 'Pump Repair/Replacement'),
            ('watershed_management', 'Watershed Management'),
            ('community_education', 'Community Education Program'),
            ('other', 'Other')
        ]
