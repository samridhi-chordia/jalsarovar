"""Samples routes - Water sample management"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Site, WaterSample, TestResult, Analysis
from app.services.data_processor import DataProcessor


def admin_required(f):
    """Decorator to require admin access for write operations"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Admin access required for this operation.', 'error')
            return redirect(url_for('samples.index'))
        return f(*args, **kwargs)
    return decorated_function

samples_bp = Blueprint('samples', __name__)


@samples_bp.route('/')
def index():
    """List all samples"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    site_id = request.args.get('site_id', type=int)
    site_category = request.args.get('site_category')
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    country = request.args.get('country')
    state = request.args.get('state')
    site_type = request.args.get('site_type')

    query = WaterSample.query.join(Site)

    # Apply site-level access filtering for authenticated users
    if current_user.is_authenticated:
        accessible = current_user.get_accessible_sites()
        if accessible == 'all':
            pass  # No filtering needed
        elif accessible == 'public':
            query = query.filter(Site.site_category == 'public')
        else:
            # Filter by assigned site IDs
            if accessible:
                query = query.filter(Site.id.in_(accessible))
            else:
                # No assigned sites - return empty query
                query = query.filter(Site.id == -1)

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
    if status:
        query = query.filter(WaterSample.status == status)
    if date_from:
        query = query.filter(WaterSample.collection_date >= date_from)
    if date_to:
        query = query.filter(WaterSample.collection_date <= date_to)

    samples = query.order_by(WaterSample.collection_date.desc()).paginate(
        page=page, per_page=per_page
    )

    # Filter sites list for dropdown too
    sites_query = Site.query.filter_by(is_active=True)
    if current_user.is_authenticated:
        sites_query = current_user.filter_sites_query(sites_query)
    sites = sites_query.order_by(Site.site_name).all()

    # Get filter options
    countries = db.session.query(Site.country).distinct().order_by(Site.country).all()
    states = db.session.query(Site.state).distinct().order_by(Site.state).all()
    types = db.session.query(Site.site_type).distinct().order_by(Site.site_type).all()

    return render_template('samples/index.html',
                         samples=samples,
                         sites=sites,
                         countries=[c[0] for c in countries],
                         states=[s[0] for s in states],
                         types=[t[0] for t in types])


@samples_bp.route('/<int:sample_id>')
def detail(sample_id):
    """Sample detail with test results and analysis"""
    sample = WaterSample.query.get_or_404(sample_id)

    # Verify user has access to this sample's site
    if current_user.is_authenticated and not current_user.can_access_site(sample.site_id):
        flash('You do not have permission to access this sample.', 'error')
        return redirect(url_for('samples.index'))

    test_result = sample.get_latest_test()
    analysis = sample.get_latest_analysis()

    return render_template('samples/detail.html',
                           sample=sample,
                           test_result=test_result,
                           analysis=analysis)


@samples_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create new sample (Admin or users with create permission)"""
    # Check if user has permission to create samples
    if not current_user.has_permission('can_create_samples'):
        flash('You do not have permission to create samples.', 'error')
        return redirect(url_for('samples.index'))

    if request.method == 'POST':
        site_id = request.form.get('site_id', type=int)

        # Verify user can create samples for this site
        if not current_user.can_create_sample_for_site(site_id):
            flash('You do not have permission to create samples for this site.', 'error')
            return redirect(url_for('samples.new'))

        # Generate sample ID
        sample_count = WaterSample.query.count() + 1
        sample_id = f"WS-{datetime.utcnow().strftime('%Y%m%d')}-{sample_count:05d}"

        sample = WaterSample(
            sample_id=sample_id,
            site_id=site_id,
            collection_date=datetime.strptime(request.form.get('collection_date'), '%Y-%m-%d').date(),
            collection_time=datetime.strptime(request.form.get('collection_time'), '%H:%M').time() if request.form.get('collection_time') else None,
            collected_by_id=current_user.id,
            source_point=request.form.get('source_point'),
            depth_meters=request.form.get('depth_meters', type=float),
            weather_condition=request.form.get('weather_condition'),
            rained_recently=request.form.get('rained_recently') == 'on',
            rainfall_mm_24h=request.form.get('rainfall_mm_24h', type=float),
            air_temperature_celsius=request.form.get('air_temperature', type=float),
            apparent_color=request.form.get('apparent_color'),
            odor=request.form.get('odor'),
            visible_algae=request.form.get('visible_algae') == 'on',
            floating_matter=request.form.get('floating_matter') == 'on',
            notes=request.form.get('notes'),
            status='collected'
        )

        db.session.add(sample)
        db.session.commit()

        # Update site last_tested
        site = Site.query.get(sample.site_id)
        site.last_tested = datetime.utcnow()
        db.session.commit()

        flash(f'Sample {sample_id} created successfully!', 'success')

        # Redirect based on permissions
        if current_user.has_permission('can_submit_test_results'):
            return redirect(url_for('samples.add_test_results', sample_id=sample.id))
        else:
            return redirect(url_for('samples.detail', sample_id=sample.id))

    # Filter sites list to only show accessible sites
    sites_query = Site.query.filter_by(is_active=True)
    sites_query = current_user.filter_sites_query(sites_query)
    sites = sites_query.order_by(Site.site_name).all()

    return render_template('samples/new.html', sites=sites)


