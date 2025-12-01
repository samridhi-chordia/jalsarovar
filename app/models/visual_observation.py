"""
Visual Observation Model - Camera photos and computer vision analysis
"""
from app import db
from datetime import datetime


class VisualObservation(db.Model):
    """Photos and visual analysis of water bodies"""

    __tablename__ = 'visual_observations'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Photo Information
    photo_date = db.Column(db.Date, nullable=False)
    photo_time = db.Column(db.Time, nullable=False)
    photographer = db.Column(db.String(100))  # User or 'Robot-{id}'
    photo_type = db.Column(db.String(50), nullable=False)  # 'water_surface', 'test_strip', 'documentation'

    # File Storage
    photo_path = db.Column(db.String(500), nullable=False)  # Path to image file
    photo_filename = db.Column(db.String(255), nullable=False)
    photo_size_bytes = db.Column(db.Integer)
    photo_resolution = db.Column(db.String(20))  # e.g., '3280x2464'
    photo_format = db.Column(db.String(10), default='jpg')  # 'jpg', 'png'

    # Camera Settings
    camera_model = db.Column(db.String(100))  # e.g., 'Raspberry Pi Camera v2'
    led_brightness = db.Column(db.Integer)  # 0-100
    exposure_time_ms = db.Column(db.Float)
    iso_value = db.Column(db.Integer)

    # GPS Location (if available)
    gps_latitude = db.Column(db.Float)
    gps_longitude = db.Column(db.Float)
    gps_altitude_meters = db.Column(db.Float)
    gps_accuracy_meters = db.Column(db.Float)

    # Color Analysis (water surface photos)
    rgb_mean_r = db.Column(db.Float)  # Mean red value (0-255)
    rgb_mean_g = db.Column(db.Float)  # Mean green value
    rgb_mean_b = db.Column(db.Float)  # Mean blue value
    hsv_mean_h = db.Column(db.Float)  # Mean hue (0-360)
    hsv_mean_s = db.Column(db.Float)  # Mean saturation (0-100)
    hsv_mean_v = db.Column(db.Float)  # Mean value/brightness (0-100)
    dominant_color_r = db.Column(db.Integer)  # Dominant color RGB
    dominant_color_g = db.Column(db.Integer)
    dominant_color_b = db.Column(db.Integer)
    color_category = db.Column(db.String(30))  # 'clear_gray', 'green', 'yellow_brown', 'blue', etc.

    # Clarity Analysis
    clarity_score = db.Column(db.Float)  # 0-100 (higher = clearer water)
    edge_sharpness = db.Column(db.Float)  # Laplacian variance
    contrast_ratio = db.Column(db.Float)  # Michelson contrast
    texture_entropy = db.Column(db.Float)  # Shannon entropy
    estimated_turbidity_ntu = db.Column(db.Float)  # Visual turbidity proxy
    clarity_category = db.Column(db.String(30))  # 'crystal_clear', 'clear', 'turbid', etc.

    # Algae Detection
    algae_coverage_percent = db.Column(db.Float)  # % of water surface with algae
    algae_type = db.Column(db.String(50))  # 'green_algae', 'blue_green_algae', 'brown_algae'
    algae_severity = db.Column(db.String(20))  # 'none', 'low', 'moderate', 'high', 'severe'
    algae_distribution = db.Column(db.String(30))  # 'none', 'localized', 'patchy', 'scattered', 'uniform_dense'
    chlorophyll_proxy_ug_l = db.Column(db.Float)  # Estimated chlorophyll-a (µg/L)
    eutrophication_status = db.Column(db.String(30))  # 'oligotrophic', 'mesotrophic', 'eutrophic', 'hypereutrophic'

    # Test Strip Reading (for test_strip photos)
    strip_parameter = db.Column(db.String(50))  # 'pH', 'chlorine_mg_l', 'nitrate_mg_l', etc.
    strip_value = db.Column(db.Float)  # Read value from color matching
    strip_confidence = db.Column(db.Float)  # Confidence (0-100)
    strip_pad_color_r = db.Column(db.Integer)  # Detected pad color RGB
    strip_pad_color_g = db.Column(db.Integer)
    strip_pad_color_b = db.Column(db.Integer)

    # Quality Control
    analysis_status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    analysis_engine = db.Column(db.String(50))  # 'color_analyzer_v1', 'clarity_scorer_v1', etc.
    analysis_version = db.Column(db.String(20))
    analysis_error = db.Column(db.Text)  # Error message if analysis failed

    # Metadata
    description = db.Column(db.Text)  # User description or auto-generated
    tags = db.Column(db.String(500))  # Comma-separated tags
    is_flagged = db.Column(db.Boolean, default=False)  # Flagged for review
    flag_reason = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sample = db.relationship('WaterSample', backref='visual_observations', lazy=True)
    site = db.relationship('Site', backref='visual_observations', lazy=True)

    def __repr__(self):
        return f'<VisualObservation {self.id}: {self.photo_type} at {self.site_id}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sample_id': self.sample_id,
            'site_id': self.site_id,
            'photo_date': self.photo_date.isoformat() if self.photo_date else None,
            'photo_time': self.photo_time.isoformat() if self.photo_time else None,
            'photo_type': self.photo_type,
            'photo_path': self.photo_path,
            'photo_filename': self.photo_filename,
            'photo_size_bytes': self.photo_size_bytes,
            'color_category': self.color_category,
            'clarity_score': self.clarity_score,
            'clarity_category': self.clarity_category,
            'algae_coverage_percent': self.algae_coverage_percent,
            'algae_severity': self.algae_severity,
            'eutrophication_status': self.eutrophication_status,
            'strip_parameter': self.strip_parameter,
            'strip_value': self.strip_value,
            'strip_confidence': self.strip_confidence,
            'analysis_status': self.analysis_status,
            'gps_latitude': self.gps_latitude,
            'gps_longitude': self.gps_longitude,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def get_color_rgb(self):
        """Get average color as RGB tuple"""
        if self.rgb_mean_r is not None:
            return (
                round(self.rgb_mean_r),
                round(self.rgb_mean_g),
                round(self.rgb_mean_b)
            )
        return None

    def get_dominant_color_rgb(self):
        """Get dominant color as RGB tuple"""
        if self.dominant_color_r is not None:
            return (
                self.dominant_color_r,
                self.dominant_color_g,
                self.dominant_color_b
            )
        return None

    def is_contaminated_visual(self):
        """
        Determine if water appears contaminated based on visual analysis

        Returns:
            (is_contaminated, reasons) tuple
        """
        reasons = []

        # Check clarity
        if self.clarity_score is not None and self.clarity_score < 40:
            reasons.append(f'Very turbid (clarity: {self.clarity_score:.1f}/100)')

        # Check algae
        if self.algae_severity in ['high', 'severe']:
            reasons.append(f'Severe algae bloom ({self.algae_coverage_percent:.1f}% coverage)')

        # Check eutrophication
        if self.eutrophication_status in ['eutrophic', 'hypereutrophic']:
            reasons.append(f'Eutrophic water body ({self.eutrophication_status})')

        # Check color (brown/red = contamination)
        if self.color_category in ['red_brown', 'yellow_brown', 'very_dark']:
            reasons.append(f'Abnormal color ({self.color_category})')

        is_contaminated = len(reasons) > 0

        return (is_contaminated, reasons)


