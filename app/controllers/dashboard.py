"""Dashboard routes"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.models import Site, WaterSample, TestResult, Analysis, SensorAlert

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Main dashboard"""
    # Get statistics
    stats = get_dashboard_stats()
    recent_samples = get_recent_samples(5)
    critical_sites = get_critical_sites(5)
    recent_alerts = get_recent_alerts(5)

    return render_template('dashboard/index.html',
                           stats=stats,
                           recent_samples=recent_samples,
                           critical_sites=critical_sites,
                           recent_alerts=recent_alerts)


@dashboard_bp.route('/api/stats')
def api_stats():
    """Dashboard statistics API"""
    return jsonify(get_dashboard_stats())


def get_dashboard_stats():
    """Calculate dashboard statistics"""
    today = datetime.utcnow().date()
    last_30_days = today - timedelta(days=30)

    # Total counts
    total_sites = Site.query.filter_by(is_active=True).count()
    total_samples = WaterSample.query.count()
    samples_30d = WaterSample.query.filter(WaterSample.collection_date >= last_30_days).count()

    # Contamination stats (count distinct samples, not duplicate Analysis records)
    contaminated_30d = db.session.query(func.count(func.distinct(WaterSample.id))).join(Analysis).filter(
        WaterSample.collection_date >= last_30_days,
        Analysis.is_contaminated == True
    ).scalar() or 0

    contamination_rate = (contaminated_30d / samples_30d * 100) if samples_30d > 0 else 0

    # WHO compliance (count distinct samples, not duplicate Analysis records)
    who_compliant = db.session.query(func.count(func.distinct(WaterSample.id))).join(Analysis).filter(
        WaterSample.collection_date >= last_30_days,
        Analysis.is_compliant_who == True
    ).scalar() or 0
    who_rate = (who_compliant / samples_30d * 100) if samples_30d > 0 else 0

    # Site risk distribution
    risk_distribution = {
        'critical': Site.query.filter_by(current_risk_level='critical', is_active=True).count(),
        'high': Site.query.filter_by(current_risk_level='high', is_active=True).count(),
        'medium': Site.query.filter_by(current_risk_level='medium', is_active=True).count(),
        'low': Site.query.filter_by(current_risk_level='low', is_active=True).count()
    }

    # Active alerts
    active_alerts = SensorAlert.query.filter_by(is_active=True, resolved=False).count()

    return {
        'total_sites': total_sites,
        'total_samples': total_samples,
        'samples_30d': samples_30d,
        'contamination_rate': round(contamination_rate, 1),
        'who_compliance_rate': round(who_rate, 1),
        'risk_distribution': risk_distribution,
        'active_alerts': active_alerts
    }


def get_recent_samples(limit=5):
    """Get recent samples with analysis"""
    samples = WaterSample.query.order_by(
        WaterSample.collection_date.desc()
    ).limit(limit).all()

    result = []
    for sample in samples:
        analysis = sample.get_latest_analysis()
        result.append({
            'id': sample.id,
            'sample_id': sample.sample_id,
            'site_name': sample.site.site_name,
            'collection_date': sample.collection_date.isoformat(),
            'status': sample.status,
            'contamination_type': analysis.contamination_type if analysis else None,
            'severity': analysis.severity_level if analysis else None,
            'wqi_score': analysis.wqi_score if analysis else None
        })
    return result


def get_critical_sites(limit=5):
    """Get sites with critical or high risk"""
    sites = Site.query.filter(
        Site.current_risk_level.in_(['critical', 'high']),
        Site.is_active == True
    ).order_by(Site.risk_score.desc()).limit(limit).all()

    return [{
        'id': site.id,
        'site_code': site.site_code,
        'site_name': site.site_name,
        'state': site.state,
        'risk_level': site.current_risk_level,
        'risk_score': site.risk_score,
        'last_tested': site.last_tested.isoformat() if site.last_tested else None
    } for site in sites]


def get_recent_alerts(limit=5):
    """Get recent alerts"""
    alerts = SensorAlert.query.filter_by(is_active=True).order_by(
        SensorAlert.alert_timestamp.desc()
    ).limit(limit).all()

    return [{
        'id': alert.id,
        'site_id': alert.site_id,
        'alert_type': alert.alert_type,
        'severity': alert.severity,
        'parameter': alert.parameter,
        'message': alert.message,
        'timestamp': alert.alert_timestamp.isoformat(),
        'acknowledged': alert.acknowledged
    } for alert in alerts]
