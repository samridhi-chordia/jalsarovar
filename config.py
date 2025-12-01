"""
Jal Sarovar - Configuration Module
Handles all application configuration settings
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""

    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_APP = os.environ.get('FLASK_APP') or 'app.py'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///jalsarovar.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Pagination
    SAMPLES_PER_PAGE = int(os.environ.get('SAMPLES_PER_PAGE', 50))

    # File Upload
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE', 50 * 1024 * 1024))  # 50MB (for large datasets)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'json', 'xml', 'pdf'}  # Data import + PDF reports

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ML Model API
    ML_MODEL_API_URL = os.environ.get('ML_MODEL_API_URL', '')
    ML_MODEL_API_KEY = os.environ.get('ML_MODEL_API_KEY', '')
    ML_MODEL_TIMEOUT = int(os.environ.get('ML_MODEL_TIMEOUT', 30))

    # Email (optional)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Twilio Configuration (Voice, SMS, WhatsApp)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')

    # Voice Agent Feature Flags
    VOICE_ENABLED = os.environ.get('VOICE_ENABLED', 'False') == 'True'
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'False') == 'True'
    WHATSAPP_ENABLED = os.environ.get('WHATSAPP_ENABLED', 'False') == 'True'

    # Voice Agent Settings
    VOICE_CALLBACK_BASE_URL = os.environ.get('VOICE_CALLBACK_BASE_URL', 'http://localhost:5000')
    NOTIFICATION_RETRY_ATTEMPTS = int(os.environ.get('NOTIFICATION_RETRY_ATTEMPTS', 3))
    NOTIFICATION_RETRY_DELAY = int(os.environ.get('NOTIFICATION_RETRY_DELAY', 5))  # seconds

    # Application Settings
    ORGANIZATION_NAME = "Samridhi Lab4All"
    PROJECT_NAME = "WFLOW - Water Quality Testing"
    VERSION = "1.0.0"


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Override with stronger settings
    @staticmethod
    def init_app(app):
        # Log to syslog or file in production
        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/jalsarovar.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Jal Sarovar startup')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
