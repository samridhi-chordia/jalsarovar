"""
ML Models Controller
Handles ML-driven cost optimization, risk prediction, and contamination classification
"""
from flask import Blueprint, render_template, request, jsonify, current_app
import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime
import plotly
import plotly.graph_objs as go

ml_models_bp = Blueprint('ml_models', __name__, url_prefix='/ml')

# Global storage for loaded models and data
MODELS = {}
DATA = {}
REPORTS = {}
MODELS_LOADED = False


def load_ml_assets():
    """Load ML models, data, and reports on first request"""
    global MODELS, DATA, REPORTS, MODELS_LOADED

    if MODELS_LOADED:
        return True

    try:
        base_path = os.path.join(current_app.root_path, '..')

        # Load trained models
        MODELS['site_risk_classifier'] = joblib.load(
            os.path.join(base_path, 'app/ml/trained_models/site_risk_classifier.pkl')
        )
        MODELS['contamination_classifier'] = joblib.load(
            os.path.join(base_path, 'app/ml/trained_models/contamination_classifier.pkl')
        )
        MODELS['quality_forecaster'] = joblib.load(
            os.path.join(base_path, 'app/ml/trained_models/quality_forecaster_ph.pkl')
        )
        MODELS['testing_schedule'] = pd.read_csv(
            os.path.join(base_path, 'app/ml/trained_models/testing_schedule.csv')
        )

        # Load demo data
        DATA['sites'] = pd.read_csv(os.path.join(base_path, 'demo_data/amrit_sarovar_sites.csv'))
        DATA['samples'] = pd.read_csv(os.path.join(base_path, 'demo_data/water_samples.csv'))
        DATA['test_results'] = pd.read_csv(os.path.join(base_path, 'demo_data/test_results.csv'))
        DATA['analyses'] = pd.read_csv(os.path.join(base_path, 'demo_data/analyses.csv'))

        # Load reports
        with open(os.path.join(base_path, 'reports/ml_model_report.json'), 'r') as f:
            REPORTS['ml_models'] = json.load(f)

        with open(os.path.join(base_path, 'reports/cost_analysis_report_full.json'), 'r') as f:
            REPORTS['cost_full'] = json.load(f)

        MODELS_LOADED = True
        return True

    except Exception as e:
        current_app.logger.error(f"Error loading ML assets: {e}")
        return False


@ml_models_bp.route('/')
def index():
    """ML Dashboard - Main overview page"""
    if not load_ml_assets():
        return render_template('error.html', error='Failed to load ML models'), 500

    # Calculate summary statistics
    total_sites = len(DATA['sites'])
    total_samples = len(DATA['samples'])

    # Get model metrics
    site_risk_acc = REPORTS['ml_models']['metrics']['site_risk_classifier']['accuracy']
    contam_acc = REPORTS['ml_models']['metrics']['contamination_classifier']['accuracy']
    forecast_rmse = REPORTS['ml_models']['metrics']['quality_forecaster_ph']['rmse']

    # Get cost savings
    baseline_cost = REPORTS['cost_full']['baseline_approach']['total_annual_cost']
    ml_cost = REPORTS['cost_full']['ml_optimized_approach']['total_annual_cost']
    savings_percent = REPORTS['cost_full']['savings_analysis']['savings_percentage']

    # Risk distribution
    risk_dist = REPORTS['ml_models']['metrics']['testing_schedule_optimizer']['risk_distribution']

    summary_stats = {
        'total_sites': total_sites,
        'total_samples': total_samples,
        'site_risk_accuracy': f"{site_risk_acc*100:.1f}%",
        'contamination_accuracy': f"{contam_acc*100:.1f}%",
        'forecast_rmse': f"{forecast_rmse:.2f}",
        'baseline_cost': f"₹{baseline_cost/10000000:.2f} Cr",
        'ml_cost': f"₹{ml_cost/10000000:.2f} Cr",
        'savings_percent': f"{savings_percent:.1f}%",
        'risk_distribution': risk_dist
    }

    return render_template('ml/dashboard.html', stats=summary_stats)


@ml_models_bp.route('/cost-analysis')
def cost_analysis():
    """Cost analysis and ROI visualization"""
    if not load_ml_assets():
        return render_template('error.html', error='Failed to load ML models'), 500

    # Create cost comparison chart
    cost_chart = create_cost_comparison_chart()

    # Create savings breakdown chart
    savings_chart = create_savings_breakdown_chart()

    # Get detailed cost metrics - pass directly from reports
    cost_metrics = REPORTS['cost_full']

    return render_template('ml/cost_analysis.html',
                         cost_chart=cost_chart,
                         savings_chart=savings_chart,
                         metrics=cost_metrics)


