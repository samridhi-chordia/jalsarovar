"""
Interventions Controller
Manages water treatment interventions and effectiveness tracking
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db
from app.models.intervention import Intervention
from app.models.treatment_method import TreatmentMethod
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.services.intervention_analyzer import InterventionAnalyzer


# Create blueprint
interventions_bp = Blueprint('interventions', __name__, url_prefix='/interventions')


# ============================================================================
# INTERVENTIONS MANAGEMENT
# ============================================================================

@interventions_bp.route('/')
@login_required
def list_interventions():
    """List all interventions with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filter options
    status = request.args.get('status')
    site_id = request.args.get('site_id', type=int)
    treatment_method_id = request.args.get('treatment_method_id', type=int)

    query = Intervention.query

    if status:
        query = query.filter_by(status=status)
    if site_id:
        query = query.filter_by(site_id=site_id)
    if treatment_method_id:
        query = query.filter_by(treatment_method_id=treatment_method_id)

    interventions = query.order_by(Intervention.implementation_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    sites = Site.query.order_by(Site.site_name).all()
    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.name).all()
    status_choices = dict(Intervention.get_status_choices())

    # Get summary stats
    analyzer = InterventionAnalyzer()
    summary_stats = analyzer.get_intervention_summary_stats()

    return render_template('interventions/list.html',
                         interventions=interventions,
                         sites=sites,
                         treatment_methods=treatment_methods,
                         status_choices=status_choices,
                         summary_stats=summary_stats,
                         selected_status=status,
                         selected_site=site_id,
                         selected_treatment=treatment_method_id)


