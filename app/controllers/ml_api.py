"""ML API routes - Endpoints for all 6 ML models"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import (
    Site, WaterSample, TestResult, Analysis,
    SiteRiskPrediction, ContaminationPrediction,
    WaterQualityForecast, WQIReading, AnomalyDetection,
    CostOptimizationResult, SensorReading
)
from app.services.data_processor import DataProcessor
from app.services.ml_pipeline import MLPipeline

ml_api_bp = Blueprint('ml_api', __name__)


# ========== 1. Site Risk Classifier API ==========

@ml_api_bp.route('/site-risk/<int:site_id>', methods=['GET'])
@login_required
def get_site_risk(site_id):
    """Get site risk prediction"""
    site = Site.query.get_or_404(site_id)

    # Get latest prediction
    prediction = SiteRiskPrediction.query.filter_by(site_id=site_id).order_by(
        SiteRiskPrediction.prediction_date.desc()
    ).first()

    if prediction:
        return jsonify({
            'site_id': site_id,
            'risk_level': prediction.risk_level,
            'risk_score': prediction.risk_score,
            'confidence': prediction.confidence,
            'recommended_frequency': prediction.recommended_frequency,
            'tests_per_year': prediction.tests_per_year,
            'prediction_date': prediction.prediction_date.isoformat(),
            'probabilities': {
                'critical': prediction.prob_critical,
                'high': prediction.prob_high,
                'medium': prediction.prob_medium,
                'low': prediction.prob_low
            }
        })

    return jsonify({'error': 'No prediction available'}), 404


@ml_api_bp.route('/site-risk/<int:site_id>/predict', methods=['POST'])
@login_required
def predict_site_risk(site_id):
    """Run new site risk prediction"""
    site = Site.query.get_or_404(site_id)

    processor = DataProcessor()
    result = processor._update_site_risk(site)

    return jsonify({
        'success': True,
        'site_id': site_id,
        'risk_level': result['risk_level'],
        'risk_score': result['risk_score'],
        'recommended_frequency': result['recommended_frequency']
    })


@ml_api_bp.route('/site-risk/batch', methods=['POST'])
@login_required
def batch_site_risk():
    """Run risk prediction for multiple sites"""
    data = request.get_json()
    site_ids = data.get('site_ids', [])

    if not site_ids:
        # Process all active sites
        sites = Site.query.filter_by(is_active=True).all()
        site_ids = [s.id for s in sites]

    processor = DataProcessor()
    results = []

    for site_id in site_ids:
        site = Site.query.get(site_id)
        if site:
            result = processor._update_site_risk(site)
            results.append({
                'site_id': site_id,
                'site_name': site.site_name,
                'risk_level': result['risk_level'],
                'risk_score': result['risk_score']
            })

    return jsonify({
        'success': True,
        'processed': len(results),
        'results': results
    })


# ========== 2. Contamination Classifier API ==========

@ml_api_bp.route('/contamination/<int:sample_id>', methods=['GET'])
@login_required
def get_contamination(sample_id):
    """Get contamination classification for a sample"""
    prediction = ContaminationPrediction.query.filter_by(sample_id=sample_id).order_by(
        ContaminationPrediction.prediction_date.desc()
    ).first()

    if prediction:
        return jsonify({
            'sample_id': sample_id,
            'predicted_type': prediction.predicted_type,
            'confidence': prediction.confidence,
            'probabilities': {
                'runoff_sediment': prediction.prob_runoff_sediment,
                'sewage_ingress': prediction.prob_sewage_ingress,
                'salt_intrusion': prediction.prob_salt_intrusion,
                'pipe_corrosion': prediction.prob_pipe_corrosion,
                'disinfectant_decay': prediction.prob_disinfectant_decay
            },
            'prediction_date': prediction.prediction_date.isoformat()
        })

    return jsonify({'error': 'No prediction available'}), 404


@ml_api_bp.route('/contamination/<int:sample_id>/predict', methods=['POST'])
@login_required
def predict_contamination(sample_id):
    """Run contamination classification for a sample"""
    sample = WaterSample.query.get_or_404(sample_id)
    test_result = sample.get_latest_test()

    if not test_result:
        return jsonify({'error': 'No test results available'}), 400

    ml = MLPipeline()
    result = ml.classify_contamination(test_result, sample, sample.site)

    # Save prediction
    prediction = ContaminationPrediction(
        sample_id=sample_id,
        predicted_type=result['predicted_type'],
        confidence=result['confidence'],
        prob_runoff_sediment=result['prob_runoff_sediment'],
        prob_sewage_ingress=result['prob_sewage_ingress'],
        prob_salt_intrusion=result['prob_salt_intrusion'],
        prob_pipe_corrosion=result['prob_pipe_corrosion'],
        prob_disinfectant_decay=result['prob_disinfectant_decay'],
        shap_explanations=result['shap_explanations'],
        model_version=result['model_version'],
        f1_score=result['f1_score']
    )
    db.session.add(prediction)
    db.session.commit()

    return jsonify({
        'success': True,
        'sample_id': sample_id,
        'predicted_type': result['predicted_type'],
        'confidence': result['confidence']
    })


# ========== 3. Water Quality Forecaster API ==========

@ml_api_bp.route('/forecast/<int:site_id>', methods=['GET'])
@login_required
def get_forecast(site_id):
    """Get water quality forecasts for a site"""
    parameter = request.args.get('parameter', 'ph')
    days = request.args.get('days', 30, type=int)

    forecasts = WaterQualityForecast.query.filter_by(
        site_id=site_id,
        parameter=parameter
    ).filter(
        WaterQualityForecast.forecast_date >= datetime.utcnow().date()
    ).order_by(WaterQualityForecast.forecast_date).limit(days).all()

    return jsonify({
        'site_id': site_id,
        'parameter': parameter,
        'forecasts': [{
            'date': f.forecast_date.isoformat(),
            'predicted_value': f.predicted_value,
            'lower_bound': f.lower_bound_95,
            'upper_bound': f.upper_bound_95,
            'uncertainty': f.uncertainty,
            'prob_exceed_threshold': f.prob_exceed_threshold
        } for f in forecasts]
    })


@ml_api_bp.route('/forecast/<int:site_id>/generate', methods=['POST'])
@login_required
def generate_forecast(site_id):
    """Generate new forecasts for a site"""
    data = request.get_json() or {}
    parameters = data.get('parameters', ['ph', 'turbidity', 'tds', 'chlorine'])
    days_ahead = data.get('days_ahead', 90)

    processor = DataProcessor()
    result = processor.generate_forecasts(site_id, parameters, days_ahead)

    return jsonify({
        'success': True,
        'site_id': site_id,
        'parameters': parameters,
        'forecasts_generated': sum(len(f) for f in result['forecasts'].values())
    })


# ========== 4. Real-time WQI API ==========

@ml_api_bp.route('/wqi/<int:site_id>', methods=['GET'])
@login_required
def get_wqi(site_id):
    """Get latest WQI reading for a site"""
    reading = WQIReading.query.filter_by(site_id=site_id).order_by(
        WQIReading.reading_timestamp.desc()
    ).first()

    if reading:
        return jsonify({
            'site_id': site_id,
            'wqi_score': reading.wqi_score,
            'wqi_class': reading.wqi_class,
            'is_drinkable': reading.is_drinkable,
            'timestamp': reading.reading_timestamp.isoformat(),
            'penalties': {
                'ph': reading.ph_penalty,
                'tds': reading.tds_penalty,
                'turbidity': reading.turbidity_penalty,
                'chlorine': reading.chlorine_penalty,
                'temperature': reading.temperature_penalty
            },
            'values': {
                'ph': reading.ph_value,
                'tds': reading.tds_value,
                'turbidity': reading.turbidity_value,
                'chlorine': reading.chlorine_value,
                'temperature': reading.temperature_value
            }
        })

    return jsonify({'error': 'No WQI reading available'}), 404


@ml_api_bp.route('/wqi/calculate', methods=['POST'])
@login_required
def calculate_wqi():
    """Calculate WQI from provided values"""
    data = request.get_json()

    ml = MLPipeline()
    result = ml.calculate_realtime_wqi({
        'ph': data.get('ph'),
        'tds': data.get('tds'),
        'turbidity': data.get('turbidity'),
        'chlorine': data.get('chlorine'),
        'temperature': data.get('temperature')
    })

    return jsonify(result)


@ml_api_bp.route('/wqi/<int:site_id>/history', methods=['GET'])
@login_required
def get_wqi_history(site_id):
    """Get WQI history for a site"""
    days = request.args.get('days', 7, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    readings = WQIReading.query.filter(
        WQIReading.site_id == site_id,
        WQIReading.reading_timestamp >= cutoff
    ).order_by(WQIReading.reading_timestamp).all()

    return jsonify({
        'site_id': site_id,
        'readings': [{
            'timestamp': r.reading_timestamp.isoformat(),
            'wqi_score': r.wqi_score,
            'wqi_class': r.wqi_class
        } for r in readings]
    })


# ========== 5. Anomaly Detection API ==========

@ml_api_bp.route('/anomalies/<int:site_id>', methods=['GET'])
@login_required
def get_anomalies(site_id):
    """Get anomaly detections for a site"""
    days = request.args.get('days', 7, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    anomalies = AnomalyDetection.query.filter(
        AnomalyDetection.site_id == site_id,
        AnomalyDetection.detection_timestamp >= cutoff,
        AnomalyDetection.is_anomaly == True
    ).order_by(AnomalyDetection.detection_timestamp.desc()).all()

    return jsonify({
        'site_id': site_id,
        'anomalies': [{
            'id': a.id,
            'type': a.anomaly_type,
            'parameter': a.parameter,
            'observed_value': a.observed_value,
            'expected_value': a.expected_value,
            'deviation_sigma': a.deviation_sigma,
            'timestamp': a.detection_timestamp.isoformat(),
            'acknowledged': a.acknowledged
        } for a in anomalies]
    })


@ml_api_bp.route('/anomalies/detect', methods=['POST'])
@login_required
def detect_anomaly():
    """Detect anomaly from sensor reading"""
    data = request.get_json()
    site_id = data.get('site_id')

    current_reading = {
        'ph': data.get('ph'),
        'tds': data.get('tds'),
        'turbidity': data.get('turbidity'),
        'chlorine': data.get('chlorine'),
        'temperature': data.get('temperature')
    }

    # Get historical stats (simplified)
    historical_stats = data.get('historical_stats', {
        'ph': {'mean': 7.0, 'std': 0.5},
        'tds': {'mean': 400, 'std': 100},
        'turbidity': {'mean': 3, 'std': 2},
        'chlorine': {'mean': 0.5, 'std': 0.2},
        'temperature': {'mean': 25, 'std': 3}
    })

    ml = MLPipeline()
    result = ml.detect_anomaly(current_reading, historical_stats)

    # Save if anomaly detected
    if result['is_anomaly'] and site_id:
        anomaly = AnomalyDetection(
            site_id=site_id,
            is_anomaly=True,
            anomaly_type=result['anomaly_type'],
            anomaly_score=result['anomaly_score'],
            cusum_value=result['cusum_value'],
            parameter=result['parameter'],
            observed_value=result['observed_value'],
            expected_value=result['expected_value'],
            deviation_sigma=result['deviation_sigma'],
            detection_method=result['detection_method'],
            model_version=result['model_version']
        )
        db.session.add(anomaly)
        db.session.commit()
        result['anomaly_id'] = anomaly.id

    return jsonify(result)


@ml_api_bp.route('/anomalies/<int:anomaly_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_anomaly(anomaly_id):
    """Acknowledge an anomaly"""
    from flask_login import current_user

    anomaly = AnomalyDetection.query.get_or_404(anomaly_id)
    anomaly.acknowledged = True
    anomaly.acknowledged_by_id = current_user.id
    anomaly.acknowledged_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'anomaly_id': anomaly_id})


# ========== 6. Cost Optimizer API ==========

@ml_api_bp.route('/cost-optimizer/results', methods=['GET'])
@login_required
def get_cost_optimization():
    """Get latest cost optimization results"""
    run_id = request.args.get('run_id')

    if run_id:
        results = CostOptimizationResult.query.filter_by(
            optimization_run_id=run_id
        ).order_by(CostOptimizationResult.priority_rank).all()
    else:
        # Get latest run
        latest = CostOptimizationResult.query.order_by(
            CostOptimizationResult.optimization_date.desc()
        ).first()

        if not latest:
            return jsonify({'error': 'No optimization results available'}), 404

        results = CostOptimizationResult.query.filter_by(
            optimization_run_id=latest.optimization_run_id
        ).order_by(CostOptimizationResult.priority_rank).all()

    # Calculate totals
    total_current = sum(r.current_cost_inr or 0 for r in results)
    total_optimized = sum(r.optimized_cost_inr or 0 for r in results)

    return jsonify({
        'run_id': results[0].optimization_run_id if results else None,
        'run_date': results[0].optimization_date.isoformat() if results else None,
        'summary': {
            'total_sites': len(results),
            'total_current_cost': total_current,
            'total_optimized_cost': total_optimized,
            'total_savings': total_current - total_optimized,
            'savings_percent': round((total_current - total_optimized) / total_current * 100, 1) if total_current > 0 else 0
        },
        'sites': [{
            'site_id': r.site_id,
            'risk_category': r.risk_category,
            'current_tests': r.current_tests_per_year,
            'optimized_tests': r.optimized_tests_per_year,
            'current_cost': r.current_cost_inr,
            'optimized_cost': r.optimized_cost_inr,
            'savings': r.cost_savings_inr,
            'savings_percent': r.cost_reduction_percent,
            'detection_rate': r.detection_rate,
            'recommended_frequency': r.recommended_frequency,
            'priority': r.priority_rank
        } for r in results]
    })


@ml_api_bp.route('/cost-optimizer/run', methods=['POST'])
@login_required
def run_cost_optimization():
    """Run cost optimization"""
    data = request.get_json() or {}
    budget = data.get('budget_inr')

    processor = DataProcessor()
    result = processor.run_cost_optimization(budget)

    return jsonify({
        'success': True,
        'run_id': result['optimization_run_id'],
        'total_sites': result['total_sites'],
        'total_savings': result['total_savings'],
        'savings_percent': result['cost_reduction_percent'],
        'average_detection_rate': result['average_detection_rate']
    })


# ========== Pipeline API ==========

@ml_api_bp.route('/pipeline/process-sample/<int:sample_id>', methods=['POST'])
@login_required
def process_sample(sample_id):
    """Run complete ML pipeline on a sample"""
    processor = DataProcessor()
    result = processor.process_new_sample(sample_id)

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 400

    return jsonify({
        'success': True,
        'sample_id': sample_id,
        'analysis_id': result.get('analysis_id'),
        'contamination_type': result.get('contamination_type'),
        'severity': result.get('severity'),
        'ml_prediction': result.get('ml_prediction'),
        'site_risk': result.get('site_risk')
    })


@ml_api_bp.route('/pipeline/process-sensor-reading', methods=['POST'])
@login_required
def process_sensor_reading():
    """Process IoT sensor reading through ML pipeline"""
    data = request.get_json()

    # Create sensor reading
    reading = SensorReading(
        sensor_id=data.get('sensor_id'),
        site_id=data.get('site_id'),
        ph=data.get('ph'),
        tds_ppm=data.get('tds'),
        turbidity_ntu=data.get('turbidity'),
        free_chlorine_mg_l=data.get('chlorine'),
        temperature_celsius=data.get('temperature'),
        is_valid=True
    )
    db.session.add(reading)
    db.session.commit()

    # Process through pipeline
    processor = DataProcessor()
    result = processor.process_sensor_reading(reading)

    return jsonify({
        'success': True,
        'reading_id': reading.id,
        'wqi': result.get('wqi'),
        'anomaly': result.get('anomaly')
    })
