"""
WQI (Water Quality Index) Calculator Controller
Public-facing WQI calculator for manual water quality assessment
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user

wqi_bp = Blueprint('wqi', __name__, url_prefix='/wqi')


def calculate_wqi(ph=None, tds=None, turbidity=None, chlorine=None, temperature=None, coliform=None):
    """
    Calculate Water Quality Index using penalty-based scoring

    WQI = 100 - sum(penalties)

    Classifications:
        Excellent: 90-100 (safe to drink)
        Compliant: 70-89 (safe to drink)
        Warning: 50-69 (marginal, caution advised)
        Unsafe: 0-49 (do not drink)
    """
    wqi = 100.0
    penalties = {
        'ph': 0.0,
        'tds': 0.0,
        'turbidity': 0.0,
        'chlorine': 0.0,
        'temperature': 0.0,
        'coliform': 0.0
    }

    # pH penalty (max 20 points) - Optimal range: 6.5-8.5
    if ph is not None:
        if ph < 6.5:
            penalties['ph'] = min(20, (6.5 - ph) * 10)
        elif ph > 8.5:
            penalties['ph'] = min(20, (ph - 8.5) * 10)

    # TDS penalty (max 30 points) - Optimal: ≤500 ppm
    if tds is not None:
        if tds > 500:
            penalties['tds'] = min(30, (tds - 500) / 50)

    # Turbidity penalty (max 20 points) - Optimal: ≤5 NTU
    if turbidity is not None:
        if turbidity > 5:
            penalties['turbidity'] = min(20, (turbidity - 5) * 2)

    # Chlorine penalty (max 15 points) - Optimal: 0.2-4.0 mg/L
    if chlorine is not None:
        if chlorine < 0.2:
            penalties['chlorine'] = 15  # No disinfection
        elif chlorine > 4.0:
            penalties['chlorine'] = 10  # Over-chlorinated

    # Temperature penalty (max 10 points) - Optimal: 10-25°C
    if temperature is not None:
        if temperature < 10:
            penalties['temperature'] = min(10, 10 - temperature)
        elif temperature > 25:
            penalties['temperature'] = min(10, (temperature - 25) * 0.5)

    # Coliform penalty (max 25 points) - Optimal: 0 CFU/100mL
    if coliform is not None:
        if coliform > 0:
            penalties['coliform'] = min(25, coliform * 2.5)

    # Calculate total penalty and WQI
    total_penalty = sum(penalties.values())
    wqi = max(0, min(100, 100 - total_penalty))

    # Determine compliance class
    if wqi >= 90:
        compliance_class = 'excellent'
        is_safe = True
    elif wqi >= 70:
        compliance_class = 'compliant'
        is_safe = True
    elif wqi >= 50:
        compliance_class = 'warning'
        is_safe = False
    else:
        compliance_class = 'unsafe'
        is_safe = False

    return {
        'wqi_score': round(wqi, 1),
        'compliance_class': compliance_class,
        'is_safe': is_safe,
        'total_penalty': round(total_penalty, 2),
        'penalties': {k: round(v, 2) for k, v in penalties.items()}
    }


def get_compliance_info(compliance_class):
    """Get detailed compliance information for display"""
    info_map = {
        'excellent': {
            'class': 'Excellent',
            'color': '#10b981',
            'description': 'Water quality is excellent. All parameters are within optimal ranges.',
            'recommendations': [
                'Continue regular monitoring to maintain quality',
                'Water is safe for all uses including drinking'
            ]
        },
        'compliant': {
            'class': 'Compliant',
            'color': '#3b82f6',
            'description': 'Water quality meets drinking water standards.',
            'recommendations': [
                'Safe for drinking and domestic use',
                'Monitor parameters showing minor deviations',
                'Consider treatment if approaching threshold limits'
            ]
        },
        'warning': {
            'class': 'Warning',
            'color': '#f59e0b',
            'description': 'Water quality is marginal. Some parameters exceed acceptable limits.',
            'recommendations': [
                'Not recommended for direct drinking without treatment',
                'Investigate source of contamination',
                'Consider boiling or filtering before consumption',
                'Schedule more frequent testing'
            ]
        },
        'unsafe': {
            'class': 'Unsafe',
            'color': '#ef4444',
            'description': 'Water quality does not meet safety standards. Do not consume.',
            'recommendations': [
                'DO NOT drink or use for cooking',
                'Immediately report to local authorities',
                'Identify and address contamination source',
                'Use alternative safe water source',
                'Professional treatment required before use'
            ]
        }
    }
    return info_map.get(compliance_class, info_map['warning'])


# ============================================================================
# API ENDPOINTS
# ============================================================================

@wqi_bp.route('/calculate', methods=['POST'])
def api_calculate_wqi():
    """
    Calculate WQI from water quality parameters (API endpoint)

    Request Body (JSON):
    {
        "ph_value": 7.2,
        "tds_ppm": 450,
        "turbidity_ntu": 3.5,
        "free_chlorine": 0.5,
        "temperature_c": 22.0,
        "total_coliform": 5
    }

    Returns:
        JSON with WQI score, compliance class, penalties breakdown
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Calculate WQI
        result = calculate_wqi(
            ph=data.get('ph_value'),
            tds=data.get('tds_ppm'),
            turbidity=data.get('turbidity_ntu'),
            chlorine=data.get('free_chlorine'),
            temperature=data.get('temperature_c'),
            coliform=data.get('total_coliform')
        )

        # Add compliance information
        result['compliance_info'] = get_compliance_info(result['compliance_class'])

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@wqi_bp.route('/calculator')
def calculator_page():
    """WQI Calculator page - public access, no login required"""
    return render_template('wqi/calculator.html')


@wqi_bp.route('/info')
def info_page():
    """WQI Information page - explains WQI methodology"""
    return render_template('wqi/info.html')
