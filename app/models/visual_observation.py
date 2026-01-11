"""
Visual Observation Model - Field observations and photo documentation
For tracking visual water quality indicators during site visits
"""
from app import db
from datetime import datetime


class VisualObservation(db.Model):
    """Field observations and visual analysis of water bodies"""

    __tablename__ = 'visual_observations'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Observation Information
    observation_date = db.Column(db.Date, nullable=False)
    observation_time = db.Column(db.Time, nullable=True)
    observer_name = db.Column(db.String(100))

    # Photo Information (optional)
    photo_path = db.Column(db.String(500))  # Path to image file
    photo_filename = db.Column(db.String(255))
    photo_format = db.Column(db.String(10), default='jpg')  # 'jpg', 'png'

    # GPS Location (if available)
    gps_latitude = db.Column(db.Float)
    gps_longitude = db.Column(db.Float)

    # Visual Indicators - Water Appearance
    water_color = db.Column(db.String(50))  # 'clear', 'greenish', 'brownish', 'yellowish', 'milky', 'dark'
    water_clarity = db.Column(db.String(50))  # 'transparent', 'slightly_turbid', 'turbid', 'very_turbid'
    water_odor = db.Column(db.String(50))  # 'none', 'earthy', 'musty', 'chemical', 'sewage', 'rotten_egg'
    surface_condition = db.Column(db.String(50))  # 'clean', 'oily_sheen', 'foam', 'debris', 'algae_bloom'

    # Visual Indicators - Surroundings
    algae_presence = db.Column(db.String(30))  # 'none', 'low', 'moderate', 'high', 'severe'
    floating_debris = db.Column(db.Boolean, default=False)
    dead_fish = db.Column(db.Boolean, default=False)
    visible_pollution = db.Column(db.Boolean, default=False)
    pollution_type = db.Column(db.String(100))  # 'plastic', 'sewage', 'industrial', 'agricultural', 'other'

    # Water Level Observation
    water_level = db.Column(db.String(30))  # 'very_low', 'low', 'normal', 'high', 'flood'
    bank_condition = db.Column(db.String(50))  # 'good', 'eroded', 'overgrown', 'littered'

    # Weather Conditions
    weather = db.Column(db.String(50))  # 'sunny', 'cloudy', 'rainy', 'stormy'
    recent_rainfall = db.Column(db.Boolean, default=False)

    # Overall Assessment
    visual_quality_rating = db.Column(db.Integer)  # 1-5 scale (1=very poor, 5=excellent)
    concerns_noted = db.Column(db.Text)  # Free text for observer notes
    recommended_action = db.Column(db.String(200))  # 'none', 'monitor', 'test', 'urgent_test', 'notify_authorities'

    # Analysis Status
    analysis_status = db.Column(db.String(20), default='pending')  # 'pending', 'reviewed', 'flagged'
    reviewed_by = db.Column(db.String(100))
    review_date = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sample = db.relationship('WaterSample', backref='visual_observations', lazy=True)
    site = db.relationship('Site', backref='visual_observations', lazy=True)

    def __repr__(self):
        return f'<VisualObservation {self.id}: Site {self.site_id} on {self.observation_date}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'site_id': self.site_id,
            'observation_date': self.observation_date.isoformat() if self.observation_date else None,
            'observation_time': self.observation_time.isoformat() if self.observation_time else None,
            'observer_name': self.observer_name,
            'water_color': self.water_color,
            'water_clarity': self.water_clarity,
            'water_odor': self.water_odor,
            'surface_condition': self.surface_condition,
            'algae_presence': self.algae_presence,
            'floating_debris': self.floating_debris,
            'dead_fish': self.dead_fish,
            'visible_pollution': self.visible_pollution,
            'pollution_type': self.pollution_type,
            'water_level': self.water_level,
            'visual_quality_rating': self.visual_quality_rating,
            'concerns_noted': self.concerns_noted,
            'recommended_action': self.recommended_action,
            'analysis_status': self.analysis_status,
            'gps_latitude': self.gps_latitude,
            'gps_longitude': self.gps_longitude,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def is_contaminated_visual(self):
        """
        Determine if water appears contaminated based on visual observation

        Returns:
            (is_contaminated, reasons) tuple
        """
        reasons = []

        # Check water clarity
        if self.water_clarity in ['turbid', 'very_turbid']:
            reasons.append(f'Water is {self.water_clarity.replace("_", " ")}')

        # Check water color
        if self.water_color in ['brownish', 'dark', 'milky']:
            reasons.append(f'Abnormal water color: {self.water_color}')

        # Check odor
        if self.water_odor in ['sewage', 'chemical', 'rotten_egg']:
            reasons.append(f'Concerning odor detected: {self.water_odor.replace("_", " ")}')

        # Check algae
        if self.algae_presence in ['high', 'severe']:
            reasons.append(f'Significant algae presence: {self.algae_presence}')

        # Check visible pollution
        if self.visible_pollution:
            reasons.append(f'Visible pollution ({self.pollution_type or "unspecified type"})')

        # Check for dead fish
        if self.dead_fish:
            reasons.append('Dead fish observed - potential contamination indicator')

        # Check surface condition
        if self.surface_condition in ['oily_sheen', 'sewage', 'algae_bloom']:
            reasons.append(f'Surface condition: {self.surface_condition.replace("_", " ")}')

        is_contaminated = len(reasons) > 0

        return (is_contaminated, reasons)

    def get_urgency_level(self):
        """
        Determine urgency level based on observations

        Returns:
            str: 'low', 'medium', 'high', 'critical'
        """
        is_contaminated, reasons = self.is_contaminated_visual()

        if self.dead_fish or self.water_odor in ['sewage', 'chemical']:
            return 'critical'

        if self.visible_pollution or self.algae_presence == 'severe':
            return 'high'

        if is_contaminated:
            return 'medium'

        if self.visual_quality_rating and self.visual_quality_rating <= 2:
            return 'medium'

        return 'low'