@ml_models_bp.route('/site-risk-predictor')
def site_risk_predictor():
    """Site risk prediction interface"""
    if not load_ml_assets():
        return render_template('error.html', error='Failed to load ML models'), 500

    # Get sample sites for demo
    sample_sites = DATA['sites'].head(10).to_dict('records')

    # Get model metrics
    metrics = REPORTS['ml_models']['metrics']['site_risk_classifier']

    return render_template('ml/site_risk.html',
                         sample_sites=sample_sites,
                         metrics=metrics)


@ml_models_bp.route('/model-performance')
def model_performance():
    """Model performance metrics and visualizations"""
    if not load_ml_assets():
        return render_template('error.html', error='Failed to load ML models'), 500

    # Create feature importance chart
    feature_chart = create_feature_importance_chart()

    # Create confusion matrix
    confusion_chart = create_confusion_matrix_chart()

    metrics = REPORTS['ml_models']['metrics']

    return render_template('ml/model_performance.html',
                         feature_chart=feature_chart,
                         confusion_chart=confusion_chart,
                         metrics=metrics)


@ml_models_bp.route('/data-explorer')
def data_explorer():
    """Interactive data exploration interface"""
    if not load_ml_assets():
        return render_template('error.html', error='Failed to load ML models'), 500

    # Sample sites for display
    sample_sites = DATA['sites'].head(20).to_dict('records')

    # Summary statistics
    stats = {
        'total_sites': len(DATA['sites']),
        'total_samples': len(DATA['samples']),
        'states_covered': DATA['sites']['state'].nunique(),
        'who_compliant': int(DATA['analyses']['who_compliant'].sum()),
        'non_compliant': int((~DATA['analyses']['who_compliant']).sum()),
        'urgent_priority': int((DATA['analyses']['overall_quality_score'] > 0.7).sum())
    }

    return render_template('ml/data_explorer.html',
                         sample_sites=sample_sites,
                         stats=stats)


@ml_models_bp.route('/anomaly-detection')
def anomaly_detection():
    """Anomaly Detection Dashboard - Real-time monitoring"""
    return render_template('ml/anomaly_detection.html')


# API Endpoints

@ml_models_bp.route('/api/predict-site-risk', methods=['POST'])
def api_predict_site_risk():
    """API endpoint for site risk prediction"""
    if not load_ml_assets():
        return jsonify({'error': 'ML models not loaded'}), 500

    try:
        data = request.get_json()
        site_code = data.get('site_code')

        if not site_code:
            return jsonify({'error': 'site_code required'}), 400

        # Find site in schedule
        site_schedule = MODELS['testing_schedule'][
            MODELS['testing_schedule']['site_code'] == site_code
        ]

        if len(site_schedule) == 0:
            return jsonify({'error': 'Site not found'}), 404

        site_info = site_schedule.iloc[0]

        result = {
            'site_code': site_code,
            'risk_level': site_info['predicted_risk'],
            'tests_per_year': int(site_info['tests_per_year']),
            'annual_cost': float(site_info['annual_cost']),
            'confidence': 'High'
        }

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Site risk prediction error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/site-details/<site_code>')
def api_site_details(site_code):
    """Get detailed information for a specific site"""
    if not load_ml_assets():
        return jsonify({'error': 'ML models not loaded'}), 500

    try:
        # Get site info
        site = DATA['sites'][DATA['sites']['site_code'] == site_code]
        if len(site) == 0:
            return jsonify({'error': 'Site not found'}), 404

        site_info = site.iloc[0].to_dict()

        # Get samples for this site
        samples = DATA['samples'][DATA['samples']['site_code'] == site_code]
        sample_ids = samples['sample_id'].tolist()

        # Get analyses
        analyses = DATA['analyses'][
            DATA['analyses']['sample_id'].isin(sample_ids)
        ]

        # Calculate statistics
        result = {
            'site_info': site_info,
            'total_samples': len(samples),
            'avg_quality_score': float(analyses['overall_quality_score'].mean()) if len(analyses) > 0 else 0,
            'who_compliant_rate': float(analyses['who_compliant'].mean()) if len(analyses) > 0 else 0,
            'primary_contaminations': analyses['primary_contamination_type'].value_counts().to_dict() if len(analyses) > 0 else {},
            'recent_samples': samples.tail(5).to_dict('records')
        }

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Site details error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/stats')
def api_stats():
    """Get ML system statistics"""
    if not load_ml_assets():
        return jsonify({'error': 'ML models not loaded'}), 500

    try:
        stats = {
            'models_loaded': len(MODELS),
            'total_sites': len(DATA['sites']),
            'total_samples': len(DATA['samples']),
            'site_risk_accuracy': REPORTS['ml_models']['metrics']['site_risk_classifier']['accuracy'],
            'contamination_accuracy': REPORTS['ml_models']['metrics']['contamination_classifier']['accuracy'],
            'annual_savings': REPORTS['cost_full']['savings_analysis']['annual_savings'],
            'savings_percentage': REPORTS['cost_full']['savings_analysis']['savings_percentage']
        }

        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Stats API error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/detect-anomalies', methods=['POST'])
