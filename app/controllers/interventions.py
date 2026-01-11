"""
Interventions Controller
Manages water treatment interventions and effectiveness tracking
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db
from app.models import Intervention, TreatmentMethod, Site, WaterSample
from app.services.intervention_analyzer import InterventionAnalyzer


# Admin required decorator
def admin_required(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


# Create blueprint
interventions_bp = Blueprint('interventions', __name__, url_prefix='/interventions')


# Helper functions
def get_intervention_types():
    """Get available intervention types"""
    return [
        ('treatment', 'Water Treatment'),
        ('cleaning', 'Cleaning/Maintenance'),
        ('repair', 'Infrastructure Repair'),
        ('replacement', 'Equipment Replacement'),
        ('chlorination', 'Chlorination'),
        ('filtration', 'Filtration'),
        ('disinfection', 'UV/Chemical Disinfection'),
        ('other', 'Other')
    ]


def get_status_choices():
    """Get available status choices"""
    return [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified')
    ]


def get_parameter_choices():
    """Get water quality parameter choices"""
    return [
        ('ph', 'pH'),
        ('turbidity', 'Turbidity (NTU)'),
        ('tds', 'TDS (ppm)'),
        ('chlorine', 'Free Chlorine (mg/L)'),
        ('iron', 'Iron (mg/L)'),
        ('coliform', 'Total Coliform'),
        ('fluoride', 'Fluoride (mg/L)'),
        ('nitrate', 'Nitrate (mg/L)'),
        ('arsenic', 'Arsenic (mg/L)'),
        ('other', 'Other')
    ]


def calculate_summary_stats():
    """Calculate intervention summary statistics"""
    total = Intervention.query.count()
    completed = Intervention.query.filter_by(status='completed').count()
    in_progress = Intervention.query.filter_by(status='in_progress').count()
    planned = Intervention.query.filter_by(status='planned').count()

    # Calculate average effectiveness
    completed_interventions = Intervention.query.filter(
        Intervention.status == 'completed',
        Intervention.improvement_percent.isnot(None)
    ).all()

    avg_effectiveness = 0
    if completed_interventions:
        total_improvement = sum(i.improvement_percent for i in completed_interventions if i.improvement_percent)
        avg_effectiveness = total_improvement / len(completed_interventions) if completed_interventions else 0

    # Calculate total cost
    total_cost = db.session.query(db.func.sum(Intervention.actual_cost_inr)).filter(
        Intervention.actual_cost_inr.isnot(None)
    ).scalar() or 0

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'planned': planned,
        'avg_effectiveness': round(avg_effectiveness, 1),
        'total_cost': total_cost
    }


# ============================================================================
# INTERVENTIONS MANAGEMENT
# ============================================================================

@interventions_bp.route('/')
def index():
    """List all interventions with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filter options
    status = request.args.get('status')
    site_id = request.args.get('site_id', type=int)
    site_category = request.args.get('site_category')
    intervention_type = request.args.get('type')
    country = request.args.get('country')
    state = request.args.get('state')
    site_type = request.args.get('site_type')

    from sqlalchemy.orm import joinedload

    query = Intervention.query.join(Site).options(joinedload(Intervention.site))

    # Apply filters in order: Country -> Category -> State -> Site Type -> Site -> Status -> Type
    if country:
        query = query.filter(Site.country == country)
    if site_category:
        query = query.filter(Site.site_category == site_category)
    if state:
        query = query.filter(Site.state == state)
    if site_type:
        query = query.filter(Site.site_type == site_type)
    if site_id:
        query = query.filter(Intervention.site_id == site_id)
    if status:
        query = query.filter(Intervention.status == status)
    if intervention_type:
        query = query.filter(Intervention.intervention_type == intervention_type)

    interventions = query.order_by(Intervention.intervention_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    sites_query = Site.query
    if country:
        sites_query = sites_query.filter_by(country=country)
    if site_category:
        sites_query = sites_query.filter_by(site_category=site_category)
    if state:
        sites_query = sites_query.filter_by(state=state)
    if site_type:
        sites_query = sites_query.filter_by(site_type=site_type)
    sites = sites_query.order_by(Site.site_name).all()

    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.method_name).all()
    status_choices = get_status_choices()
    intervention_types = get_intervention_types()

    # Get summary stats
    summary_stats = calculate_summary_stats()

    # Get distinct filter values
    countries = db.session.query(Site.country).distinct().order_by(Site.country).all()
    states = db.session.query(Site.state).distinct().order_by(Site.state).all()
    types = db.session.query(Site.site_type).distinct().order_by(Site.site_type).all()

    return render_template('interventions/list.html',
                         interventions=interventions,
                         sites=sites,
                         treatment_methods=treatment_methods,
                         status_choices=status_choices,
                         intervention_types=intervention_types,
                         summary_stats=summary_stats,
                         selected_status=status,
                         selected_site=site_id,
                         selected_category=site_category,
                         selected_type=intervention_type,
                         countries=[c[0] for c in countries],
                         states=[s[0] for s in states],
                         types=[t[0] for t in types])


