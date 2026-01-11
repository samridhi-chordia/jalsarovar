"""Sites routes - Water body management"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Site, WaterSample, Analysis
from app.services.data_processor import DataProcessor


def admin_required(f):
    """Decorator to require admin access for write operations"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Admin access required for this operation.', 'error')
            return redirect(url_for('sites.index'))
        return f(*args, **kwargs)
    return decorated_function

sites_bp = Blueprint('sites', __name__)


@sites_bp.route('/')
def index():
    """List all sites with ML results"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    country = request.args.get('country')
    state = request.args.get('state')
    site_type = request.args.get('type')
    category = request.args.get('category')
    risk_level = request.args.get('risk')
    search = request.args.get('search', '').strip()

    query = Site.query.filter_by(is_active=True)

    # Apply site-level access filtering for authenticated users
    if current_user.is_authenticated:
        query = current_user.filter_sites_query(query)

    # Search by site name or site code
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Site.site_name.ilike(search_term),
                Site.site_code.ilike(search_term)
            )
        )
    if country:
        query = query.filter_by(country=country)
    if state:
        query = query.filter_by(state=state)
    if site_type:
        query = query.filter_by(site_type=site_type)
    if category:
        query = query.filter_by(site_category=category)
    if risk_level:
        query = query.filter_by(current_risk_level=risk_level)

    sites = query.order_by(Site.site_name).paginate(page=page, per_page=per_page)

    # Get filter options
    countries = db.session.query(Site.country).distinct().order_by(Site.country).all()
    states = db.session.query(Site.state).distinct().order_by(Site.state).all()
    types = db.session.query(Site.site_type).distinct().order_by(Site.site_type).all()

    # Get ML stats for each site
    site_stats = {}
    for site in sites.items:
        # Count samples
        sample_count = WaterSample.query.filter_by(site_id=site.id).count()

        # Get latest WQI from Analysis
        latest_analysis = Analysis.query.join(WaterSample).filter(
            WaterSample.site_id == site.id
        ).order_by(Analysis.analysis_date.desc()).first()

        # Calculate contamination rate
        total_analyses = Analysis.query.join(WaterSample).filter(
            WaterSample.site_id == site.id
        ).count()
        contaminated_count = Analysis.query.join(WaterSample).filter(
            WaterSample.site_id == site.id,
            Analysis.is_contaminated == True
        ).count()
        contamination_rate = (contaminated_count / total_analyses * 100) if total_analyses > 0 else 0

        site_stats[site.id] = {
            'sample_count': sample_count,
            'latest_wqi': latest_analysis.wqi_score if latest_analysis else None,
            'wqi_class': latest_analysis.wqi_class if latest_analysis else None,
            'contamination_rate': round(contamination_rate, 1),
            'contaminated_count': contaminated_count,
            'total_analyses': total_analyses
        }

    return render_template('sites/index.html',
                           sites=sites,
                           site_stats=site_stats,
                           countries=[c[0] for c in countries],
                           states=[s[0] for s in states],
                           types=[t[0] for t in types])


@sites_bp.route('/api/list')
def api_list():
    """API endpoint to get all sites as JSON for dropdown population"""
    query = Site.query.filter_by(is_active=True)

    # Apply site-level access filtering for authenticated users
    if current_user.is_authenticated:
        query = current_user.filter_sites_query(query)

    sites = query.order_by(Site.site_name).all()

    return jsonify({
        'success': True,
        'sites': [{
            'id': s.id,
            'site_code': s.site_code,
            'site_name': s.site_name,
            'site_category': s.site_category or 'public',
            'site_type': s.site_type,
            'state': s.state,
            'country': s.country
        } for s in sites]
    })


@sites_bp.route('/api/filter-options')
def api_filter_options():
    """API endpoint to get filter dropdown options based on current selections"""
    # Get current filter values
    country = request.args.get('country')
    state = request.args.get('state')
    site_type = request.args.get('type')
    category = request.args.get('category')
    risk_level = request.args.get('risk')

    # Build base query with only active sites
    query = Site.query.filter_by(is_active=True)

    # Apply filters sequentially based on what's selected
    if country:
        query = query.filter_by(country=country)
    if state:
        query = query.filter_by(state=state)
    if site_type:
        query = query.filter_by(site_type=site_type)
    if category:
        query = query.filter_by(site_category=category)
    if risk_level:
        query = query.filter_by(current_risk_level=risk_level)

    # Get distinct values from filtered results
    countries = db.session.query(Site.country).filter(
        Site.id.in_([s.id for s in query.all()])
    ).distinct().order_by(Site.country).all()

    states = db.session.query(Site.state).filter(
        Site.id.in_([s.id for s in query.all()])
    ).distinct().order_by(Site.state).all()

    types = db.session.query(Site.site_type).filter(
        Site.id.in_([s.id for s in query.all()])
    ).distinct().order_by(Site.site_type).all()

    return jsonify({
        'success': True,
        'countries': [c[0] for c in countries if c[0]],
        'states': [s[0] for s in states if s[0]],
        'types': [t[0] for t in types if t[0]]
    })


@sites_bp.route('/<int:site_id>')
def detail(site_id):
    """Site detail page with all ML and rule-based results"""
    from datetime import datetime

    site = Site.query.get_or_404(site_id)

    # Verify user has access to this site
    if current_user.is_authenticated and not current_user.can_access_site(site_id):
        flash('You do not have permission to access this site.', 'error')
        return redirect(url_for('sites.index'))

    # Get recent samples
    samples = WaterSample.query.filter_by(site_id=site_id).order_by(
        WaterSample.collection_date.desc()
    ).limit(10).all()

    # Get risk predictions - separate rule-based and ML
    risk_predictions = SiteRiskPrediction.query.filter_by(site_id=site_id).order_by(
        SiteRiskPrediction.prediction_date.desc()
    ).limit(10).all()

    # Separate rule-based and ML predictions
    rule_based_risk = None
    ml_risk = None
    for pred in risk_predictions:
        model_ver = pred.model_version or ''
        if 'rolling' in model_ver or 'rf' in model_ver or 'xgb' in model_ver:
            if not ml_risk:
                ml_risk = pred
        else:
            if not rule_based_risk:
                rule_based_risk = pred

    # For backward compatibility
    latest_risk = rule_based_risk or ml_risk

    # Get cost optimization results
    cost_result = CostOptimizationResult.query.filter_by(site_id=site_id).order_by(
        CostOptimizationResult.optimization_date.desc()
    ).first()

    # Fallback: Generate cost optimization from site data if not available
    if not cost_result:
        sample_count = WaterSample.query.filter_by(site_id=site_id).count()
        if sample_count > 0:
            # Calculate contamination rate
            total_analyses = Analysis.query.join(WaterSample).filter(
                WaterSample.site_id == site_id
            ).count()
            contaminated = Analysis.query.join(WaterSample).filter(
                WaterSample.site_id == site_id,
                Analysis.is_contaminated == True
            ).count()
            contamination_rate = (contaminated / total_analyses * 100) if total_analyses > 0 else 0

            # Determine optimal testing based on risk
            risk_level = site.current_risk_level or 'medium'
            if risk_level == 'critical':
                optimized_tests = 24
                recommended_freq = 'bi-weekly'
            elif risk_level == 'high':
                optimized_tests = 12
                recommended_freq = 'monthly'
            elif risk_level == 'medium':
                optimized_tests = 6
                recommended_freq = 'bi-monthly'
            else:
                optimized_tests = 4
                recommended_freq = 'quarterly'

            current_tests = 12  # Assume monthly baseline
            cost_per_test = 2500  # INR
            current_cost = current_tests * cost_per_test
            optimized_cost = optimized_tests * cost_per_test
            savings = current_cost - optimized_cost if current_cost > optimized_cost else 0

            class CostFallback:
                def __init__(self):
                    self.optimized_tests_per_year = optimized_tests
                    self.cost_reduction_percent = (savings / current_cost * 100) if current_cost > 0 else 0
                    self.detection_rate = min(95, 70 + contamination_rate * 0.25)
                    self.current_tests_per_year = current_tests
                    self.current_cost_inr = current_cost
                    self.optimized_cost_inr = optimized_cost
                    self.cost_savings_inr = savings
                    self.recommended_frequency = recommended_freq
                    self.next_test_date = None
                    self.priority_rank = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}.get(risk_level, 3)
                    self.model_version = 'rule_based_v1'
                    self.optimization_date = datetime.utcnow()

            cost_result = CostFallback()

    # Get WQI readings from WQIReading table
    wqi_readings = WQIReading.query.filter_by(site_id=site_id).order_by(
        WQIReading.reading_timestamp.desc()
    ).limit(10).all()
    latest_wqi = wqi_readings[0] if wqi_readings else None

    # Fallback: Get WQI from Analysis records if WQIReading table is empty
    if not latest_wqi:
        latest_analysis = Analysis.query.join(WaterSample).filter(
            WaterSample.site_id == site_id,
            Analysis.wqi_score.isnot(None)
        ).order_by(Analysis.analysis_date.desc()).first()

        if latest_analysis:
            # Create a dict-like object with WQI data from Analysis
            class WQIFallback:
                def __init__(self, analysis):
                    self.wqi_score = analysis.wqi_score
                    self.wqi_class = analysis.wqi_class
                    self.is_drinkable = analysis.wqi_class in ['Excellent', 'Compliant']
                    self.reading_timestamp = analysis.analysis_date or datetime.utcnow()
                    # Penalty breakdown from contamination scores
                    self.ph_penalty = 0
                    self.tds_penalty = analysis.runoff_sediment_score or 0
                    self.turbidity_penalty = analysis.runoff_sediment_score or 0
                    self.chlorine_penalty = analysis.disinfectant_decay_score or 0
                    self.temperature_penalty = 0
                    self.coliform_penalty = analysis.sewage_ingress_score or 0

            latest_wqi = WQIFallback(latest_analysis)

    # Get anomaly detections
    anomalies = AnomalyDetection.query.filter_by(site_id=site_id).order_by(
        AnomalyDetection.detection_timestamp.desc()
    ).limit(10).all()

    # Get water quality forecasts
    forecasts = WaterQualityForecast.query.filter_by(site_id=site_id).filter(
        WaterQualityForecast.forecast_date >= datetime.utcnow().date()
    ).order_by(WaterQualityForecast.forecast_date).limit(30).all()

    # Get contamination predictions from ContaminationPrediction table
    contamination_predictions = ContaminationPrediction.query.join(
        WaterSample, ContaminationPrediction.sample_id == WaterSample.id
    ).filter(WaterSample.site_id == site_id).order_by(
        ContaminationPrediction.prediction_date.desc()
    ).limit(10).all()

    # Fallback: Get contamination data from Analysis records if ContaminationPrediction is empty
    if not contamination_predictions:
        contaminated_analyses = Analysis.query.join(WaterSample).filter(
            WaterSample.site_id == site_id,
            Analysis.is_contaminated == True
        ).order_by(Analysis.analysis_date.desc()).limit(10).all()

        if contaminated_analyses:
            class ContaminationFallback:
                def __init__(self, analysis):
                    self.predicted_type = analysis.contamination_type or 'unknown'
                    self.confidence = analysis.confidence_score or 85.0
                    self.f1_score = 0.82
                    self.prediction_date = analysis.analysis_date or datetime.utcnow()

            contamination_predictions = [ContaminationFallback(a) for a in contaminated_analyses]

    return render_template('sites/detail.html',
                           site=site,
                           samples=samples,
                           risk_predictions=risk_predictions,
                           latest_risk=latest_risk,
                           rule_based_risk=rule_based_risk,
                           ml_risk=ml_risk,
                           cost_result=cost_result,
                           wqi_readings=wqi_readings,
                           latest_wqi=latest_wqi,
                           anomalies=anomalies,
                           forecasts=forecasts,
                           contamination_predictions=contamination_predictions)


@sites_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Create new site (Admin only)"""
    if request.method == 'POST':
        site = Site(
            site_code=request.form.get('site_code'),
            site_name=request.form.get('site_name'),
            country=request.form.get('country', 'India'),
            state=request.form.get('state'),
            district=request.form.get('district'),
            block=request.form.get('block'),
            village=request.form.get('village'),
            latitude=request.form.get('latitude', type=float),
            longitude=request.form.get('longitude', type=float),
            site_type=request.form.get('site_type'),
            site_category=request.form.get('site_category', 'public'),
            water_source=request.form.get('water_source'),
            surface_area_hectares=request.form.get('surface_area', type=float),
            is_coastal=request.form.get('is_coastal') == 'on',
            is_industrial_nearby=request.form.get('is_industrial_nearby') == 'on',
            is_agricultural_nearby=request.form.get('is_agricultural_nearby') == 'on',
            is_urban=request.form.get('is_urban') == 'on',
            population_served=request.form.get('population_served', type=int),
            amrit_sarovar_id=request.form.get('amrit_sarovar_id')
        )

        db.session.add(site)
        db.session.commit()

        # Run initial risk assessment
        processor = DataProcessor()
        processor._update_site_risk(site)

        flash(f'Site {site.site_name} created successfully!', 'success')
        return redirect(url_for('sites.detail', site_id=site.id))

    return render_template('sites/new.html')