def api_detect_anomalies():
    """
    Detect anomalies in water quality measurement using Isolation Forest + CUSUM

    Request JSON format:
    {
        "measurement": {
            "ph_value": 7.2,
            "tds_ppm": 250,
            "temperature_celsius": 25,
            "turbidity_ntu": 1.0,
            "conductivity_us_cm": 400,
            "free_chlorine_mg_l": 0.5,
            "orp_mv": 650,
            "measurement_datetime": "2025-01-15T10:30:00"  (optional)
        },
        "site_id": 123  (optional, for CUSUM tracking)
    }

    Response JSON format:
    {
        "timestamp": "2025-01-15T10:30:00",
        "overall_anomaly_detected": false,
        "sudden_anomaly": {
            "detected": false,
            "type": null,
            "severity": null,
            "score": -0.05
        },
        "drift": {
            "detected": false,
            "parameters_affected": [],
            "details": {...}
        },
        "overall_severity": "normal"
    }
    """
    try:
        from app.services.drift_detector import get_combined_detector

        data = request.get_json()
        if not data or 'measurement' not in data:
            return jsonify({'error': 'measurement data required'}), 400

        measurement = data['measurement']
        measurement_time = None

        # Parse timestamp if provided
        if 'measurement_datetime' in measurement:
            try:
                measurement_time = datetime.fromisoformat(measurement['measurement_datetime'].replace('Z', '+00:00'))
            except:
                measurement_time = datetime.now()

        # Get combined detector (Isolation Forest + CUSUM)
        detector = get_combined_detector()

        # Perform detection
        result = detector.detect(measurement, measurement_time)

        # Convert datetime to ISO format for JSON
        result['timestamp'] = result['timestamp'].isoformat()

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Anomaly detection error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/anomaly-batch-detect', methods=['POST'])
def api_anomaly_batch_detect():
    """
    Batch anomaly detection for multiple measurements

    Request JSON format:
    {
        "measurements": [
            {"ph_value": 7.2, "tds_ppm": 250, ...},
            {"ph_value": 7.3, "tds_ppm": 255, ...},
            ...
        ],
        "timestamps": ["2025-01-15T10:00:00", ...] (optional)
    }

    Response: Array of anomaly detection results
    """
    try:
        from app.services.drift_detector import get_combined_detector

        data = request.get_json()
        if not data or 'measurements' not in data:
            return jsonify({'error': 'measurements array required'}), 400

        measurements = data['measurements']
        timestamps = data.get('timestamps')

        # Parse timestamps if provided
        if timestamps:
            try:
                timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
            except:
                timestamps = None

        # Get detector
        detector = get_combined_detector()

        # Process each measurement
        results = []
        for i, measurement in enumerate(measurements):
            timestamp = timestamps[i] if timestamps else None
            result = detector.detect(measurement, timestamp)
            result['timestamp'] = result['timestamp'].isoformat()
            results.append(result)

        return jsonify({
            'total_measurements': len(measurements),
            'anomalies_detected': sum(1 for r in results if r['overall_anomaly_detected']),
            'results': results
        })

    except Exception as e:
        current_app.logger.error(f"Batch anomaly detection error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/drift-summary')
def api_drift_summary():
    """
    Get current drift detection summary

    Response: Summary of parameters currently showing drift
    """
    try:
        from app.services.drift_detector import get_drift_detector

        detector = get_drift_detector()
        summary = detector.get_drift_summary()

        # Convert datetime objects to ISO format
        if 'drift_details' in summary:
            for param, details in summary['drift_details'].items():
                if details.get('start_time'):
                    # Already in ISO format from detector
                    pass

        return jsonify(summary)

    except Exception as e:
        current_app.logger.error(f"Drift summary error: {e}")
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/reset-drift/<parameter>')
def api_reset_drift(parameter):
    """
    Reset CUSUM drift detection for a specific parameter
    (e.g., after maintenance or calibration)

    Parameters:
    -----------
    parameter : str
        Parameter name (ph_value, tds_ppm, etc.)
    """
    try:
        from app.services.drift_detector import get_drift_detector

        detector = get_drift_detector()
        detector.reset_parameter(parameter)

        return jsonify({
            'success': True,
            'message': f'Drift statistics reset for parameter: {parameter}'
        })

    except Exception as e:
        current_app.logger.error(f"Reset drift error: {e}")
        return jsonify({'error': str(e)}), 500


# ===========================
# Gaussian Process Forecasting API Endpoints
# ===========================

@ml_models_bp.route('/api/gp-forecast', methods=['POST'])
def api_gp_forecast():
    """
    Generate 90-day water quality forecast using Gaussian Process

    Request JSON:
    {
        "parameter": "ph_value",  # or "tds_ppm", "turbidity_ntu", etc.
        "site_id": 1,             # Optional: specific site
        "forecast_days": 90       # Optional: forecast horizon (default: 90)
    }

    Response:
    {
        "parameter": "ph_value",
        "forecast_days": 90,
        "forecast": [
            {
                "timestamp": "2024-07-01T00:00:00",
                "mean": 7.2,
                "std": 0.15,
                "lower_95ci": 6.9,
                "upper_95ci": 7.5,
                "early_warning": false
            },
            ...
        ],
        "early_warnings": [...],
        "model_metrics": {...}
    }
    """
    try:
        from app.services.gp_forecaster import get_gp_forecaster
        from app.models.residential_site import ResidentialMeasurement

        data = request.get_json()
        parameter = data.get('parameter', 'ph_value')
        site_id = data.get('site_id')
        forecast_days = data.get('forecast_days', 90)

        # Get historical measurements for training
        query = ResidentialMeasurement.query
        if site_id:
            query = query.filter_by(site_id=site_id)

        # Get last 180 days of measurements
        measurements_db = query.filter(
            ResidentialMeasurement.measurement_datetime >= datetime.now() - timedelta(days=180)
        ).order_by(ResidentialMeasurement.measurement_datetime).all()

        if len(measurements_db) < 30:
            return jsonify({
                'error': 'Insufficient historical data',
                'message': f'Need at least 30 measurements, found {len(measurements_db)}'
            }), 400

        # Prepare data for GP
        measurements = []
        timestamps = []

        for m in measurements_db:
            measurement_dict = {
                'ph_value': m.ph_value,
                'tds_ppm': m.tds_ppm,
                'temperature_celsius': m.temperature_celsius,
                'turbidity_ntu': m.turbidity_ntu,
                'conductivity_us_cm': m.conductivity_us_cm,
                'free_chlorine_mg_l': m.free_chlorine_mg_l
            }

            # Skip if parameter is missing
            if measurement_dict.get(parameter) is None:
                continue

            measurements.append(measurement_dict)
            timestamps.append(m.measurement_datetime)

        if len(measurements) < 30:
            return jsonify({
                'error': 'Insufficient valid data',
                'message': f'Parameter {parameter} needs at least 30 valid measurements'
            }), 400

        # Create and train forecaster
        forecaster = get_gp_forecaster(parameter=parameter, forecast_days=forecast_days)

        # Train on historical data
        metrics = forecaster.train(measurements, timestamps)

        # Generate forecast
        forecast_df = forecaster.forecast()

        # Get early warnings
        warnings = forecaster.get_early_warnings(forecast_df)

        # Convert forecast to JSON-serializable format
        forecast_list = []
        for idx, row in forecast_df.iterrows():
            forecast_list.append({
                'timestamp': row['timestamp'].isoformat(),
                'mean': float(row['mean']),
                'std': float(row['std']),
                'lower_95ci': float(row['lower_95ci']),
                'upper_95ci': float(row['upper_95ci']),
                'early_warning': bool(row['early_warning'])
            })

        return jsonify({
            'parameter': parameter,
            'forecast_days': forecast_days,
            'training_samples': len(measurements),
            'forecast': forecast_list,
            'early_warnings': warnings,
            'model_metrics': metrics
        })

    except Exception as e:
        current_app.logger.error(f"GP forecast error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@ml_models_bp.route('/api/gp-forecast-batch', methods=['POST'])
def api_gp_forecast_batch():
    """
    Generate forecasts for multiple parameters

    Request JSON:
    {
        "parameters": ["ph_value", "tds_ppm", "turbidity_ntu"],
        "site_id": 1,
        "forecast_days": 90
    }

    Response:
    {
        "forecasts": {
            "ph_value": {...},
            "tds_ppm": {...},
            ...
        }
    }
    """
    try:
        data = request.get_json()
        parameters = data.get('parameters', ['ph_value'])
        site_id = data.get('site_id')
        forecast_days = data.get('forecast_days', 90)

        forecasts = {}

        for parameter in parameters:
            # Call single forecast API for each parameter
            single_request = {
                'parameter': parameter,
                'site_id': site_id,
                'forecast_days': forecast_days
            }

            # Use internal request context
            with current_app.test_request_context(
                '/ml/api/gp-forecast',
                method='POST',
                json=single_request
            ):
                response = api_gp_forecast()

                if isinstance(response, tuple):  # Error response
                    forecasts[parameter] = {'error': response[0].get_json()['error']}
                else:
                    forecasts[parameter] = response.get_json()

        return jsonify({
            'forecasts': forecasts,
            'total_parameters': len(parameters),
            'successful': sum(1 for f in forecasts.values() if 'error' not in f)
        })

    except Exception as e:
        current_app.logger.error(f"GP batch forecast error: {e}")
        return jsonify({'error': str(e)}), 500


# Helper functions for visualizations

def create_cost_comparison_chart():
    """Create interactive cost comparison chart"""
    baseline_cost = REPORTS['cost_full']['baseline_approach']['total_annual_cost'] / 10000000
    ml_cost = REPORTS['cost_full']['ml_optimized_approach']['total_annual_cost'] / 10000000

    fig = go.Figure(data=[
        go.Bar(
            name='Baseline (Monthly Testing)',
            x=['Annual Cost'],
            y=[baseline_cost],
            marker_color='#e74c3c',
            text=[f'₹{baseline_cost:.2f} Cr'],
            textposition='auto',
        ),
        go.Bar(
            name='ML-Optimized (Risk-Based)',
            x=['Annual Cost'],
            y=[ml_cost],
            marker_color='#27ae60',
            text=[f'₹{ml_cost:.2f} Cr'],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Annual Testing Cost Comparison (68,000 Sites)',
        yaxis_title='Cost (Crore ₹)',
        barmode='group',
        height=400,
        template='plotly_white'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_savings_breakdown_chart():
    """Create savings breakdown by risk level"""
    risk_dist = REPORTS['ml_models']['metrics']['testing_schedule_optimizer']['risk_distribution']

    labels = ['High Risk', 'Medium Risk', 'Low Risk']
    values = [risk_dist['high'], risk_dist['medium'], risk_dist['low']]
    colors = ['#e74c3c', '#f39c12', '#27ae60']

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        hole=0.4,
        textinfo='label+percent',
        textposition='outside'
    )])

    fig.update_layout(
        title='Risk Distribution Across 68,000 Sites',
        height=400,
        template='plotly_white'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_feature_importance_chart():
    """Create feature importance chart for site risk classifier"""
    feature_data = REPORTS['ml_models']['metrics']['site_risk_classifier']['feature_importances'][:10]

    features = [f['feature'] for f in feature_data]
    importances = [f['importance'] for f in feature_data]

    fig = go.Figure(data=[go.Bar(
        x=importances,
        y=features,
        orientation='h',
        marker_color='#3498db',
        text=[f'{imp:.3f}' for imp in importances],
        textposition='auto'
    )])

    fig.update_layout(
        title='Top 10 Feature Importances (Site Risk Classifier)',
        xaxis_title='Importance Score',
        yaxis_title='Feature',
        height=500,
        template='plotly_white'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_confusion_matrix_chart():
    """Create confusion matrix heatmap"""
    cm = REPORTS['ml_models']['metrics']['site_risk_classifier']['confusion_matrix']

    fig = go.Figure(data=go.Heatmap(
        z=cm,
        x=['High', 'Low', 'Medium'],
        y=['High', 'Low', 'Medium'],
        colorscale='Blues',
        text=cm,
        texttemplate='%{text}',
        textfont={"size": 16},
    ))

    fig.update_layout(
        title='Confusion Matrix (Site Risk Classifier)',
        xaxis_title='Predicted',
        yaxis_title='Actual',
        height=500,
        template='plotly_white'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
