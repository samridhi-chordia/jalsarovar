"""
Main Controller - Dashboard and primary views
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app.models.analysis import Analysis
from app.models.site import Site
from app.models.user import User
from app.models.residential_site import ResidentialSite, ResidentialMeasurement, ResidentialAlert
from sqlalchemy import func
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics and recent samples"""

    # Overall statistics
    total_samples = WaterSample.query.count()
    total_sites = Site.query.count()
    total_tests = TestResult.query.count()
    total_analyses = Analysis.query.count()

    # Recent samples (last 7 days)
    last_week = datetime.utcnow() - timedelta(days=7)
    recent_samples = WaterSample.query.filter(
        WaterSample.created_at >= last_week
    ).count()

    # Contamination statistics
    contaminated_count = Analysis.query.filter(
        Analysis.contamination_detected == True
    ).count()

    # Compliance statistics
    who_compliant = Analysis.query.filter(
        Analysis.who_compliant == True
    ).count()
    bis_compliant = Analysis.query.filter(
        Analysis.bis_compliant == True
    ).count()

    # Primary causes breakdown
    causes_breakdown = Analysis.query.with_entities(
        Analysis.primary_cause,
        func.count(Analysis.id).label('count')
    ).filter(
        Analysis.primary_cause.isnot(None)
    ).group_by(Analysis.primary_cause).all()

    # Recent samples with their latest status
    recent_sample_list = WaterSample.query.order_by(
        WaterSample.created_at.desc()
    ).limit(10).all()

    # Samples requiring follow-up
    follow_up_samples = Analysis.query.filter(
        Analysis.follow_up_required == True,
        Analysis.follow_up_completed == False
    ).count()

    # Calculate compliance percentages
    total_analyzed = Analysis.query.count()
    who_compliant_percent = int((who_compliant / total_analyzed * 100)) if total_analyzed > 0 else 0
    bis_compliant_percent = int((bis_compliant / total_analyzed * 100)) if total_analyzed > 0 else 0

    # Get pending tests count
    pending_tests = WaterSample.query.filter(
        WaterSample.status == 'collected'
    ).count()

    # Get active sites count
    active_sites = Site.query.filter(
        Site.is_active == True
    ).count()

    # Get recent alerts (contaminated samples)
    recent_alerts = Analysis.query.filter(
        Analysis.contamination_detected == True
    ).order_by(Analysis.analysis_date.desc()).limit(5).all()

    # Calculate average response time (placeholder - would need actual calculation)
    avg_response_time = 24

    # Get tests this month
    first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    tests_this_month = TestResult.query.filter(
        TestResult.created_at >= first_day_of_month
    ).count()

    # ===== RESIDENTIAL MONITORING STATISTICS (NEW) =====
    # Get residential monitoring statistics
    total_residential_sites = ResidentialSite.query.filter_by(is_active=True).count()

    # Get residential measurements in last 7 days
    residential_measurements_week = ResidentialMeasurement.query.filter(
        ResidentialMeasurement.measurement_datetime >= last_week
    ).count()

    # Get active residential alerts
    residential_active_alerts = ResidentialAlert.query.filter_by(resolved=False).count()

    # Get residential sites with data sharing consent (for public health monitoring)
    residential_sites_sharing = ResidentialSite.query.filter_by(
        data_sharing_consent=True,
        is_active=True
    ).count()

    # Calculate average residential water quality index (last 7 days, with consent)
    residential_avg_wqi = None
    if residential_sites_sharing > 0:
        consent_sites = ResidentialSite.query.filter_by(
            data_sharing_consent=True,
            is_active=True
        ).all()
        consent_site_ids = [s.id for s in consent_sites]

        recent_residential_measurements = ResidentialMeasurement.query.filter(
            ResidentialMeasurement.site_id.in_(consent_site_ids),
            ResidentialMeasurement.measurement_datetime >= last_week,
            ResidentialMeasurement.water_quality_index.isnot(None)
        ).all()

        if recent_residential_measurements:
            wqi_values = [m.water_quality_index for m in recent_residential_measurements]
            residential_avg_wqi = round(sum(wqi_values) / len(wqi_values), 1)

    return render_template('main/dashboard.html',
                          # Public water monitoring stats
                          total_samples=total_samples,
                          total_sites=total_sites,
                          total_tests=total_tests,
                          total_analyses=total_analyses,
                          recent_samples=recent_sample_list,
                          contaminated_count=contaminated_count,
                          who_compliant_percent=who_compliant_percent,
                          bis_compliant_percent=bis_compliant_percent,
                          pending_tests=pending_tests,
                          active_sites=active_sites,
                          recent_alerts=recent_alerts,
                          avg_response_time=avg_response_time,
                          tests_this_month=tests_this_month,
                          # Residential monitoring stats (NEW)
                          total_residential_sites=total_residential_sites,
                          residential_measurements_week=residential_measurements_week,
                          residential_active_alerts=residential_active_alerts,
                          residential_sites_sharing=residential_sites_sharing,
                          residential_avg_wqi=residential_avg_wqi)

@main_bp.route('/users')
@login_required
def users():
    """User management - admin only"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    users_list = User.query.all()
    return render_template('main/users.html', users=users_list)

@main_bp.route('/about')
def about():
    """About Jal Sarovar project"""
    return render_template('main/about.html')
