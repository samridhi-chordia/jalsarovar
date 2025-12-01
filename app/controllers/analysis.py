"""
Analysis Controller - View and manage contamination analyses
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.analysis import Analysis
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app.services.contamination_analyzer import ContaminationAnalyzer
from app.services.ml_api_client import MLAPIClient

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')

@analysis_bp.route('/')
@login_required
def index():
    """List all analyses with filtering"""
    page = request.args.get('page', 1, type=int)
    contamination_filter = request.args.get('contamination')
    cause_filter = request.args.get('cause')
    severity_filter = request.args.get('severity')

    query = Analysis.query

    if contamination_filter:
        query = query.filter_by(contamination_detected=(contamination_filter == 'yes'))
    if cause_filter:
        query = query.filter_by(primary_cause=cause_filter)
    if severity_filter:
        query = query.filter_by(severity=severity_filter)

    analyses = query.order_by(Analysis.analysis_date.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    return render_template('analysis/index.html',
                          analyses=analyses,
                          contamination_filter=contamination_filter,
                          cause_filter=cause_filter,
                          severity_filter=severity_filter)

@analysis_bp.route('/<int:analysis_id>')
@login_required
def view(analysis_id):
    """View analysis details"""
    analysis = Analysis.query.get_or_404(analysis_id)
    return render_template('analysis/view.html', analysis=analysis)

@analysis_bp.route('/sample/<int:sample_id>/create', methods=['GET', 'POST'])
@login_required
def create(sample_id):
    """Run analysis on a sample"""
    if not current_user.can_analyze():
        flash('You do not have permission to perform analysis', 'error')
        return redirect(url_for('samples.view', sample_id=sample_id))

    sample = WaterSample.query.get_or_404(sample_id)

    # Get latest test result
    test_result = sample.test_results.order_by(TestResult.test_date.desc()).first()

    if not test_result:
        flash('No test results found for this sample. Please add test results first.', 'error')
        return redirect(url_for('samples.view', sample_id=sample_id))

    if request.method == 'POST':
        analysis_type = request.form.get('analysis_type', 'automated')

        analyzer = ContaminationAnalyzer()

        # Run rule-based analysis
        analysis = analyzer.analyze_sample(sample, test_result)
        analysis.analysis_type = analysis_type
        analysis.analyzed_by_id = current_user.id

        # Run ML analysis if enabled
        if request.form.get('run_ml_analysis') == 'yes':
            ml_client = MLAPIClient()
            ml_result = ml_client.predict_contamination(sample, test_result)

            if ml_result.get('success'):
                analysis.ml_prediction = ml_result.get('prediction')
                analysis.ml_confidence = ml_result.get('confidence')
                analysis.ml_model_version = ml_result.get('model_version')
                analysis.ml_response_data = str(ml_result)
            else:
                analysis.ml_api_error = ml_result.get('error')

        db.session.add(analysis)

        # Update sample status
        sample.status = 'analyzed'
        db.session.commit()

        flash('Analysis completed successfully', 'success')
        return redirect(url_for('analysis.view', analysis_id=analysis.id))

    return render_template('analysis/create.html', sample=sample, test_result=test_result)

@analysis_bp.route('/<int:analysis_id>/review', methods=['GET', 'POST'])
@login_required
def review(analysis_id):
    """Review and approve analysis"""
    if not current_user.can_analyze():
        flash('You do not have permission to review analyses', 'error')
        return redirect(url_for('analysis.view', analysis_id=analysis_id))

    analysis = Analysis.query.get_or_404(analysis_id)

    if request.method == 'POST':
        analysis.status = request.form.get('status')
        analysis.reviewed_by = current_user.full_name or current_user.username
        analysis.review_date = db.func.now()
        analysis.review_notes = request.form.get('review_notes')

        db.session.commit()
        flash('Analysis reviewed successfully', 'success')
        return redirect(url_for('analysis.view', analysis_id=analysis_id))

    return render_template('analysis/review.html', analysis=analysis)

@analysis_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for analysis statistics (for charts)"""
    from sqlalchemy import func

    # Contamination breakdown
    contamination_stats = db.session.query(
        Analysis.contamination_detected,
        func.count(Analysis.id)
    ).group_by(Analysis.contamination_detected).all()

    # Cause breakdown
    cause_stats = db.session.query(
        Analysis.primary_cause,
        func.count(Analysis.id)
    ).filter(Analysis.primary_cause.isnot(None)).group_by(Analysis.primary_cause).all()

    # Severity breakdown
    severity_stats = db.session.query(
        Analysis.severity,
        func.count(Analysis.id)
    ).filter(Analysis.severity.isnot(None)).group_by(Analysis.severity).all()

    return jsonify({
        'contamination': [{'detected': str(c[0]), 'count': c[1]} for c in contamination_stats],
        'causes': [{'cause': c[0], 'count': c[1]} for c in cause_stats],
        'severity': [{'level': s[0], 'count': s[1]} for s in severity_stats]
    })