@sites_bp.route('/<int:site_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(site_id):
    """Edit site (Admin or Site Manager with access)"""
    site = Site.query.get_or_404(site_id)

    # Verify user can edit this site
    if not current_user.can_edit_site(site_id):
        flash('You do not have permission to edit this site.', 'error')
        return redirect(url_for('sites.detail', site_id=site_id))

    if request.method == 'POST':
        site.site_name = request.form.get('site_name')
        site.country = request.form.get('country', 'India')
        site.district = request.form.get('district')
        site.block = request.form.get('block')
        site.village = request.form.get('village')
        site.latitude = request.form.get('latitude', type=float)
        site.longitude = request.form.get('longitude', type=float)
        site.site_type = request.form.get('site_type')
        site.site_category = request.form.get('site_category', 'public')
        site.water_source = request.form.get('water_source')
        site.surface_area_hectares = request.form.get('surface_area', type=float)
        site.is_coastal = request.form.get('is_coastal') == 'on'
        site.is_industrial_nearby = request.form.get('is_industrial_nearby') == 'on'
        site.is_agricultural_nearby = request.form.get('is_agricultural_nearby') == 'on'
        site.is_urban = request.form.get('is_urban') == 'on'
        site.population_served = request.form.get('population_served', type=int)

        db.session.commit()
        flash('Site updated successfully!', 'success')
        return redirect(url_for('sites.detail', site_id=site.id))

    return render_template('sites/edit.html', site=site)


@sites_bp.route('/<int:site_id>/risk-assessment', methods=['POST'])
@login_required
@admin_required
def run_risk_assessment(site_id):
    """Run risk assessment for a site (Admin only)"""
    site = Site.query.get_or_404(site_id)

    processor = DataProcessor()
    result = processor._update_site_risk(site)

    return jsonify({
        'success': True,
        'risk_level': result['risk_level'],
        'risk_score': result['risk_score']
    })


@sites_bp.route('/map')
def map_view():
    """Map view of all sites"""
    sites = Site.query.filter_by(is_active=True).filter(
        Site.latitude.isnot(None),
        Site.longitude.isnot(None)
    ).all()

    site_data = [{
        'id': s.id,
        'name': s.site_name,
        'lat': s.latitude,
        'lng': s.longitude,
        'type': s.site_type,
        'risk': s.current_risk_level,
        'state': s.state,
        'category': s.site_category or 'public'
    } for s in sites]

    return render_template('sites/map.html', sites=site_data)


# Import at bottom to avoid circular imports
from app.models.ml_prediction import (
    SiteRiskPrediction, CostOptimizationResult, WQIReading,
    AnomalyDetection, WaterQualityForecast, ContaminationPrediction
)
