"""Analysis routes - Contamination analysis and trends"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Site, WaterSample, Analysis
from app.models.ml_prediction import (
    SiteRiskPrediction, ContaminationPrediction, WQIReading,
    AnomalyDetection, WaterQualityForecast, CostOptimizationResult
)

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/')
def index():
    """List all analyses"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    site_id = request.args.get('site_id', type=int)
    site_category = request.args.get('site_category')
    contamination_type = request.args.get('type')
    severity = request.args.get('severity')
    compliant = request.args.get('compliant')
    country = request.args.get('country')
    state = request.args.get('state')
    site_type = request.args.get('site_type')

    query = Analysis.query.join(WaterSample).join(Site)

    # Apply site-level access filtering for authenticated users
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass  # No filtering needed
        elif accessible == 'public':
            query = query.filter(Site.site_category == 'public')
        else:
            if accessible:
                query = query.filter(Site.id.in_(accessible))
            else:
                query = query.filter(Site.id == -1)  # No access

    if country:
        query = query.filter(Site.country == country)
    if site_category:
        query = query.filter(Site.site_category == site_category)
    if state:
        query = query.filter(Site.state == state)
    if site_type:
        query = query.filter(Site.site_type == site_type)
    if site_id:
        query = query.filter(WaterSample.site_id == site_id)
    if contamination_type:
        query = query.filter_by(contamination_type=contamination_type)
    if severity:
        query = query.filter_by(severity_level=severity)
    if compliant == 'who':
        query = query.filter_by(is_compliant_who=True)
    elif compliant == 'bis':
        query = query.filter_by(is_compliant_bis=True)
    elif compliant == 'none':
        query = query.filter(
            Analysis.is_compliant_who == False,
            Analysis.is_compliant_bis == False
        )

    analyses = query.order_by(Analysis.analysis_date.desc()).paginate(
        page=page, per_page=per_page
    )

    # Apply site filtering to sites dropdown
    sites_query = Site.query.filter_by(is_active=True)
    if current_user.is_authenticated:
        sites_query = current_user.filter_sites_query(sites_query)
    sites = sites_query.order_by(Site.site_name).all()

    # Get filter options (also filtered by accessible sites)
    base_query = Site.query.filter_by(is_active=True)
    if current_user.is_authenticated:
        base_query = current_user.filter_sites_query(base_query)

    countries = db.session.query(Site.country).select_from(base_query.subquery()).distinct().order_by(Site.country).all()
    states = db.session.query(Site.state).select_from(base_query.subquery()).distinct().order_by(Site.state).all()
    types = db.session.query(Site.site_type).select_from(base_query.subquery()).distinct().order_by(Site.site_type).all()

    return render_template('analysis/index.html',
                         analyses=analyses,
                         sites=sites,
                         countries=[c[0] for c in countries],
                         states=[s[0] for s in states],
                         types=[t[0] for t in types])


@analysis_bp.route('/<int:analysis_id>')
def detail(analysis_id):
    """Analysis detail page"""
    analysis = Analysis.query.get_or_404(analysis_id)
    sample = analysis.sample
    test_result = analysis.test_result
    site = sample.site

    # Verify user has access to this site
    if current_user.is_authenticated and not current_user.can_access_site(site.id):
        from flask import flash, redirect, url_for
        flash('You do not have permission to access this analysis.', 'error')
        return redirect(url_for('analysis.index'))

    # Get contamination breakdown
    breakdown = analysis.get_contamination_breakdown()

    # Get ML prediction if exists
    ml_prediction = analysis.contamination_predictions.first()

    return render_template('analysis/detail.html',
                           analysis=analysis,
                           sample=sample,
                           test_result=test_result,
                           site=site,
                           breakdown=breakdown,
                           ml_prediction=ml_prediction)


