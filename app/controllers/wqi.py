"""
WQI (Water Quality Index) Controller
API endpoints for real-time water quality index calculations
"""
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from app import db
from app.services.wqi_service import WQIService
from app.models.wqi_calculation import WQICalculation
from app.models.site import Site
from app.models.water_sample import WaterSample
from datetime import datetime

wqi_bp = Blueprint('wqi', __name__, url_prefix='/api/wqi')


# ============================================================================
# API ENDPOINTS
# ============================================================================

@wqi_bp.route('/calculate', methods=['POST'])
def calculate_wqi():
    """
    Calculate WQI from water quality parameters

    Request Body (JSON):
    {
        "ph_value": 7.2,
        "tds_ppm": 450,
        "turbidity_ntu": 3.5,
        "free_chlorine": 0.5,
        "temperature_c": 22.0,
        "total_coliform": 5,
        "sample_id": 123,  // optional
        "site_id": 45,     // optional
        "device_id": "IOT-001",  // optional
        "save": true  // optional, default false
    }

    Returns:
        JSON with WQI score, compliance class, penalties breakdown
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract water quality parameters
        ph_value = data.get('ph_value')
        tds_ppm = data.get('tds_ppm')
        turbidity_ntu = data.get('turbidity_ntu')
        free_chlorine = data.get('free_chlorine')
        temperature_c = data.get('temperature_c')
        total_coliform = data.get('total_coliform')

        # Calculate WQI
        result = WQIService.calculate_wqi(
            ph_value=ph_value,
            tds_ppm=tds_ppm,
            turbidity_ntu=turbidity_ntu,
            free_chlorine=free_chlorine,
            temperature_c=temperature_c,
            total_coliform=total_coliform
        )

        # Optionally save to database
        if data.get('save', False):
            wqi_calc = WQICalculation(
                sample_id=data.get('sample_id'),
                site_id=data.get('site_id'),
                device_id=data.get('device_id'),
                ph_value=ph_value,
                tds_ppm=tds_ppm,
                turbidity_ntu=turbidity_ntu,
                free_chlorine=free_chlorine,
                temperature_c=temperature_c,
                total_coliform=total_coliform,
                wqi_score=result['wqi_score'],
                compliance_class=result['compliance_class'],
                is_safe=result['is_safe'],
                ph_penalty=result['penalties']['ph'],
                tds_penalty=result['penalties']['tds'],
                turbidity_penalty=result['penalties']['turbidity'],
                chlorine_penalty=result['penalties']['chlorine'],
                temperature_penalty=result['penalties']['temperature'],
                coliform_penalty=result['penalties']['coliform'],
                total_penalty=result['total_penalty'],
                calculation_type=data.get('calculation_type', 'manual'),
                calculated_by_id=current_user.id if current_user.is_authenticated else None
            )

            db.session.add(wqi_calc)
            db.session.commit()

            result['calculation_id'] = wqi_calc.id

        # Add compliance information
        compliance_info = WQIService.get_compliance_info(result['compliance_class'])
        result['compliance_info'] = compliance_info

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error calculating WQI: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/device/<device_id>/latest', methods=['GET'])
def get_latest_wqi_for_device(device_id):
    """
    Get latest WQI calculation for a specific device

    Args:
        device_id: Device identifier

    Returns:
        JSON with latest WQI calculation or 404 if not found
    """
    try:
        wqi_calc = WQICalculation.get_latest_for_device(device_id)

        if not wqi_calc:
            return jsonify({'error': 'No WQI calculations found for this device'}), 404

        result = wqi_calc.to_dict()
        compliance_info = WQIService.get_compliance_info(wqi_calc.compliance_class)
        result['compliance_info'] = compliance_info

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving WQI for device {device_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/device/<device_id>/history', methods=['GET'])
def get_wqi_history_for_device(device_id):
    """
    Get historical WQI calculations for a device

    Query Parameters:
        limit: Number of results to return (default 100)

    Returns:
        JSON array of WQI calculations
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        limit = min(limit, 1000)  # Cap at 1000

        wqi_calcs = WQICalculation.get_history_for_device(device_id, limit=limit)

        results = [calc.to_dict() for calc in wqi_calcs]

        return jsonify({
            'device_id': device_id,
            'count': len(results),
            'calculations': results
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving WQI history for device {device_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/site/<int:site_id>/latest', methods=['GET'])
def get_latest_wqi_for_site(site_id):
    """
    Get latest WQI calculation for a specific site

    Args:
        site_id: Site ID

    Returns:
        JSON with latest WQI calculation or 404 if not found
    """
    try:
        wqi_calc = WQICalculation.get_latest_for_site(site_id)

        if not wqi_calc:
            return jsonify({'error': 'No WQI calculations found for this site'}), 404

        result = wqi_calc.to_dict()
        compliance_info = WQIService.get_compliance_info(wqi_calc.compliance_class)
        result['compliance_info'] = compliance_info

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving WQI for site {site_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/site/<int:site_id>/history', methods=['GET'])
def get_wqi_history_for_site(site_id):
    """
    Get historical WQI calculations for a site

    Query Parameters:
        limit: Number of results to return (default 100)

    Returns:
        JSON array of WQI calculations
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        limit = min(limit, 1000)  # Cap at 1000

        wqi_calcs = WQICalculation.get_history_for_site(site_id, limit=limit)

        results = [calc.to_dict() for calc in wqi_calcs]

        return jsonify({
            'site_id': site_id,
            'count': len(results),
            'calculations': results
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving WQI history for site {site_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/summary-statistics', methods=['GET'])
def get_summary_statistics():
    """
    Get summary statistics for WQI calculations

    Query Parameters:
        days: Number of days to include (default 30)

    Returns:
        JSON with statistics (total, average, compliance distribution, etc.)
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Cap at 1 year

        stats = WQICalculation.get_summary_statistics(days=days)

        return jsonify(stats), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving WQI statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wqi_bp.route('/batch-calculate', methods=['POST'])
def batch_calculate_wqi():
    """
    Calculate WQI for multiple water samples

    Request Body (JSON):
    {
        "samples": [
            {
                "ph_value": 7.2,
                "tds_ppm": 450,
                ...
            },
            ...
        ],
        "save": true  // optional
    }

    Returns:
        JSON array of WQI calculations
    """
    try:
        data = request.get_json()

        if not data or 'samples' not in data:
            return jsonify({'error': 'No samples provided'}), 400

        samples = data.get('samples', [])
        save = data.get('save', False)

        results = []

        for sample_data in samples:
            # Calculate WQI
            result = WQIService.calculate_wqi(
                ph_value=sample_data.get('ph_value'),
                tds_ppm=sample_data.get('tds_ppm'),
                turbidity_ntu=sample_data.get('turbidity_ntu'),
                free_chlorine=sample_data.get('free_chlorine'),
                temperature_c=sample_data.get('temperature_c'),
                total_coliform=sample_data.get('total_coliform')
            )

            # Optionally save to database
            if save:
                wqi_calc = WQICalculation(
                    sample_id=sample_data.get('sample_id'),
                    site_id=sample_data.get('site_id'),
                    device_id=sample_data.get('device_id'),
                    ph_value=sample_data.get('ph_value'),
                    tds_ppm=sample_data.get('tds_ppm'),
                    turbidity_ntu=sample_data.get('turbidity_ntu'),
                    free_chlorine=sample_data.get('free_chlorine'),
                    temperature_c=sample_data.get('temperature_c'),
                    total_coliform=sample_data.get('total_coliform'),
                    wqi_score=result['wqi_score'],
                    compliance_class=result['compliance_class'],
                    is_safe=result['is_safe'],
                    ph_penalty=result['penalties']['ph'],
                    tds_penalty=result['penalties']['tds'],
                    turbidity_penalty=result['penalties']['turbidity'],
                    chlorine_penalty=result['penalties']['chlorine'],
                    temperature_penalty=result['penalties']['temperature'],
                    coliform_penalty=result['penalties']['coliform'],
                    total_penalty=result['total_penalty'],
                    calculation_type='batch',
                    calculated_by_id=current_user.id if current_user.is_authenticated else None
                )

                db.session.add(wqi_calc)
                result['calculation_id'] = wqi_calc.id

            results.append(result)

        if save:
            db.session.commit()

        return jsonify({
            'count': len(results),
            'calculations': results
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in batch WQI calculation: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@wqi_bp.route('/calculator', methods=['GET'])
@login_required
def wqi_calculator_page():
    """
    WQI Calculator page - manual WQI calculation tool
    """
    return render_template('wqi/calculator.html')


@wqi_bp.route('/dashboard', methods=['GET'])
@login_required
def wqi_dashboard():
    """
    WQI Dashboard - overview of WQI calculations and trends
    """
    # Get statistics for different time periods
    stats_7d = WQICalculation.get_summary_statistics(days=7)
    stats_30d = WQICalculation.get_summary_statistics(days=30)

    # Get recent calculations
    recent_calcs = WQICalculation.query.order_by(
        WQICalculation.calculated_at.desc()
    ).limit(20).all()

    return render_template('wqi/dashboard.html',
                         stats_7d=stats_7d,
                         stats_30d=stats_30d,
                         recent_calculations=recent_calcs)


@wqi_bp.route('/info', methods=['GET'])
def wqi_info_page():
    """
    WQI Information page - explains WQI methodology
    Public access (no login required)
    """
    return render_template('wqi/info.html')


# ============================================================================
# HEALTH CHECK
# ============================================================================

@wqi_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Jal Sarovar WQI Calculator',
        'version': '1.0.0'
    }), 200