@samples_bp.route('/<int:sample_id>/test-results', methods=['GET', 'POST'])
@login_required
def add_test_results(sample_id):
    """Add test results to a sample (Admin or Lab Partner)"""
    # Check if user has permission to submit test results
    if not current_user.has_permission('can_submit_test_results'):
        flash('You do not have permission to submit test results.', 'error')
        return redirect(url_for('samples.detail', sample_id=sample_id))

    sample = WaterSample.query.get_or_404(sample_id)

    # Verify user has access to this sample's site
    if not current_user.can_access_site(sample.site_id):
        flash('You do not have permission to access this sample.', 'error')
        return redirect(url_for('samples.index'))

    if request.method == 'POST':
        test_result = TestResult(
            sample_id=sample.id,
            tested_by_id=current_user.id,
            tested_date=datetime.utcnow(),
            lab_name=request.form.get('lab_name'),

            # Physical parameters
            ph=request.form.get('ph', type=float),
            temperature_celsius=request.form.get('temperature_celsius', type=float),
            turbidity_ntu=request.form.get('turbidity_ntu', type=float),
            color_hazen=request.form.get('color_hazen', type=float),
            conductivity_us_cm=request.form.get('conductivity_us_cm', type=float),

            # Chemical parameters
            tds_ppm=request.form.get('tds_ppm', type=float),
            total_hardness_mg_l=request.form.get('total_hardness_mg_l', type=float),
            total_alkalinity_mg_l=request.form.get('total_alkalinity_mg_l', type=float),

            # Disinfection
            free_chlorine_mg_l=request.form.get('free_chlorine_mg_l', type=float),
            total_chlorine_mg_l=request.form.get('total_chlorine_mg_l', type=float),

            # Anions
            chloride_mg_l=request.form.get('chloride_mg_l', type=float),
            fluoride_mg_l=request.form.get('fluoride_mg_l', type=float),
            sulfate_mg_l=request.form.get('sulfate_mg_l', type=float),
            nitrate_mg_l=request.form.get('nitrate_mg_l', type=float),
            nitrite_mg_l=request.form.get('nitrite_mg_l', type=float),

            # Metals
            iron_mg_l=request.form.get('iron_mg_l', type=float),
            manganese_mg_l=request.form.get('manganese_mg_l', type=float),
            copper_mg_l=request.form.get('copper_mg_l', type=float),
            lead_mg_l=request.form.get('lead_mg_l', type=float),
            arsenic_mg_l=request.form.get('arsenic_mg_l', type=float),

            # Nitrogen
            ammonia_mg_l=request.form.get('ammonia_mg_l', type=float),

            # Microbiology
            total_coliform_mpn=request.form.get('total_coliform_mpn', type=float),
            fecal_coliform_mpn=request.form.get('fecal_coliform_mpn', type=float),
            e_coli_mpn=request.form.get('e_coli_mpn', type=float),

            # Organic
            dissolved_oxygen_mg_l=request.form.get('dissolved_oxygen_mg_l', type=float),
            bod_mg_l=request.form.get('bod_mg_l', type=float),

            notes=request.form.get('notes')
        )

        db.session.add(test_result)
        sample.status = 'tested'
        db.session.commit()

        # Run analysis pipeline
        processor = DataProcessor()
        result = processor.process_new_sample(sample.id)

        flash('Test results saved and analysis completed!', 'success')
        return redirect(url_for('samples.detail', sample_id=sample.id))

    return render_template('samples/test_results.html', sample=sample)


