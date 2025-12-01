"""
Samples Controller - CRUD operations for water samples
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.water_sample import WaterSample
from app.models.site import Site
from datetime import datetime

samples_bp = Blueprint('samples', __name__, url_prefix='/samples')

@samples_bp.route('/')
@login_required
def index():
    """List all samples with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    site_filter = request.args.get('site_id', type=int)
    status_filter = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search_id = request.args.get('search_id', '').strip()
    search_site = request.args.get('search_site', '').strip()

    query = WaterSample.query

    # Apply filters
    if site_filter:
        query = query.filter_by(site_id=site_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_from:
        query = query.filter(WaterSample.collection_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(WaterSample.collection_date <= datetime.strptime(date_to, '%Y-%m-%d').date())

    # Search by Sample ID
    if search_id:
        query = query.filter(WaterSample.sample_id.ilike(f'%{search_id}%'))

    # Search by Site name or code
    if search_site:
        query = query.join(Site).filter(
            db.or_(
                Site.site_name.ilike(f'%{search_site}%'),
                Site.site_code.ilike(f'%{search_site}%')
            )
        )

    samples = query.order_by(WaterSample.collection_date.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    sites = Site.query.filter_by(is_active=True).all()

    return render_template('samples/index.html',
                          samples=samples,
                          sites=sites,
                          site_filter=site_filter,
                          status_filter=status_filter,
                          date_from=date_from,
                          date_to=date_to,
                          search_id=search_id,
                          search_site=search_site)

@samples_bp.route('/<int:sample_id>')
@login_required
def view(sample_id):
    """View sample details"""
    sample = WaterSample.query.get_or_404(sample_id)
    test_results = sample.test_results.all()
    analyses = sample.analyses.all()

    return render_template('samples/view.html',
                          sample=sample,
                          test_results=test_results,
                          analyses=analyses)

@samples_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    """Create new sample"""
    if not current_user.can_edit_samples():
        flash('You do not have permission to create samples', 'error')
        return redirect(url_for('samples.index'))

    if request.method == 'POST':
        site_id = request.form.get('site_id')
        site = Site.query.get_or_404(site_id)

        # Parse collection date
        collection_date = datetime.strptime(request.form.get('collection_date'), '%Y-%m-%d').date()

        # Generate unique sample ID
        sample_id_str = WaterSample.generate_sample_id(site.site_code, collection_date)

        # Create sample
        sample = WaterSample(
            sample_id=sample_id_str,
            site_id=site_id,
            collection_date=collection_date,
            collection_time=datetime.strptime(request.form.get('collection_time'), '%H:%M').time(),
            collected_by_id=current_user.id,
            sub_site_details=request.form.get('sub_site_details'),
            exact_latitude=request.form.get('exact_latitude', type=float),
            exact_longitude=request.form.get('exact_longitude', type=float),
            source_type=request.form.get('source_type'),
            source_depth_meters=request.form.get('source_depth_meters', type=float),
            storage_type=request.form.get('storage_type'),
            storage_material=request.form.get('storage_material'),
            discharge_type=request.form.get('discharge_type'),
            discharge_material=request.form.get('discharge_material'),
            water_source_root=request.form.get('water_source_root'),
            is_recycled=request.form.get('is_recycled') == 'yes',
            source_age_years=request.form.get('source_age_years', type=int),
            pipe_material=request.form.get('pipe_material'),
            pipe_age_years=request.form.get('pipe_age_years', type=int),
            distance_from_source_meters=request.form.get('distance_from_source_meters', type=float),
            weather_condition=request.form.get('weather_condition'),
            rained_recently=request.form.get('rained_recently') == 'yes',
            days_since_rain=request.form.get('days_since_rain', type=int),
            ambient_temperature_celsius=request.form.get('ambient_temperature_celsius', type=float),
            water_appearance=request.form.get('water_appearance'),
            odor_present=request.form.get('odor_present') == 'yes',
            odor_description=request.form.get('odor_description'),
            visible_particles=request.form.get('visible_particles') == 'yes',
            priority=request.form.get('priority', 'normal'),
            collection_notes=request.form.get('collection_notes'),
            special_observations=request.form.get('special_observations')
        )

        db.session.add(sample)
        db.session.commit()

        flash(f'Sample {sample_id_str} created successfully', 'success')
        return redirect(url_for('samples.view', sample_id=sample.id))

    sites = Site.query.filter_by(is_active=True).all()
    return render_template('samples/create.html', sites=sites)

@samples_bp.route('/<int:sample_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(sample_id):
    """Edit existing sample"""
    if not current_user.can_edit_samples():
        flash('You do not have permission to edit samples', 'error')
        return redirect(url_for('samples.index'))

    sample = WaterSample.query.get_or_404(sample_id)

    if request.method == 'POST':
        # Update fields
        sample.sub_site_details = request.form.get('sub_site_details')
        sample.exact_latitude = request.form.get('exact_latitude', type=float)
        sample.exact_longitude = request.form.get('exact_longitude', type=float)
        sample.source_type = request.form.get('source_type')
        sample.source_depth_meters = request.form.get('source_depth_meters', type=float)
        sample.storage_type = request.form.get('storage_type')
        sample.storage_material = request.form.get('storage_material')
        sample.discharge_type = request.form.get('discharge_type')
        sample.discharge_material = request.form.get('discharge_material')
        sample.water_source_root = request.form.get('water_source_root')
        sample.is_recycled = request.form.get('is_recycled') == 'yes'
        sample.source_age_years = request.form.get('source_age_years', type=int)
        sample.pipe_material = request.form.get('pipe_material')
        sample.pipe_age_years = request.form.get('pipe_age_years', type=int)
        sample.distance_from_source_meters = request.form.get('distance_from_source_meters', type=float)
        sample.weather_condition = request.form.get('weather_condition')
        sample.rained_recently = request.form.get('rained_recently') == 'yes'
        sample.days_since_rain = request.form.get('days_since_rain', type=int)
        sample.ambient_temperature_celsius = request.form.get('ambient_temperature_celsius', type=float)
        sample.water_appearance = request.form.get('water_appearance')
        sample.odor_present = request.form.get('odor_present') == 'yes'
        sample.odor_description = request.form.get('odor_description')
        sample.visible_particles = request.form.get('visible_particles') == 'yes'
        sample.priority = request.form.get('priority')
        sample.status = request.form.get('status')
        sample.collection_notes = request.form.get('collection_notes')
        sample.special_observations = request.form.get('special_observations')

        db.session.commit()
        flash(f'Sample {sample.sample_id} updated successfully', 'success')
        return redirect(url_for('samples.view', sample_id=sample.id))

    return render_template('samples/edit.html', sample=sample)

@samples_bp.route('/<int:sample_id>/delete', methods=['POST'])
@login_required
def delete(sample_id):
    """Delete sample (admin only)"""
    if not current_user.is_admin():
        flash('Only administrators can delete samples', 'error')
        return redirect(url_for('samples.index'))

    sample = WaterSample.query.get_or_404(sample_id)
    sample_id_str = sample.sample_id

    db.session.delete(sample)
    db.session.commit()

    flash(f'Sample {sample_id_str} deleted successfully', 'success')
    return redirect(url_for('samples.index'))
