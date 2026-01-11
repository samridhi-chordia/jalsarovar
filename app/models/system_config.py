"""System Configuration model for user-overridable settings"""
from datetime import datetime
from flask import current_app
from app import db
import json


class SystemConfig(db.Model):
    """Key-value store for system configuration settings.

    Allows users to override default config values from config.py.
    Values are stored as JSON strings to support various data types.
    """
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)  # JSON-encoded value
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    category = db.Column(db.String(50), default='general')  # For grouping in UI
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationship
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def get_value(self):
        """Get the typed value from JSON storage"""
        try:
            raw = json.loads(self.value)
            if self.value_type == 'int':
                return int(raw)
            elif self.value_type == 'float':
                return float(raw)
            elif self.value_type == 'bool':
                return bool(raw)
            elif self.value_type == 'json':
                return raw  # Already parsed
            return str(raw)
        except (json.JSONDecodeError, ValueError):
            return self.value

    def set_value(self, value):
        """Set value with proper JSON encoding"""
        self.value = json.dumps(value)

    @staticmethod
    def get(key, default=None):
        """Get a config value by key, with fallback to default"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            return config.get_value()

        # Fall back to Flask config if available
        if default is None and hasattr(current_app, 'config'):
            return current_app.config.get(key, default)
        return default

    @staticmethod
    def set(key, value, value_type='string', category='general', description=None, user_id=None):
        """Set a config value, creating or updating as needed"""
        config = SystemConfig.query.filter_by(key=key).first()
        if not config:
            config = SystemConfig(
                key=key,
                value_type=value_type,
                category=category,
                description=description
            )
            db.session.add(config)

        config.set_value(value)
        config.updated_by_id = user_id
        db.session.commit()
        return config

    @staticmethod
    def get_all_by_category(category=None):
        """Get all config values, optionally filtered by category"""
        query = SystemConfig.query
        if category:
            query = query.filter_by(category=category)
        return query.order_by(SystemConfig.category, SystemConfig.key).all()

    @staticmethod
    def get_effective_config():
        """Get all effective config values (user overrides + defaults)"""
        # Start with defaults from config.py
        defaults = CONFIGURABLE_SETTINGS.copy()

        # Override with database values
        db_configs = SystemConfig.query.all()
        for config in db_configs:
            if config.key in defaults:
                defaults[config.key]['value'] = config.get_value()
                defaults[config.key]['is_default'] = False

        return defaults

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'


# Define all configurable settings with metadata
CONFIGURABLE_SETTINGS = {
    # Sampling Configuration
    'DEFAULT_SAMPLING_FREQUENCY': {
        'value': 'monthly',
        'value_type': 'string',
        'category': 'sampling',
        'description': 'Default sampling frequency for new sites',
        'options': ['weekly', 'bi-weekly', 'monthly', 'quarterly'],
        'is_default': True
    },

    # CPCB Import Settings
    'CPCB_EXCEL_HEADER_ROW': {
        'value': 6,
        'value_type': 'int',
        'category': 'import',
        'description': 'Row number where Excel headers start (1-indexed)',
        'min': 1,
        'max': 20,
        'is_default': True
    },
    'CPCB_MIN_SAMPLES_FOR_IMPORT': {
        'value': 10,
        'value_type': 'int',
        'category': 'import',
        'description': 'Minimum samples required to import a station',
        'min': 1,
        'max': 100,
        'is_default': True
    },
    'CPCB_MAX_STATIONS_TO_IMPORT': {
        'value': 5,
        'value_type': 'int',
        'category': 'import',
        'description': 'Maximum stations to import at once',
        'min': 1,
        'max': 50,
        'is_default': True
    },

    # ML Model Settings
    'ML_MIN_SAMPLES_FOR_TRAINING': {
        'value': 10,
        'value_type': 'int',
        'category': 'ml',
        'description': 'Minimum samples needed for ML model training',
        'min': 5,
        'max': 100,
        'is_default': True
    },
    'ML_ANOMALY_THRESHOLD_SIGMA': {
        'value': 3.0,
        'value_type': 'float',
        'category': 'ml',
        'description': 'Standard deviations for anomaly detection threshold',
        'min': 1.0,
        'max': 5.0,
        'is_default': True
    },
    'ML_FORECAST_HORIZON_DAYS': {
        'value': 30,
        'value_type': 'int',
        'category': 'ml',
        'description': 'Number of days to forecast ahead',
        'min': 7,
        'max': 90,
        'is_default': True
    },

    # Risk Assessment Thresholds
    'RISK_THRESHOLD_CRITICAL': {
        'value': 70,
        'value_type': 'int',
        'category': 'risk',
        'description': 'Risk score threshold for critical level',
        'min': 50,
        'max': 95,
        'is_default': True
    },
    'RISK_THRESHOLD_HIGH': {
        'value': 50,
        'value_type': 'int',
        'category': 'risk',
        'description': 'Risk score threshold for high level',
        'min': 30,
        'max': 70,
        'is_default': True
    },
    'RISK_THRESHOLD_MEDIUM': {
        'value': 30,
        'value_type': 'int',
        'category': 'risk',
        'description': 'Risk score threshold for medium level',
        'min': 10,
        'max': 50,
        'is_default': True
    },

    # Cost Analysis Settings
    'COST_PER_TEST_INR': {
        'value': 500,
        'value_type': 'int',
        'category': 'cost',
        'description': 'Cost per water quality test in INR',
        'min': 100,
        'max': 5000,
        'is_default': True
    },

    # Alert Settings
    'ALERT_DAYS_BEFORE_SCHEDULED_TEST': {
        'value': 3,
        'value_type': 'int',
        'category': 'alerts',
        'description': 'Days before scheduled test to send reminder',
        'min': 1,
        'max': 14,
        'is_default': True
    },
    'ALERT_CONTAMINATION_SCORE_THRESHOLD': {
        'value': 0.7,
        'value_type': 'float',
        'category': 'alerts',
        'description': 'Contamination score above which to generate alert',
        'min': 0.3,
        'max': 1.0,
        'is_default': True
    },

    # Data Retention
    'DATA_RETENTION_YEARS': {
        'value': 10,
        'value_type': 'int',
        'category': 'data',
        'description': 'Years to keep historical data',
        'min': 1,
        'max': 50,
        'is_default': True
    }
}


# Category labels for UI
CONFIG_CATEGORIES = {
    'sampling': {'label': 'Sampling Settings', 'icon': 'droplet', 'order': 1},
    'import': {'label': 'Data Import', 'icon': 'upload', 'order': 2},
    'ml': {'label': 'ML & Analytics', 'icon': 'cpu', 'order': 3},
    'risk': {'label': 'Risk Thresholds', 'icon': 'shield-exclamation', 'order': 4},
    'cost': {'label': 'Cost Analysis', 'icon': 'currency-rupee', 'order': 5},
    'alerts': {'label': 'Alerts & Notifications', 'icon': 'bell', 'order': 6},
    'data': {'label': 'Data Management', 'icon': 'database', 'order': 7}
}