@interventions_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def new_intervention():
    """Create new intervention"""
    if request.method == 'POST':
        try:
            # Parse dates
            intervention_date = None
            completed_date = None
            follow_up_date = None

            if request.form.get('intervention_date'):
                intervention_date = datetime.strptime(request.form['intervention_date'], '%Y-%m-%d').date()
            if request.form.get('completed_date'):
                completed_date = datetime.strptime(request.form['completed_date'], '%Y-%m-%d').date()
            if request.form.get('follow_up_date'):
                follow_up_date = datetime.strptime(request.form['follow_up_date'], '%Y-%m-%d').date()

            intervention = Intervention(
                site_id=request.form.get('site_id', type=int) or None,
                sample_id=request.form.get('sample_id', type=int) or None,
                treatment_method_id=request.form.get('treatment_method_id', type=int) or None,
                intervention_type=request.form.get('intervention_type'),
                intervention_date=intervention_date,
                description=request.form.get('description'),
                implemented_by=request.form.get('implemented_by'),
                contractor=request.form.get('contractor'),
                actual_cost_inr=request.form.get('actual_cost_inr', type=float),
                labor_cost_inr=request.form.get('labor_cost_inr', type=float),
                material_cost_inr=request.form.get('material_cost_inr', type=float),
                parameter_targeted=request.form.get('parameter_targeted'),
                before_value=request.form.get('before_value', type=float),
                after_value=request.form.get('after_value', type=float),
                effectiveness_rating=request.form.get('effectiveness_rating', type=int),
                follow_up_required=request.form.get('follow_up_required') == 'on',
                follow_up_date=follow_up_date,
                status=request.form.get('status', 'planned'),
                completed_date=completed_date,
                notes=request.form.get('notes'),
                created_by_id=current_user.id
            )

            # Calculate improvement if before/after values exist
            if intervention.before_value and intervention.after_value:
                improvement = intervention.calculate_effectiveness()
                if improvement:
                    intervention.improvement_percent = improvement

            db.session.add(intervention)
            db.session.commit()

            flash('Intervention created successfully', 'success')
            return redirect(url_for('interventions.view_intervention', intervention_id=intervention.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating intervention: {str(e)}', 'error')

    # GET - show form
    sites = Site.query.order_by(Site.site_name).all()
    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.method_name).all()
    intervention_types = get_intervention_types()
    status_choices = get_status_choices()
    parameter_choices = get_parameter_choices()

    # Get samples for dropdown (recent samples)
    samples = WaterSample.query.order_by(WaterSample.collection_date.desc()).limit(100).all()

    return render_template('interventions/form.html',
                         intervention=None,
                         sites=sites,
                         samples=samples,
                         treatment_methods=treatment_methods,
                         intervention_types=intervention_types,
                         status_choices=status_choices,
                         parameter_choices=parameter_choices)


@interventions_bp.route('/<int:intervention_id>')
def view_intervention(intervention_id):
    """View intervention details"""
    intervention = Intervention.query.get_or_404(intervention_id)

    return render_template('interventions/detail.html',
                         intervention=intervention)


@interventions_bp.route('/<int:intervention_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_intervention(intervention_id):
    """Edit existing intervention"""
    intervention = Intervention.query.get_or_404(intervention_id)

    if request.method == 'POST':
        try:
            # Parse dates
            if request.form.get('intervention_date'):
                intervention.intervention_date = datetime.strptime(request.form['intervention_date'], '%Y-%m-%d').date()
            if request.form.get('completed_date'):
                intervention.completed_date = datetime.strptime(request.form['completed_date'], '%Y-%m-%d').date()
            if request.form.get('follow_up_date'):
                intervention.follow_up_date = datetime.strptime(request.form['follow_up_date'], '%Y-%m-%d').date()

            intervention.site_id = request.form.get('site_id', type=int) or None
            intervention.sample_id = request.form.get('sample_id', type=int) or None
            intervention.treatment_method_id = request.form.get('treatment_method_id', type=int) or None
            intervention.intervention_type = request.form.get('intervention_type')
            intervention.description = request.form.get('description')
            intervention.implemented_by = request.form.get('implemented_by')
            intervention.contractor = request.form.get('contractor')
            intervention.actual_cost_inr = request.form.get('actual_cost_inr', type=float)
            intervention.labor_cost_inr = request.form.get('labor_cost_inr', type=float)
            intervention.material_cost_inr = request.form.get('material_cost_inr', type=float)
            intervention.parameter_targeted = request.form.get('parameter_targeted')
            intervention.before_value = request.form.get('before_value', type=float)
            intervention.after_value = request.form.get('after_value', type=float)
            intervention.effectiveness_rating = request.form.get('effectiveness_rating', type=int)
            intervention.follow_up_required = request.form.get('follow_up_required') == 'on'
            intervention.status = request.form.get('status')
            intervention.notes = request.form.get('notes')

            # Calculate improvement if before/after values exist
            if intervention.before_value and intervention.after_value:
                improvement = intervention.calculate_effectiveness()
                if improvement:
                    intervention.improvement_percent = improvement

            db.session.commit()

            flash('Intervention updated successfully', 'success')
            return redirect(url_for('interventions.view_intervention', intervention_id=intervention.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating intervention: {str(e)}', 'error')

    # GET - show form
    sites = Site.query.order_by(Site.site_name).all()
    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.method_name).all()
    intervention_types = get_intervention_types()
    status_choices = get_status_choices()
    parameter_choices = get_parameter_choices()
    samples = WaterSample.query.order_by(WaterSample.collection_date.desc()).limit(100).all()

    return render_template('interventions/form.html',
                         intervention=intervention,
                         sites=sites,
                         samples=samples,
                         treatment_methods=treatment_methods,
                         intervention_types=intervention_types,
                         status_choices=status_choices,
                         parameter_choices=parameter_choices)


@interventions_bp.route('/<int:intervention_id>/delete', methods=['POST'])
@admin_required
def delete_intervention(intervention_id):
    """Delete intervention"""
    intervention = Intervention.query.get_or_404(intervention_id)

    try:
        db.session.delete(intervention)
        db.session.commit()

        flash('Intervention deleted successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting intervention: {str(e)}', 'error')

    return redirect(url_for('interventions.index'))


# ============================================================================
# EFFECTIVENESS DASHBOARD
# ============================================================================

@interventions_bp.route('/effectiveness')
def effectiveness_dashboard():
    """Dashboard showing treatment effectiveness across all interventions"""

    # Get completed interventions with improvement data
    completed_interventions = Intervention.query.filter(
        Intervention.status == 'completed',
        Intervention.improvement_percent.isnot(None)
    ).all()

    # Group by intervention type
    effectiveness_by_type = {}
    for intervention in completed_interventions:
        itype = intervention.intervention_type or 'unknown'
        if itype not in effectiveness_by_type:
            effectiveness_by_type[itype] = {'count': 0, 'total_improvement': 0, 'total_cost': 0}
        effectiveness_by_type[itype]['count'] += 1
        effectiveness_by_type[itype]['total_improvement'] += intervention.improvement_percent or 0
        effectiveness_by_type[itype]['total_cost'] += intervention.actual_cost_inr or 0

    # Calculate averages
    for itype in effectiveness_by_type:
        count = effectiveness_by_type[itype]['count']
        effectiveness_by_type[itype]['avg_improvement'] = round(
            effectiveness_by_type[itype]['total_improvement'] / count, 1
        ) if count > 0 else 0
        effectiveness_by_type[itype]['avg_cost'] = round(
            effectiveness_by_type[itype]['total_cost'] / count, 0
        ) if count > 0 else 0

    # Group by treatment method
    effectiveness_by_method = {}
    for intervention in completed_interventions:
        if intervention.treatment_method:
            method_name = intervention.treatment_method.method_name
            if method_name not in effectiveness_by_method:
                effectiveness_by_method[method_name] = {'count': 0, 'total_improvement': 0}
            effectiveness_by_method[method_name]['count'] += 1
            effectiveness_by_method[method_name]['total_improvement'] += intervention.improvement_percent or 0

    for method in effectiveness_by_method:
        count = effectiveness_by_method[method]['count']
        effectiveness_by_method[method]['avg_improvement'] = round(
            effectiveness_by_method[method]['total_improvement'] / count, 1
        ) if count > 0 else 0

    # Get summary stats
    summary_stats = calculate_summary_stats()

    # Recent interventions
    recent_interventions = Intervention.query.filter_by(status='completed').order_by(
        Intervention.completed_date.desc()
    ).limit(10).all()

    return render_template('interventions/effectiveness.html',
                         effectiveness_by_type=effectiveness_by_type,
                         effectiveness_by_method=effectiveness_by_method,
                         summary_stats=summary_stats,
                         recent_interventions=recent_interventions,
                         intervention_types=dict(get_intervention_types()))


# ============================================================================
# TREATMENT METHODS MANAGEMENT
# ============================================================================

@interventions_bp.route('/methods')
def list_methods():
    """List all treatment methods"""
    methods = TreatmentMethod.query.order_by(TreatmentMethod.method_name).all()

    return render_template('interventions/methods_list.html', methods=methods)


@interventions_bp.route('/methods/new', methods=['GET', 'POST'])
@admin_required
def new_method():
    """Create new treatment method"""
    if request.method == 'POST':
        try:
            method = TreatmentMethod(
                method_name=request.form['method_name'],
                method_code=request.form.get('method_code'),
                description=request.form.get('description'),
                estimated_cost_min_inr=request.form.get('estimated_cost_min_inr', type=float),
                estimated_cost_max_inr=request.form.get('estimated_cost_max_inr', type=float),
                cost_per_kl=request.form.get('cost_per_kl', type=float),
                average_effectiveness_percent=request.form.get('average_effectiveness_percent', type=float),
                time_to_effect_days=request.form.get('time_to_effect_days', type=int),
                duration_effectiveness_months=request.form.get('duration_effectiveness_months', type=int),
                implementation_time_days=request.form.get('implementation_time_days', type=int),
                requires_specialist=request.form.get('requires_specialist') == 'on',
                requires_equipment=request.form.get('requires_equipment') == 'on',
                equipment_list=request.form.get('equipment_list'),
                is_active=request.form.get('is_active', 'on') == 'on'
            )

            db.session.add(method)
            db.session.commit()

            flash(f'Treatment method "{method.method_name}" created successfully', 'success')
            return redirect(url_for('interventions.list_methods'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating treatment method: {str(e)}', 'error')

    return render_template('interventions/method_form.html', method=None)


@interventions_bp.route('/methods/<int:method_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_method(method_id):
    """Edit treatment method"""
    method = TreatmentMethod.query.get_or_404(method_id)

    if request.method == 'POST':
        try:
            method.method_name = request.form['method_name']
            method.method_code = request.form.get('method_code')
            method.description = request.form.get('description')
            method.estimated_cost_min_inr = request.form.get('estimated_cost_min_inr', type=float)
            method.estimated_cost_max_inr = request.form.get('estimated_cost_max_inr', type=float)
            method.cost_per_kl = request.form.get('cost_per_kl', type=float)
            method.average_effectiveness_percent = request.form.get('average_effectiveness_percent', type=float)
            method.time_to_effect_days = request.form.get('time_to_effect_days', type=int)
            method.duration_effectiveness_months = request.form.get('duration_effectiveness_months', type=int)
            method.implementation_time_days = request.form.get('implementation_time_days', type=int)
            method.requires_specialist = request.form.get('requires_specialist') == 'on'
            method.requires_equipment = request.form.get('requires_equipment') == 'on'
            method.equipment_list = request.form.get('equipment_list')
            method.is_active = request.form.get('is_active') == 'on'

            db.session.commit()

            flash(f'Treatment method "{method.method_name}" updated successfully', 'success')
            return redirect(url_for('interventions.list_methods'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating treatment method: {str(e)}', 'error')

    return render_template('interventions/method_form.html', method=method)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@interventions_bp.route('/api/stats')
def api_intervention_stats():
    """API: Get intervention summary statistics"""
    stats = calculate_summary_stats()
    return jsonify(stats)


@interventions_bp.route('/api/site/<int:site_id>/interventions')
def api_site_interventions(site_id):
    """API: Get interventions for a specific site"""
    interventions = Intervention.query.filter_by(site_id=site_id).order_by(
        Intervention.intervention_date.desc()
    ).all()

    return jsonify([{
        'id': i.id,
        'type': i.intervention_type,
        'date': i.intervention_date.isoformat() if i.intervention_date else None,
        'status': i.status,
        'improvement': i.improvement_percent,
        'cost': i.actual_cost_inr
    } for i in interventions])


# ============================================================================
# TREATMENT RECOMMENDATIONS
# ============================================================================

@interventions_bp.route('/recommend')
def treatment_recommendations():
    """Get treatment recommendations based on contamination type"""
    contamination_type = request.args.get('contamination_type', 'physical')
    budget_inr = request.args.get('budget', type=float)

    analyzer = InterventionAnalyzer()
    recommendations = analyzer.recommend_treatment(contamination_type, budget_inr)

    # Get available contamination types
    contamination_types = [
        ('physical', 'Physical Contamination (Sediment, Turbidity)'),
        ('bacterial', 'Bacterial Contamination'),
        ('chemical', 'Chemical Contamination'),
        ('runoff', 'Runoff/Sediment'),
        ('sewage', 'Sewage Ingress'),
        ('salt', 'Salt/Salinity Intrusion'),
        ('corrosion', 'Pipe Corrosion'),
        ('decay', 'Disinfectant Decay')
    ]

    # Get method effectiveness stats
    method_stats = analyzer.get_effectiveness_by_treatment_method()

    return render_template('interventions/recommendations.html',
                         recommendations=recommendations,
                         contamination_types=contamination_types,
                         selected_type=contamination_type,
                         budget=budget_inr,
                         method_stats=method_stats)


@interventions_bp.route('/api/<int:intervention_id>/analyze')
def api_analyze_intervention(intervention_id):
    """API: Analyze a specific intervention's effectiveness"""
    analyzer = InterventionAnalyzer()
    analysis = analyzer.analyze_intervention(intervention_id)
    return jsonify(analysis)


@interventions_bp.route('/api/recommend')
def api_recommend_treatment():
    """API: Get treatment recommendations"""
    contamination_type = request.args.get('contamination_type', 'physical')
    budget_inr = request.args.get('budget', type=float)

    analyzer = InterventionAnalyzer()
    recommendations = analyzer.recommend_treatment(contamination_type, budget_inr)
    return jsonify(recommendations)


@interventions_bp.route('/api/summary')
def api_summary_stats():
    """API: Get comprehensive intervention summary statistics"""
    analyzer = InterventionAnalyzer()
    stats = analyzer.get_intervention_summary_stats()
    return jsonify(stats)


@interventions_bp.route('/api/method-effectiveness')
def api_method_effectiveness():
    """API: Get effectiveness by treatment method"""
    analyzer = InterventionAnalyzer()
    effectiveness = analyzer.get_effectiveness_by_treatment_method()
    return jsonify(effectiveness)


@interventions_bp.route('/api/<int:intervention_id>/roi')
def api_calculate_roi(intervention_id):
    """API: Calculate ROI for a specific intervention"""
    analyzer = InterventionAnalyzer()
    roi = analyzer.calculate_roi(intervention_id)
    if roi is None:
        return jsonify({'error': 'ROI cannot be calculated for this intervention'}), 400
    return jsonify(roi)


@interventions_bp.route('/api/parameter/<parameter>/stats')
def api_parameter_stats(parameter):
    """API: Get intervention statistics for a specific parameter"""
    analyzer = InterventionAnalyzer()
    stats = analyzer.get_parameter_intervention_stats(parameter)
    return jsonify(stats)


@interventions_bp.route('/api/sample/<int:sample_id>/check-contamination')
def api_check_sample_contamination(sample_id):
    """API: Check a sample for contamination and suggest interventions"""
    analyzer = InterventionAnalyzer()
    result = analyzer.suggest_interventions_for_sample(sample_id)
    return jsonify(result)


@interventions_bp.route('/api/batch/<int:batch_id>/check-all')
@login_required
def api_check_batch_contamination(batch_id):
    """
    API: Check all samples from an import batch for contamination.
    Returns list of samples needing intervention.
    """
    from app.models.water_sample import WaterSample

    # Get samples from this batch (samples have collected_by like "Import Batch #X")
    samples = WaterSample.query.filter(
        WaterSample.collected_by.like(f'Import Batch #{batch_id}%')
    ).all()

    analyzer = InterventionAnalyzer()
    results = {
        'batch_id': batch_id,
        'samples_checked': len(samples),
        'samples_needing_intervention': [],
        'total_issues': 0
    }

    for sample in samples:
        check = analyzer.suggest_interventions_for_sample(sample.id)
        if check.get('needs_intervention'):
            results['samples_needing_intervention'].append({
                'sample_id': sample.id,
                'site_id': sample.site_id,
                'site_name': sample.site.site_name if sample.site else 'Unknown',
                'collection_date': sample.collection_date.isoformat() if sample.collection_date else None,
                'issues': check.get('contamination', {}).get('issues', []),
                'suggested_treatments': check.get('suggested_treatments', [])[:3]
            })
            results['total_issues'] += len(check.get('contamination', {}).get('issues', []))

    return jsonify(results)
