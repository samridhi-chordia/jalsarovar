"""
Jal Sarovar - Application Factory
Initializes and configures the Flask application
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_name=None):
    """Application factory pattern"""

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app)

    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.samples import samples_bp
    from app.controllers.tests import tests_bp
    from app.controllers.analysis import analysis_bp
    from app.controllers.auth import auth_bp
    from app.controllers.imports import imports_bp
    from app.controllers.interventions import interventions_bp
    from app.controllers.analytics import analytics_bp
    from app.controllers.ml_models import ml_models_bp
    from app.controllers.residential import residential_bp
    from app.controllers.admin import admin_bp
    from app.controllers.voice import voice_bp
    from app.controllers.wqi import wqi_bp
    from app.controllers.risk_prediction import risk_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(samples_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(interventions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ml_models_bp)
    app.register_blueprint(residential_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(wqi_bp)
    app.register_blueprint(risk_bp)

    # Shell context for flask shell command
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, WaterSample, TestResult, Analysis, Site
        from app.models.data_source import DataSource
        from app.models.import_batch import ImportBatch
        from app.models.intervention import Intervention
        from app.models.treatment_method import TreatmentMethod
        from app.models.residential_site import (
            ResidentialSite, ResidentialMeasurement,
            ResidentialAlert, ResidentialSubscription
        )
        return {
            'db': db,
            'User': User,
            'WaterSample': WaterSample,
            'TestResult': TestResult,
            'Analysis': Analysis,
            'Site': Site,
            'DataSource': DataSource,
            'ImportBatch': ImportBatch,
            'Intervention': Intervention,
            'TreatmentMethod': TreatmentMethod,
            'ResidentialSite': ResidentialSite,
            'ResidentialMeasurement': ResidentialMeasurement,
            'ResidentialAlert': ResidentialAlert,
            'ResidentialSubscription': ResidentialSubscription
        }

    return app
