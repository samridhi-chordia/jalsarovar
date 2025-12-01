"""
Risk Prediction Controller
API endpoints for site risk and contamination prediction using ML models
"""
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from app import db
from app.services.ml_model_service import get_model_service
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from datetime import datetime, timedelta
from sqlalchemy import func

risk_bp = Blueprint('risk', __name__, url_prefix='/api/risk')


# ============================================================================
# API ENDPOINTS
# ============================================================================

@risk_bp.route('/predict/site/<site_code>', methods=['GET'])
@login_required
def predict_site_risk(site_code):
    """
    Predict risk level for a specific site

    Args:
        site_code: Site code

    Returns:
        JSON with risk prediction
    """
    try:
        # Get site from database
        site = Site.query.filter_by(site_code=site_code).first()

        if not site:
            return jsonify({'error': f'Site {site_code} not found'}), 404

        # Prepare site data
        site_data = {
            'site_code': site.site_code,
            'environment_type': site.environment_type,
            'is_coastal': site.is_coastal,
            'industrial_nearby': site.industrial_nearby,
            'agricultural_nearby': site.agricultural_nearby,
            'population_density': site.population_density
        }

        # Add historical statistics if available
        # Get historical analysis data (last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        historical_samples = WaterSample.query.filter(
            WaterSample.site_code == site_code,
            WaterSample.collection_date >= six_months_ago
        ).all()

        if historical_samples:
            # Calculate historical quality metrics
            sample_ids = [s.sample_id for s in historical_samples]

            test_results = TestResult.query.filter(
                TestResult.sample_id.in_(sample_ids)
            ).all()

            if test_results:
                # Simple quality score calculation
                quality_scores = []
                for tr in test_results:
                    # Basic quality assessment (higher is better)
                    score = 1.0
                    if tr.ph and (tr.ph < 6.5 or tr.ph > 8.5):
                        score -= 0.2
                    if tr.turbidity and tr.turbidity > 10:
                        score -= 0.2
                    if tr.tds and tr.tds > 500:
                        score -= 0.1
                    quality_scores.append(max(0, score))

                site_data['hist_overall_quality_score_mean'] = sum(quality_scores) / len(quality_scores) if quality_scores else 0.7
                site_data['hist_contamination_rate'] = sum(1 for s in quality_scores if s < 0.5) / len(quality_scores) if quality_scores else 0
                site_data['hist_follow_up_count'] = sum(1 for s in quality_scores if s < 0.7)

        # Get ML prediction
        ml_service = get_model_service()
        prediction = ml_service.predict_site_risk(site_data)

        if not prediction['success']:
            return jsonify(prediction), 500

        # Add site information to response
        prediction['site'] = {
            'site_code': site.site_code,
            'site_name': site.site_name,
            'environment_type': site.environment_type,
            'state': site.state
        }

        return jsonify(prediction), 200

    except Exception as e:
        current_app.logger.error(f"Error predicting site risk: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/predict/contamination', methods=['POST'])
@login_required
def predict_contamination():
    """
    Predict contamination type from water quality parameters

    Request Body (JSON):
    {
        "sample_id": 123,  // optional
        "ph": 7.2,
        "turbidity": 5.0,
        "tds": 450,
        "dissolved_oxygen": 6.0,
        "temperature": 25.0,
        "nitrate": 10.0,
        "total_hardness": 200.0,
        "bod": 5.0,
        "cod": 20.0,
        "chloride": 100.0,
        "iron": 0.1,
        "arsenic": 0.005,
        "lead": 0.005,
        "coliform_status": "absent",
        "collection_date": "2025-11-28"
    }

    Returns:
        JSON with contamination prediction
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get ML prediction
        ml_service = get_model_service()
        prediction = ml_service.predict_contamination_type(data)

        if not prediction['success']:
            return jsonify(prediction), 500

        # Add sample info if provided
        if 'sample_id' in data:
            sample = WaterSample.query.get(data['sample_id'])
            if sample:
                prediction['sample'] = {
                    'sample_id': sample.sample_id,
                    'sample_code': sample.sample_code,
                    'site_code': sample.site_code,
                    'collection_date': sample.collection_date.isoformat() if sample.collection_date else None
                }

        return jsonify(prediction), 200

    except Exception as e:
        current_app.logger.error(f"Error predicting contamination: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/predict/sample/<int:sample_id>', methods=['GET'])
@login_required
def predict_sample_contamination(sample_id):
    """
    Predict contamination type for an existing sample

    Args:
        sample_id: Sample ID

    Returns:
        JSON with contamination prediction
    """
    try:
        # Get sample and test results from database
        sample = WaterSample.query.get(sample_id)

        if not sample:
            return jsonify({'error': f'Sample {sample_id} not found'}), 404

        # Get test results
        test_result = TestResult.query.filter_by(sample_id=sample_id).first()

        if not test_result:
            return jsonify({'error': f'No test results found for sample {sample_id}'}), 404

        # Prepare sample data
        sample_data = {
            'sample_id': sample_id,
            'ph': test_result.ph,
            'turbidity': test_result.turbidity,
            'tds': test_result.tds,
            'dissolved_oxygen': test_result.dissolved_oxygen,
            'temperature': test_result.temperature,
            'nitrate': test_result.nitrate,
            'total_hardness': test_result.total_hardness,
            'bod': test_result.bod,
            'cod': test_result.cod,
            'chloride': test_result.chloride,
            'iron': test_result.iron,
            'arsenic': test_result.arsenic,
            'lead': test_result.lead,
            'coliform_status': test_result.coliform_status,
            'collection_date': sample.collection_date.isoformat() if sample.collection_date else None
        }

        # Get ML prediction
        ml_service = get_model_service()
        prediction = ml_service.predict_contamination_type(sample_data)

        if not prediction['success']:
            return jsonify(prediction), 500

        # Add sample and site info
        prediction['sample'] = {
            'sample_id': sample.sample_id,
            'sample_code': sample.sample_code,
            'site_code': sample.site_code,
            'collection_date': sample.collection_date.isoformat() if sample.collection_date else None
        }

        return jsonify(prediction), 200

    except Exception as e:
        current_app.logger.error(f"Error predicting sample contamination: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/batch/sites', methods=['POST'])
@login_required
def batch_predict_sites():
    """
    Batch predict risk levels for multiple sites

    Request Body (JSON):
    {
        "site_codes": ["SITE001", "SITE002", "SITE003"]
    }

    Returns:
        JSON with batch prediction results
    """
    try:
        data = request.get_json()

        if not data or 'site_codes' not in data:
            return jsonify({'error': 'site_codes required'}), 400

        site_codes = data['site_codes']

        # Get sites from database
        sites = Site.query.filter(Site.site_code.in_(site_codes)).all()

        if not sites:
            return jsonify({'error': 'No sites found'}), 404

        # Prepare site data
        sites_data = []
        for site in sites:
            sites_data.append({
                'site_code': site.site_code,
                'environment_type': site.environment_type,
                'is_coastal': site.is_coastal,
                'industrial_nearby': site.industrial_nearby,
                'agricultural_nearby': site.agricultural_nearby,
                'population_density': site.population_density
            })

        # Get ML predictions
        ml_service = get_model_service()
        predictions = ml_service.batch_predict_site_risks(sites_data)

        return jsonify({
            'success': True,
            'count': len(predictions),
            'predictions': predictions
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in batch site prediction: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/all-sites', methods=['GET'])
@login_required
def predict_all_sites():
    """
    Predict risk levels for all sites (with pagination)

    Query Parameters:
        page: Page number (default 1)
        per_page: Results per page (default 20)
        risk_level: Filter by risk level (high, medium, low)

    Returns:
        JSON with site risk predictions
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        risk_level_filter = request.args.get('risk_level', None)

        # Get all sites
        sites = Site.query.paginate(page=page, per_page=per_page, error_out=False)

        # Prepare site data
        sites_data = []
        for site in sites.items:
            sites_data.append({
                'site_code': site.site_code,
                'site_name': site.site_name,
                'environment_type': site.environment_type,
                'is_coastal': site.is_coastal,
                'industrial_nearby': site.industrial_nearby,
                'agricultural_nearby': site.agricultural_nearby,
                'population_density': site.population_density,
                'state': site.state
            })

        # Get ML predictions
        ml_service = get_model_service()
        predictions = ml_service.batch_predict_site_risks(sites_data)

        # Filter by risk level if specified
        if risk_level_filter:
            predictions = [p for p in predictions if p.get('risk_level') == risk_level_filter.lower()]

        return jsonify({
            'success': True,
            'page': page,
            'per_page': per_page,
            'total': sites.total,
            'pages': sites.pages,
            'count': len(predictions),
            'predictions': predictions
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error predicting all sites: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/models/info', methods=['GET'])
def models_info():
    """
    Get information about loaded ML models

    Returns:
        JSON with model information
    """
    try:
        ml_service = get_model_service()
        info = ml_service.get_model_info()

        return jsonify({
            'success': True,
            'info': info
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting model info: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        ml_service = get_model_service()
        models_loaded = ml_service.models_loaded

        return jsonify({
            'status': 'healthy' if models_loaded else 'degraded',
            'models_loaded': models_loaded,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# FRONTEND TEMPLATES
# ============================================================================

@risk_bp.route('/dashboard', methods=['GET'])
@login_required
def risk_dashboard():
    """Risk prediction dashboard page"""
    return render_template('risk/dashboard.html')


@risk_bp.route('/site-risk/<site_code>', methods=['GET'])
@login_required
def site_risk_page(site_code):
    """Site risk detail page"""
    site = Site.query.filter_by(site_code=site_code).first_or_404()
    return render_template('risk/site_detail.html', site=site)
