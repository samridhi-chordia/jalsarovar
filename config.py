"""
Jal Sarovar Water Quality Management System - Configuration
Primary Focus: Amrit Sarovar Initiative
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus

# Load .env file
from dotenv import load_dotenv
load_dotenv()


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'jal-sarovar-amrit-sarovar-secret-key-2024')

    # PostgreSQL Database
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'jal_sarovar_prod')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

    # URL-encode password to handle special characters like @
    _encoded_password = quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{_encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Pagination
    ITEMS_PER_PAGE = 25

    # File Uploads
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

    # ML Models Path
    ML_MODELS_PATH = os.environ.get('ML_MODELS_PATH') or \
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ALL_MODELS')

    # Water Quality Standards (WHO/BIS)
    WHO_STANDARDS = {
        'ph': {'min': 6.5, 'max': 8.5},
        'turbidity_ntu': {'max': 5},
        'tds_ppm': {'max': 500},
        'free_chlorine_mg_l': {'min': 0.2, 'max': 5.0},
        'iron_mg_l': {'max': 0.3},
        'fluoride_mg_l': {'max': 1.5},
        'nitrate_mg_l': {'max': 50},
        'coliform_mpn': {'max': 0},
        'e_coli_mpn': {'max': 0},
        'arsenic_mg_l': {'max': 0.01},
        'lead_mg_l': {'max': 0.01},
        'manganese_mg_l': {'max': 0.4}
    }

    BIS_STANDARDS = {
        'ph': {'min': 6.5, 'max': 8.5},
        'turbidity_ntu': {'max': 5},
        'tds_ppm': {'max': 500, 'acceptable': 2000},
        'free_chlorine_mg_l': {'min': 0.2},
        'iron_mg_l': {'max': 0.3},
        'fluoride_mg_l': {'max': 1.0, 'acceptable': 1.5},
        'nitrate_mg_l': {'max': 45},
        'coliform_mpn': {'max': 0},
        'e_coli_mpn': {'max': 0}
    }

    # ==========================================================================
    # USER-CONFIGURABLE SETTINGS (can be overridden via Settings page)
    # ==========================================================================

    # Sampling Configuration
    DEFAULT_SAMPLING_FREQUENCY = 'monthly'  # weekly, bi-weekly, monthly, quarterly
    SAMPLING_FREQUENCIES = {
        'weekly': {'tests_per_year': 52, 'days_between': 7},
        'bi-weekly': {'tests_per_year': 26, 'days_between': 14},
        'monthly': {'tests_per_year': 12, 'days_between': 30},
        'quarterly': {'tests_per_year': 4, 'days_between': 90}
    }

    # CPCB Import Settings
    CPCB_EXCEL_HEADER_ROW = 6  # Row number where headers start (1-indexed)
    CPCB_MIN_SAMPLES_FOR_IMPORT = 10  # Minimum samples required to import a station
    CPCB_MAX_STATIONS_TO_IMPORT = 5  # Maximum stations to import at once

    # ML Model Settings
    ML_MIN_SAMPLES_FOR_TRAINING = 10  # Minimum samples for ML model training
    ML_ANOMALY_THRESHOLD_SIGMA = 3.0  # Standard deviations for anomaly detection
    ML_FORECAST_HORIZON_DAYS = 30  # Days to forecast ahead

    # Risk Assessment Thresholds
    RISK_THRESHOLD_CRITICAL = 70  # Risk score >= this = critical
    RISK_THRESHOLD_HIGH = 50  # Risk score >= this = high
    RISK_THRESHOLD_MEDIUM = 30  # Risk score >= this = medium
    # Below medium threshold = low risk

    # Cost Analysis Settings
    COST_PER_TEST_INR = 500  # Cost per water quality test in INR
    COST_ANALYSIS_BASELINE_FREQUENCY = 'monthly'  # Baseline for cost comparisons

    # Alert Settings
    ALERT_DAYS_BEFORE_SCHEDULED_TEST = 3  # Days before test to send reminder
    ALERT_CONTAMINATION_SCORE_THRESHOLD = 0.7  # Score above which to alert

    # Data Retention
    DATA_RETENTION_YEARS = 10  # Years to keep historical data

    # ==========================================================================
    # OAUTH & EMAIL CONFIGURATION
    # ==========================================================================

    # Google OAuth Settings
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    OAUTHLIB_INSECURE_TRANSPORT = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '0')  # Set to '1' for dev only

    # Email Settings (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Gmail app password or SMTP password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@jalsarovar.com')

    # Token Expiry Settings
    EMAIL_VERIFICATION_EXPIRY_HOURS = 24
    PASSWORD_RESET_EXPIRY_HOURS = 2

    # Application URL (for email links)
    SITE_URL = os.environ.get('SITE_URL', 'https://jalsarovar.com')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/jal_sarovar_test'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
