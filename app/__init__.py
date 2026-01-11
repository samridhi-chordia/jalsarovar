"""
Jal Sarovar Water Quality Management System - Application Factory
Amrit Sarovar Initiative
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
oauth = OAuth()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)


def create_app(config_name='default'):
    """Application factory pattern"""
    from config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    oauth.init_app(app)
    limiter.init_app(app)

    # Configure OAuth providers
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url=app.config.get('GOOGLE_DISCOVERY_URL'),
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.controllers.main import main_bp
    from app.controllers.auth import auth_bp
    from app.controllers.sites import sites_bp
    from app.controllers.samples import samples_bp
    from app.controllers.analysis import analysis_bp
    from app.controllers.ml_api import ml_api_bp
    from app.controllers.admin import admin_bp
    from app.controllers.dashboard import dashboard_bp
    from app.controllers.simulator import simulator_bp
    from app.controllers.poc import poc_bp
    from app.controllers.rolling_poc import rolling_poc_bp
    from app.controllers.rolling_poc_data import rolling_poc_data_bp
    from app.controllers.settings import settings_bp
    from app.controllers.reports import reports_bp
    from app.controllers.wqi import wqi_bp
    from app.controllers.analytics import analytics_bp
    from app.controllers.imports import imports_bp
    from app.controllers.interventions import interventions_bp
    from app.controllers.portfolio import portfolio_bp
    from app.controllers.admin_portfolio import admin_portfolio_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sites_bp, url_prefix='/sites')
    app.register_blueprint(samples_bp, url_prefix='/samples')
    app.register_blueprint(analysis_bp, url_prefix='/analysis')
    app.register_blueprint(ml_api_bp, url_prefix='/api/ml')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(simulator_bp, url_prefix='/simulator')
    app.register_blueprint(poc_bp, url_prefix='/poc')
    app.register_blueprint(rolling_poc_bp, url_prefix='/rolling-poc')
    app.register_blueprint(rolling_poc_data_bp, url_prefix='/rolling-data-ml')
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(wqi_bp)
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(imports_bp, url_prefix='/imports')
    app.register_blueprint(interventions_bp, url_prefix='/interventions')
    app.register_blueprint(portfolio_bp, url_prefix='/samridhi-chordia')
    app.register_blueprint(admin_portfolio_bp, url_prefix='/admin/portfolio')

    # Create upload folder
    import os
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Add visitor tracking middleware
    @app.before_request
    def track_visitor():
        """Track page visits"""
        from flask import request, session
        from app.models.visitor import VisitorStats, Visit
        from flask_login import current_user

        # Skip static files and API endpoints
        if request.endpoint and (request.endpoint.startswith('static') or
                                  request.endpoint.startswith('api.')):
            return

        # Increment total visits
        VisitorStats.increment_visit()

        # Track unique visitors by session
        if 'visitor_id' not in session:
            session['visitor_id'] = os.urandom(16).hex()
            VisitorStats.increment_unique()

        # Log individual visit
        try:
            visit = Visit(
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:500] if request.user_agent else None,
                referer=request.referer[:500] if request.referer else None,
                path=request.path[:500],
                user_id=current_user.id if current_user.is_authenticated else None,
                session_id=session.get('visitor_id')
            )
            db.session.add(visit)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Don't break the request if visitor tracking fails
            pass

    # Make visitor stats available in all templates
    @app.context_processor
    def inject_visitor_stats():
        """Inject visitor statistics into all templates"""
        from app.models.visitor import VisitorStats
        try:
            stats = VisitorStats.get_stats()
            return dict(
                total_visits=stats.total_visits,
                unique_visitors=stats.unique_visitors
            )
        except:
            return dict(total_visits=0, unique_visitors=0)

    # Add number formatting filter
    @app.template_filter('number_format')
    def number_format(value):
        """Format numbers with commas"""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value

    return app