@samples_bp.route('/<int:sample_id>/edit-test-results', methods=['GET', 'POST'])
@login_required
def edit_test_results(sample_id):
    """Edit existing test results (Admin or Lab Partner)"""
    # Check if user has permission to submit test results
    if not current_user.has_permission('can_submit_test_results'):
        flash('You do not have permission to edit test results.', 'error')
        return redirect(url_for('samples.detail', sample_id=sample_id))

    sample = WaterSample.query.get_or_404(sample_id)

    # Verify user has access to this sample's site
    if not current_user.can_access_site(sample.site_id):
        flash('You do not have permission to access this sample.', 'error')
        return redirect(url_for('samples.index'))

    # Get existing test result
    test_result = sample.get_latest_test()
    if not test_result:
        flash('No test results found for this sample.', 'error')
        return redirect(url_for('samples.add_test_results', sample_id=sample_id))

    if request.method == 'POST':
        # Update existing test result
        test_result.tested_by_id = current_user.id
        test_result.tested_date = datetime.utcnow()
        test_result.lab_name = request.form.get('lab_name')

        # Physical parameters
        test_result.ph = request.form.get('ph', type=float)
        test_result.temperature_celsius = request.form.get('temperature_celsius', type=float)
        test_result.turbidity_ntu = request.form.get('turbidity_ntu', type=float)
        test_result.color_hazen = request.form.get('color_hazen', type=float)
        test_result.conductivity_us_cm = request.form.get('conductivity_us_cm', type=float)

        # Chemical parameters
        test_result.tds_ppm = request.form.get('tds_ppm', type=float)
        test_result.total_hardness_mg_l = request.form.get('total_hardness_mg_l', type=float)
        test_result.total_alkalinity_mg_l = request.form.get('total_alkalinity_mg_l', type=float)

        # Disinfection
        test_result.free_chlorine_mg_l = request.form.get('free_chlorine_mg_l', type=float)
        test_result.total_chlorine_mg_l = request.form.get('total_chlorine_mg_l', type=float)

        # Anions
        test_result.chloride_mg_l = request.form.get('chloride_mg_l', type=float)
        test_result.fluoride_mg_l = request.form.get('fluoride_mg_l', type=float)
        test_result.sulfate_mg_l = request.form.get('sulfate_mg_l', type=float)
        test_result.nitrate_mg_l = request.form.get('nitrate_mg_l', type=float)
        test_result.nitrite_mg_l = request.form.get('nitrite_mg_l', type=float)

        # Metals
        test_result.iron_mg_l = request.form.get('iron_mg_l', type=float)
        test_result.manganese_mg_l = request.form.get('manganese_mg_l', type=float)
        test_result.copper_mg_l = request.form.get('copper_mg_l', type=float)
        test_result.lead_mg_l = request.form.get('lead_mg_l', type=float)
        test_result.arsenic_mg_l = request.form.get('arsenic_mg_l', type=float)

        # Nitrogen
        test_result.ammonia_mg_l = request.form.get('ammonia_mg_l', type=float)

        # Microbiology
        test_result.total_coliform_mpn = request.form.get('total_coliform_mpn', type=float)
        test_result.fecal_coliform_mpn = request.form.get('fecal_coliform_mpn', type=float)
        test_result.e_coli_mpn = request.form.get('e_coli_mpn', type=float)

        # Organic
        test_result.dissolved_oxygen_mg_l = request.form.get('dissolved_oxygen_mg_l', type=float)
        test_result.bod_mg_l = request.form.get('bod_mg_l', type=float)

        test_result.notes = request.form.get('notes')

        db.session.commit()

        # Re-run analysis pipeline with updated data
        processor = DataProcessor()
        result = processor.process_new_sample(sample.id)

        flash('Test results updated and analysis re-run successfully!', 'success')
        return redirect(url_for('samples.detail', sample_id=sample.id))

    return render_template('samples/edit_test_results.html', sample=sample, test_result=test_result)


@samples_bp.route('/<int:sample_id>/analyze', methods=['POST'])
@login_required
@admin_required
def analyze(sample_id):
    """Re-run analysis for a sample (Admin only)"""
    sample = WaterSample.query.get_or_404(sample_id)

    processor = DataProcessor()
    result = processor.process_new_sample(sample.id)

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 400

    return jsonify({
        'success': True,
        'analysis_id': result.get('analysis_id'),
        'contamination_type': result.get('contamination_type'),
        'severity': result.get('severity')
    })


@samples_bp.route('/api/recent')
@login_required
def api_recent():
    """API: Get recent samples"""
    limit = request.args.get('limit', 10, type=int)
    samples = WaterSample.query.order_by(
        WaterSample.collection_date.desc()
    ).limit(limit).all()

    return jsonify([{
        'id': s.id,
        'sample_id': s.sample_id,
        'site_name': s.site.site_name,
        'collection_date': s.collection_date.isoformat(),
        'status': s.status
    } for s in samples])