@interventions_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_intervention():
    """Create new intervention"""
    if request.method == 'POST':
        try:
            # Parse dates
            planned_date = None
            implementation_date = None
            completion_date = None

            if request.form.get('planned_date'):
                planned_date = datetime.strptime(request.form['planned_date'], '%Y-%m-%d').date()
            if request.form.get('implementation_date'):
                implementation_date = datetime.strptime(request.form['implementation_date'], '%Y-%m-%d').date()
            if request.form.get('completion_date'):
                completion_date = datetime.strptime(request.form['completion_date'], '%Y-%m-%d').date()

            intervention = Intervention(
                site_id=request.form.get('site_id', type=int) or None,
                sample_id=request.form.get('sample_id', type=int) or None,
                treatment_method_id=request.form['treatment_method_id'],
                intervention_type=request.form['intervention_type'],
                title=request.form['title'],
                description=request.form.get('description'),
                planned_date=planned_date,
                implementation_date=implementation_date,
                completion_date=completion_date,
                implemented_by=request.form.get('implemented_by'),
                funding_source=request.form.get('funding_source'),
                cost=request.form.get('cost', type=float),
                status=request.form.get('status', 'planned'),
                created_by_id=current_user.id
            )

            db.session.add(intervention)
            db.session.commit()

            flash(f'Intervention "{intervention.title}" created successfully', 'success')
            return redirect(url_for('interventions.view_intervention', intervention_id=intervention.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating intervention: {str(e)}', 'error')

    # GET - show form
    sites = Site.query.order_by(Site.site_name).all()
    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.name).all()
    intervention_types = dict(Intervention.get_intervention_types())
    status_choices = dict(Intervention.get_status_choices())

    return render_template('interventions/form.html',
                         intervention=None,
                         sites=sites,
                         treatment_methods=treatment_methods,
                         intervention_types=intervention_types,
                         status_choices=status_choices)


@interventions_bp.route('/<int:intervention_id>')
@login_required
def view_intervention(intervention_id):
    """View intervention details with effectiveness analysis"""
    intervention = Intervention.query.get_or_404(intervention_id)

    # Get effectiveness analysis if completed
    analysis = None
    if intervention.status == 'completed' and intervention.sample and intervention.followup_sample:
        analyzer = InterventionAnalyzer()
        analysis = analyzer.analyze_intervention(intervention_id)

    return render_template('interventions/detail.html',
                         intervention=intervention,
                         analysis=analysis)


@interventions_bp.route('/<int:intervention_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_intervention(intervention_id):
    """Edit existing intervention"""
    intervention = Intervention.query.get_or_404(intervention_id)

    if request.method == 'POST':
        try:
            # Parse dates
            if request.form.get('planned_date'):
                intervention.planned_date = datetime.strptime(request.form['planned_date'], '%Y-%m-%d').date()
            if request.form.get('implementation_date'):
                intervention.implementation_date = datetime.strptime(request.form['implementation_date'], '%Y-%m-%d').date()
            if request.form.get('completion_date'):
                intervention.completion_date = datetime.strptime(request.form['completion_date'], '%Y-%m-%d').date()

            intervention.site_id = request.form.get('site_id', type=int) or None
            intervention.sample_id = request.form.get('sample_id', type=int) or None
            intervention.treatment_method_id = request.form['treatment_method_id']
            intervention.intervention_type = request.form['intervention_type']
            intervention.title = request.form['title']
            intervention.description = request.form.get('description')
            intervention.implemented_by = request.form.get('implemented_by')
            intervention.funding_source = request.form.get('funding_source')
            intervention.cost = request.form.get('cost', type=float)
            intervention.status = request.form.get('status')

            # If marking as completed, calculate effectiveness
            if intervention.status == 'completed' and intervention.sample and intervention.followup_sample:
                intervention.calculate_effectiveness()

            db.session.commit()

            flash(f'Intervention "{intervention.title}" updated successfully', 'success')
            return redirect(url_for('interventions.view_intervention', intervention_id=intervention.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating intervention: {str(e)}', 'error')

    # GET - show form
    sites = Site.query.order_by(Site.site_name).all()
    treatment_methods = TreatmentMethod.query.filter_by(is_active=True).order_by(TreatmentMethod.name).all()
    intervention_types = dict(Intervention.get_intervention_types())
    status_choices = dict(Intervention.get_status_choices())

    return render_template('interventions/form.html',
                         intervention=intervention,
                         sites=sites,
                         treatment_methods=treatment_methods,
                         intervention_types=intervention_types,
                         status_choices=status_choices)


@interventions_bp.route('/<int:intervention_id>/delete', methods=['POST'])
@login_required
def delete_intervention(intervention_id):
    """Delete intervention"""
    intervention = Intervention.query.get_or_404(intervention_id)

    try:
        title = intervention.title
        db.session.delete(intervention)
        db.session.commit()

        flash(f'Intervention "{title}" deleted successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting intervention: {str(e)}', 'error')

    return redirect(url_for('interventions.list_interventions'))


# ============================================================================
# EFFECTIVENESS DASHBOARD
# ============================================================================

@interventions_bp.route('/effectiveness')
@login_required
def effectiveness_dashboard():
    """Dashboard showing treatment effectiveness across all interventions"""
    analyzer = InterventionAnalyzer()

    # Get effectiveness by treatment method
    effectiveness_data = analyzer.get_effectiveness_by_treatment_method()

    # Get summary stats
    summary_stats = analyzer.get_intervention_summary_stats()

    return render_template('interventions/effectiveness_dashboard.html',
                         effectiveness_data=effectiveness_data,
                         summary_stats=summary_stats)


@interventions_bp.route('/recommend')
@login_required
def treatment_recommendations():
    """Get treatment recommendations for specific contamination types"""
    contamination_type = request.args.get('contamination_type', 'arsenic')
    budget = request.args.get('budget', type=float)

    analyzer = InterventionAnalyzer()
    recommendations = analyzer.recommend_treatment(contamination_type, budget)

    # Get common contamination types
    contamination_types = [
        'arsenic', 'lead', 'iron', 'nitrate', 'fluoride',
        'bacterial', 'turbidity', 'hardness', 'chloride'
    ]

    return render_template('interventions/recommendations.html',
                         recommendations=recommendations,
                         contamination_types=contamination_types,
                         selected_type=contamination_type,
                         budget=budget)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@interventions_bp.route('/api/<int:intervention_id>/analyze', methods=['GET'])
@login_required
def api_analyze_intervention(intervention_id):
    """API: Get effectiveness analysis for intervention"""
    analyzer = InterventionAnalyzer()
    analysis = analyzer.analyze_intervention(intervention_id)

    return jsonify(analysis)


@interventions_bp.route('/api/recommend', methods=['GET'])
@login_required
def api_recommend_treatment():
    """API: Get treatment recommendations"""
    contamination_type = request.args.get('contamination_type', 'arsenic')
    budget = request.args.get('budget', type=float)

    analyzer = InterventionAnalyzer()
    recommendations = analyzer.recommend_treatment(contamination_type, budget)

    return jsonify(recommendations)


@interventions_bp.route('/api/stats', methods=['GET'])
@login_required
def api_intervention_stats():
    """API: Get intervention summary statistics"""
    analyzer = InterventionAnalyzer()
    stats = analyzer.get_intervention_summary_stats()

    return jsonify(stats)
