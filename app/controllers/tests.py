"""
Test Results Controller - Manage laboratory test data
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.test_result import TestResult
from app.models.water_sample import WaterSample
from app.services.contamination_analyzer import ContaminationAnalyzer
from datetime import datetime

tests_bp = Blueprint('tests', __name__, url_prefix='/tests')

@tests_bp.route('/sample/<int:sample_id>/new', methods=['GET', 'POST'])
@login_required
def create(sample_id):
    """Create test result for a sample"""
    if not current_user.can_edit_samples():
        flash('You do not have permission to create test results', 'error')
        return redirect(url_for('samples.view', sample_id=sample_id))

    sample = WaterSample.query.get_or_404(sample_id)

    if request.method == 'POST':
        test_result = TestResult(
            sample_id=sample.id,
            test_date=datetime.strptime(request.form.get('test_date'), '%Y-%m-%d').date(),
            test_time=datetime.strptime(request.form.get('test_time'), '%H:%M').time(),
            tested_by=request.form.get('tested_by'),
            test_batch_id=request.form.get('test_batch_id'),
            # Physical Parameters
            turbidity_ntu=request.form.get('turbidity_ntu', type=float),
            temperature_celsius=request.form.get('temperature_celsius', type=float),
            color_pcu=request.form.get('color_pcu', type=float),
            odor_intensity=request.form.get('odor_intensity', type=int),
            # Chemical Parameters
            ph_value=request.form.get('ph_value', type=float),
            tds_ppm=request.form.get('tds_ppm', type=float),
            salinity_ppm=request.form.get('salinity_ppm', type=float),
            conductivity_us_cm=request.form.get('conductivity_us_cm', type=float),
            # Chlorine
            free_chlorine_mg_l=request.form.get('free_chlorine_mg_l', type=float),
            total_chlorine_mg_l=request.form.get('total_chlorine_mg_l', type=float),
            chloride_mg_l=request.form.get('chloride_mg_l', type=float),
            # Metals
            iron_mg_l=request.form.get('iron_mg_l', type=float),
            manganese_mg_l=request.form.get('manganese_mg_l', type=float),
            copper_mg_l=request.form.get('copper_mg_l', type=float),
            lead_mg_l=request.form.get('lead_mg_l', type=float),
            arsenic_mg_l=request.form.get('arsenic_mg_l', type=float),
            # Hardness
            total_hardness_mg_l=request.form.get('total_hardness_mg_l', type=float),
            calcium_hardness_mg_l=request.form.get('calcium_hardness_mg_l', type=float),
            magnesium_hardness_mg_l=request.form.get('magnesium_hardness_mg_l', type=float),
            # Nutrients
            nitrate_mg_l=request.form.get('nitrate_mg_l', type=float),
            nitrite_mg_l=request.form.get('nitrite_mg_l', type=float),
            ammonia_mg_l=request.form.get('ammonia_mg_l', type=float),
            phosphate_mg_l=request.form.get('phosphate_mg_l', type=float),
            # Biological
            coliform_status=request.form.get('coliform_status'),
            e_coli_status=request.form.get('e_coli_status'),
            coliform_count_cfu_100ml=request.form.get('coliform_count_cfu_100ml', type=float),
            # Dissolved Oxygen
            dissolved_oxygen_mg_l=request.form.get('dissolved_oxygen_mg_l', type=float),
            bod_mg_l=request.form.get('bod_mg_l', type=float),
            cod_mg_l=request.form.get('cod_mg_l', type=float),
            # Other
            alkalinity_mg_l=request.form.get('alkalinity_mg_l', type=float),
            sulfate_mg_l=request.form.get('sulfate_mg_l', type=float),
            fluoride_mg_l=request.form.get('fluoride_mg_l', type=float),
            # Metadata
            test_method=request.form.get('test_method'),
            lab_equipment_id=request.form.get('lab_equipment_id'),
            test_notes=request.form.get('test_notes'),
            anomalies_observed=request.form.get('anomalies_observed')
        )

        db.session.add(test_result)
        db.session.commit()

        # Update sample status
        sample.status = 'tested'
        db.session.commit()

        # Auto-trigger analysis if requested
        if request.form.get('auto_analyze') == 'yes':
            analyzer = ContaminationAnalyzer()
            analysis = analyzer.analyze_sample(sample, test_result)
            db.session.add(analysis)
            db.session.commit()
            flash('Test result saved and analysis completed', 'success')
            return redirect(url_for('analysis.view', analysis_id=analysis.id))

        flash('Test result saved successfully', 'success')
        return redirect(url_for('samples.view', sample_id=sample.id))

    return render_template('tests/create.html', sample=sample)

@tests_bp.route('/<int:test_id>')
@login_required
def view(test_id):
    """View test result details"""
    test_result = TestResult.query.get_or_404(test_id)
    return render_template('tests/view.html', test_result=test_result)

@tests_bp.route('/<int:test_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(test_id):
    """Edit test result"""
    if not current_user.can_edit_samples():
        flash('You do not have permission to edit test results', 'error')
        return redirect(url_for('tests.view', test_id=test_id))

    test_result = TestResult.query.get_or_404(test_id)

    if request.method == 'POST':
        # Update all fields
        test_result.turbidity_ntu = request.form.get('turbidity_ntu', type=float)
        test_result.temperature_celsius = request.form.get('temperature_celsius', type=float)
        test_result.ph_value = request.form.get('ph_value', type=float)
        test_result.tds_ppm = request.form.get('tds_ppm', type=float)
        test_result.salinity_ppm = request.form.get('salinity_ppm', type=float)
        test_result.free_chlorine_mg_l = request.form.get('free_chlorine_mg_l', type=float)
        test_result.iron_mg_l = request.form.get('iron_mg_l', type=float)
        test_result.coliform_status = request.form.get('coliform_status')
        test_result.test_notes = request.form.get('test_notes')

        db.session.commit()
        flash('Test result updated successfully', 'success')
        return redirect(url_for('tests.view', test_id=test_id))

    return render_template('tests/edit.html', test_result=test_result)
