"""
Treatment Method Model
Defines various water treatment methods and their characteristics
"""
from datetime import datetime
from app import db
import json


class TreatmentMethod(db.Model):
    """
    Represents a water treatment method that can be applied to contaminated water sources.

    Examples: Pipe replacement, chlorination, reverse osmosis, filtration systems
    """
    __tablename__ = 'treatment_methods'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    name = db.Column(db.String(200), nullable=False, unique=True)
    category = db.Column(db.String(100), nullable=False)  # infrastructure, filtration, disinfection, source_change
    description = db.Column(db.Text)

    # Cost Information
    typical_cost_min = db.Column(db.Float)  # Minimum typical cost in local currency
    typical_cost_max = db.Column(db.Float)  # Maximum typical cost in local currency
    cost_currency = db.Column(db.String(10), default='INR')
    cost_unit = db.Column(db.String(50))  # per_household, per_village, per_liter_day, etc.

    # Implementation Details
    implementation_time_days = db.Column(db.Integer)  # Typical time to implement
    maintenance_requirements = db.Column(db.Text)  # Description of ongoing maintenance
    technical_complexity = db.Column(db.String(50))  # low, medium, high
    required_expertise = db.Column(db.Text)  # Skills/expertise needed

    # Effectiveness
    effectiveness_rate = db.Column(db.Float)  # 0-100, calculated from historical interventions
    suitable_for_contaminants = db.Column(db.Text)  # JSON array of contamination types
    limitations = db.Column(db.Text)  # Known limitations or contraindications

    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    references = db.Column(db.Text)  # Research papers, guidelines, etc.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TreatmentMethod {self.name}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'cost_range': f"{self.cost_currency} {self.typical_cost_min:,.0f} - {self.typical_cost_max:,.0f}" if self.typical_cost_min else None,
            'cost_unit': self.cost_unit,
            'implementation_days': self.implementation_time_days,
            'technical_complexity': self.technical_complexity,
            'effectiveness_rate': self.effectiveness_rate,
            'suitable_for': self.get_suitable_contaminants(),
            'is_active': self.is_active
        }

    def get_suitable_contaminants(self):
        """Parse and return suitable contaminants list"""
        if not self.suitable_for_contaminants:
            return []
        try:
            return json.loads(self.suitable_for_contaminants)
        except:
            return []

    def set_suitable_contaminants(self, contaminants_list):
        """Store suitable contaminants as JSON"""
        self.suitable_for_contaminants = json.dumps(contaminants_list)

    @property
    def cost_range_display(self):
        """Get human-readable cost range"""
        if not self.typical_cost_min or not self.typical_cost_max:
            return "Cost not specified"

        return f"{self.cost_currency} {self.typical_cost_min:,.0f} - {self.typical_cost_max:,.0f} {self.cost_unit or ''}"

    @property
    def effectiveness_display(self):
        """Get human-readable effectiveness"""
        if not self.effectiveness_rate:
            return "Not yet calculated"

        if self.effectiveness_rate >= 80:
            return f"Highly effective ({self.effectiveness_rate:.1f}%)"
        elif self.effectiveness_rate >= 60:
            return f"Moderately effective ({self.effectiveness_rate:.1f}%)"
        else:
            return f"Limited effectiveness ({self.effectiveness_rate:.1f}%)"

    @staticmethod
    def get_category_choices():
        """Return list of valid treatment categories"""
        return [
            ('infrastructure', 'Infrastructure Improvement'),
            ('filtration', 'Filtration System'),
            ('disinfection', 'Disinfection/Chemical Treatment'),
            ('source_change', 'Water Source Change'),
            ('behavioral', 'Behavioral/Educational Intervention'),
            ('maintenance', 'Maintenance/Repair'),
            ('other', 'Other')
        ]

    @staticmethod
    def get_complexity_choices():
        """Return list of technical complexity levels"""
        return [
            ('low', 'Low - Community can implement'),
            ('medium', 'Medium - Requires technical assistance'),
            ('high', 'High - Requires specialized expertise')
        ]

    def calculate_effectiveness(self):
        """
        Calculate effectiveness rate from historical interventions
        This should be called periodically to update effectiveness based on actual results
        """
        # Import here to avoid circular dependency
        from app.models.intervention import Intervention

        # Get all completed interventions using this treatment method
        interventions = Intervention.query.filter_by(
            treatment_method_id=self.id,
            status='completed'
        ).all()

        if not interventions:
            return None

        # Count successful interventions (those that improved water quality)
        successful = sum(1 for i in interventions if i.was_successful())
        total = len(interventions)

        self.effectiveness_rate = (successful / total) * 100
        return self.effectiveness_rate