class VisualTrendAnalysis(db.Model):
    """Time series analysis of visual water quality"""

    __tablename__ = 'visual_trend_analysis'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Time Period
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)

    # Clarity Trends
    avg_clarity_score = db.Column(db.Float)
    min_clarity_score = db.Column(db.Float)
    max_clarity_score = db.Column(db.Float)
    clarity_trend = db.Column(db.String(20))  # 'improving', 'declining', 'stable'

    # Algae Trends
    avg_algae_coverage = db.Column(db.Float)
    max_algae_coverage = db.Column(db.Float)
    algae_bloom_days = db.Column(db.Integer)  # Days with algae_severity >= 'moderate'
    dominant_algae_type = db.Column(db.String(50))

    # Color Trends
    most_common_color_category = db.Column(db.String(30))
    avg_rgb_r = db.Column(db.Float)
    avg_rgb_g = db.Column(db.Float)
    avg_rgb_b = db.Column(db.Float)

    # Statistics
    num_observations = db.Column(db.Integer)
    contamination_incident_count = db.Column(db.Integer)  # Visual contamination detections

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = db.relationship('Site', backref='visual_trends', lazy=True)

    def __repr__(self):
        return f'<VisualTrendAnalysis {self.site_id}: {self.year}-{self.month:02d}>'

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'year': self.year,
            'month': self.month,
            'avg_clarity_score': self.avg_clarity_score,
            'clarity_trend': self.clarity_trend,
            'avg_algae_coverage': self.avg_algae_coverage,
            'algae_bloom_days': self.algae_bloom_days,
            'most_common_color_category': self.most_common_color_category,
            'contamination_incident_count': self.contamination_incident_count,
        }