@analysis_bp.route('/trends')
def trends():
    """Comprehensive trends dashboard with all ML model data"""
    days = request.args.get('days', 30, type=int)
    site_id = request.args.get('site_id', type=int)
    site_category = request.args.get('site_category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Calculate cutoff based on custom date range or days parameter
    if date_from and date_to:
        cutoff = datetime.strptime(date_from, '%Y-%m-%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d')
    else:
        cutoff = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()

    # Get list of sites for filter dropdown
    sites_query = Site.query.filter_by(is_active=True)
    if site_category:
        sites_query = sites_query.filter_by(site_category=site_category)
    sites_list = sites_query.order_by(Site.site_name).all()

    # Contamination type distribution
    type_query = db.session.query(
        Analysis.contamination_type,
        func.count(Analysis.id)
    ).filter(
        Analysis.analysis_date >= cutoff,
        Analysis.is_contaminated == True
    )
    if site_id or site_category:
        type_query = type_query.join(WaterSample).join(Site)
        if site_id:
            type_query = type_query.filter(WaterSample.site_id == site_id)
        if site_category:
            type_query = type_query.filter(Site.site_category == site_category)
    type_dist = dict(type_query.group_by(Analysis.contamination_type).all())

    # Severity distribution
    severity_query = db.session.query(
        Analysis.severity_level,
        func.count(Analysis.id)
    ).filter(Analysis.analysis_date >= cutoff)
    if site_id or site_category:
        severity_query = severity_query.join(WaterSample).join(Site)
        if site_id:
            severity_query = severity_query.filter(WaterSample.site_id == site_id)
        if site_category:
            severity_query = severity_query.filter(Site.site_category == site_category)
    severity_dist = dict(severity_query.group_by(Analysis.severity_level).all())

    # Daily contamination trend (use sample collection_date for proper temporal trends)
    daily_query = db.session.query(
        func.date(WaterSample.collection_date).label('date'),
        func.count(Analysis.id).label('total'),
        func.sum(func.cast(Analysis.is_contaminated, db.Integer)).label('contaminated')
    ).join(WaterSample).filter(WaterSample.collection_date >= cutoff)
    if site_id or site_category:
        daily_query = daily_query.join(Site)
        if site_id:
            daily_query = daily_query.filter(WaterSample.site_id == site_id)
        if site_category:
            daily_query = daily_query.filter(Site.site_category == site_category)
    daily_trend = daily_query.group_by(func.date(WaterSample.collection_date)).order_by(
        func.date(WaterSample.collection_date)
    ).all()

    # WQI distribution
    wqi_base = Analysis.query.filter(Analysis.analysis_date >= cutoff)
    if site_id or site_category:
        wqi_base = wqi_base.join(WaterSample).join(Site)
        if site_id:
            wqi_base = wqi_base.filter(WaterSample.site_id == site_id)
        if site_category:
            wqi_base = wqi_base.filter(Site.site_category == site_category)
    wqi_dist = {
        'excellent': wqi_base.filter(Analysis.wqi_score >= 90).count(),
        'compliant': wqi_base.filter(Analysis.wqi_score >= 70, Analysis.wqi_score < 90).count(),
        'warning': wqi_base.filter(Analysis.wqi_score >= 50, Analysis.wqi_score < 70).count(),
        'unsafe': wqi_base.filter(Analysis.wqi_score < 50).count()
    }

    # === ML Model Data ===

    # Risk distribution over time
    risk_query = db.session.query(
        SiteRiskPrediction.risk_level,
        func.count(SiteRiskPrediction.id)
    ).filter(SiteRiskPrediction.prediction_date >= cutoff)
    if site_id or site_category:
        risk_query = risk_query.join(Site)
        if site_id:
            risk_query = risk_query.filter(SiteRiskPrediction.site_id == site_id)
        if site_category:
            risk_query = risk_query.filter(Site.site_category == site_category)
    risk_dist = dict(risk_query.group_by(SiteRiskPrediction.risk_level).all())

    # Risk score trend
    risk_trend_query = db.session.query(
        func.date(SiteRiskPrediction.prediction_date).label('date'),
        func.avg(SiteRiskPrediction.risk_score).label('avg_score')
    ).filter(SiteRiskPrediction.prediction_date >= cutoff)
    if site_id or site_category:
        risk_trend_query = risk_trend_query.join(Site)
        if site_id:
            risk_trend_query = risk_trend_query.filter(SiteRiskPrediction.site_id == site_id)
        if site_category:
            risk_trend_query = risk_trend_query.filter(Site.site_category == site_category)
    risk_trend = risk_trend_query.group_by(func.date(SiteRiskPrediction.prediction_date)).order_by(
        func.date(SiteRiskPrediction.prediction_date)
    ).all()

    # WQI readings trend (use sample collection_date for proper temporal trends)
    wqi_trend_query = db.session.query(
        func.date(WaterSample.collection_date).label('date'),
        func.avg(Analysis.wqi_score).label('avg_wqi')
    ).join(WaterSample).filter(WaterSample.collection_date >= cutoff)
    if site_id or site_category:
        wqi_trend_query = wqi_trend_query.join(Site)
        if site_id:
            wqi_trend_query = wqi_trend_query.filter(WaterSample.site_id == site_id)
        if site_category:
            wqi_trend_query = wqi_trend_query.filter(Site.site_category == site_category)
    wqi_trend = wqi_trend_query.group_by(func.date(WaterSample.collection_date)).order_by(
        func.date(WaterSample.collection_date)
    ).all()

    # Anomaly detection trend
    anomaly_trend_query = db.session.query(
        func.date(AnomalyDetection.detection_timestamp).label('date'),
        func.count(AnomalyDetection.id).label('count')
    ).filter(
        AnomalyDetection.detection_timestamp >= cutoff,
        AnomalyDetection.is_anomaly == True
    )
    if site_id or site_category:
        anomaly_trend_query = anomaly_trend_query.join(Site)
        if site_id:
            anomaly_trend_query = anomaly_trend_query.filter(AnomalyDetection.site_id == site_id)
        if site_category:
            anomaly_trend_query = anomaly_trend_query.filter(Site.site_category == site_category)
    anomaly_trend = anomaly_trend_query.group_by(func.date(AnomalyDetection.detection_timestamp)).order_by(
        func.date(AnomalyDetection.detection_timestamp)
    ).all()

    # Anomaly by type
    anomaly_by_type_query = db.session.query(
        AnomalyDetection.anomaly_type,
        func.count(AnomalyDetection.id)
    ).filter(
        AnomalyDetection.detection_timestamp >= cutoff,
        AnomalyDetection.is_anomaly == True
    )
    if site_id or site_category:
        anomaly_by_type_query = anomaly_by_type_query.join(Site)
        if site_id:
            anomaly_by_type_query = anomaly_by_type_query.filter(AnomalyDetection.site_id == site_id)
        if site_category:
            anomaly_by_type_query = anomaly_by_type_query.filter(Site.site_category == site_category)
    anomaly_by_type = dict(anomaly_by_type_query.group_by(AnomalyDetection.anomaly_type).all())

    # Cost optimization summary
    cost_query = db.session.query(
        func.sum(CostOptimizationResult.current_cost_inr).label('current'),
        func.sum(CostOptimizationResult.optimized_cost_inr).label('optimized'),
        func.sum(CostOptimizationResult.cost_savings_inr).label('savings'),
        func.avg(CostOptimizationResult.detection_rate).label('detection_rate')
    )
    if site_id or site_category:
        cost_query = cost_query.join(Site)
        if site_id:
            cost_query = cost_query.filter(CostOptimizationResult.site_id == site_id)
        if site_category:
            cost_query = cost_query.filter(Site.site_category == site_category)
    cost_summary = cost_query.first()

    # Site-wise performance (top 10 by risk)
    site_perf_query = db.session.query(
        Site.id,
        Site.site_name,
        Site.state,
        Site.current_risk_level,
        Site.risk_score,
        func.count(Analysis.id).label('sample_count')
    ).outerjoin(WaterSample, Site.id == WaterSample.site_id).outerjoin(
        Analysis, WaterSample.id == Analysis.sample_id
    ).filter(Site.is_active == True)
    if site_id:
        site_perf_query = site_perf_query.filter(Site.id == site_id)
    if site_category:
        site_perf_query = site_perf_query.filter(Site.site_category == site_category)
    site_performance = site_perf_query.group_by(
        Site.id, Site.site_name, Site.state, Site.current_risk_level, Site.risk_score
    ).order_by(Site.risk_score.desc()).limit(15).all()

    # Model metrics summary
    model_metrics = {
        'risk_classifier': {
            'total_predictions': SiteRiskPrediction.query.filter(SiteRiskPrediction.prediction_date >= cutoff).count(),
            'accuracy': 87.0
        },
        'contamination_classifier': {
            'total_predictions': ContaminationPrediction.query.filter(ContaminationPrediction.prediction_date >= cutoff).count(),
            'f1_score': 0.82
        },
        'wqi_calculator': {
            'total_readings': WQIReading.query.filter(WQIReading.reading_timestamp >= cutoff).count()
        },
        'anomaly_detector': {
            'total_detections': AnomalyDetection.query.filter(
                AnomalyDetection.detection_timestamp >= cutoff,
                AnomalyDetection.is_anomaly == True
            ).count(),
            'accuracy': 92.0
        },
        'forecaster': {
            'active_forecasts': WaterQualityForecast.query.filter(
                WaterQualityForecast.forecast_date >= datetime.utcnow().date()
            ).count(),
            'r2_score': 0.78
        }
    }

    return render_template('analysis/trends.html',
                           type_distribution=type_dist,
                           severity_distribution=severity_dist,
                           daily_trend=daily_trend,
                           wqi_distribution=wqi_dist,
                           risk_distribution=risk_dist,
                           risk_trend=risk_trend,
                           wqi_trend=wqi_trend,
                           anomaly_trend=anomaly_trend,
                           anomaly_by_type=anomaly_by_type,
                           cost_summary=cost_summary,
                           site_performance=site_performance,
                           model_metrics=model_metrics,
                           sites_list=sites_list,
                           selected_site=site_id,
                           selected_category=site_category,
                           days=days,
                           date_from=date_from,
                           date_to=date_to)


@analysis_bp.route('/api/contamination-stats')
def api_contamination_stats():
    """API: Contamination statistics"""
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Base query with site filtering
    base_query = Analysis.query.join(WaterSample).join(Site)
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass
        elif accessible == 'public':
            base_query = base_query.filter(Site.site_category == 'public')
        else:
            if accessible:
                base_query = base_query.filter(Site.id.in_(accessible))
            else:
                base_query = base_query.filter(Site.id == -1)

    total = base_query.filter(Analysis.analysis_date >= cutoff).count()
    contaminated = base_query.filter(
        Analysis.analysis_date >= cutoff,
        Analysis.is_contaminated == True
    ).count()

    # By type query
    by_type_query = db.session.query(
        Analysis.contamination_type,
        func.count(Analysis.id)
    ).join(WaterSample).join(Site).filter(
        Analysis.analysis_date >= cutoff,
        Analysis.is_contaminated == True
    )

    # Apply same site filtering
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass
        elif accessible == 'public':
            by_type_query = by_type_query.filter(Site.site_category == 'public')
        else:
            if accessible:
                by_type_query = by_type_query.filter(Site.id.in_(accessible))
            else:
                by_type_query = by_type_query.filter(Site.id == -1)

    by_type = by_type_query.group_by(Analysis.contamination_type).all()

    return jsonify({
        'total_samples': total,
        'contaminated': contaminated,
        'contamination_rate': round((contaminated / total * 100) if total > 0 else 0, 1),
        'by_type': dict(by_type)
    })


@analysis_bp.route('/api/site-comparison')
def api_site_comparison():
    """API: Compare contamination across sites"""
    limit = request.args.get('limit', 10, type=int)
    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Sites with highest contamination rates
    query = db.session.query(
        Site.id,
        Site.site_name,
        Site.state,
        func.count(Analysis.id).label('total'),
        func.sum(func.cast(Analysis.is_contaminated, db.Integer)).label('contaminated')
    ).join(WaterSample, Site.id == WaterSample.site_id).join(
        Analysis, WaterSample.id == Analysis.sample_id
    ).filter(
        Analysis.analysis_date >= cutoff
    )

    # Apply site filtering
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass
        elif accessible == 'public':
            query = query.filter(Site.site_category == 'public')
        else:
            if accessible:
                query = query.filter(Site.id.in_(accessible))
            else:
                query = query.filter(Site.id == -1)

    results = query.group_by(Site.id, Site.site_name, Site.state).order_by(
        func.sum(func.cast(Analysis.is_contaminated, db.Integer)).desc()
    ).limit(limit).all()

    return jsonify([{
        'site_id': r.id,
        'site_name': r.site_name,
        'state': r.state,
        'total_samples': r.total,
        'contaminated': r.contaminated or 0,
        'contamination_rate': round((r.contaminated or 0) / r.total * 100, 1) if r.total > 0 else 0
    } for r in results])


@analysis_bp.route('/api/wqi-trends')
def api_wqi_trends():
    """API: WQI trends over time"""
    site_id = request.args.get('site_id', type=int)
    days = request.args.get('days', 90, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.session.query(
        func.date(Analysis.analysis_date),
        func.avg(Analysis.wqi_score)
    ).join(WaterSample).join(Site).filter(Analysis.analysis_date >= cutoff)

    # Apply site filtering
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass
        elif accessible == 'public':
            query = query.filter(Site.site_category == 'public')
        else:
            if accessible:
                query = query.filter(Site.id.in_(accessible))
            else:
                query = query.filter(Site.id == -1)

    if site_id:
        query = query.filter(WaterSample.site_id == site_id)

    results = query.group_by(func.date(Analysis.analysis_date)).order_by(
        func.date(Analysis.analysis_date)
    ).all()

    return jsonify([{
        'date': r[0].isoformat() if r[0] else None,
        'avg_wqi': round(r[1], 1) if r[1] else None
    } for r in results])
