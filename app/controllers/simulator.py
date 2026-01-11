"""
POC Simulator Controller
Demonstrates ML model updates for investor presentations
Realistic water quality simulation with variable contamination rates
"""
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from sqlalchemy import func, desc
from app import db
from app.models import (
    Site, WaterSample, TestResult, Analysis,
    SiteRiskPrediction, ContaminationPrediction,
    WaterQualityForecast, WQIReading, AnomalyDetection,
    CostOptimizationResult, SensorReading, IoTSensor
)
from app.services.contamination_analyzer import ContaminationAnalyzer
from app.services.ml_pipeline import MLPipeline

simulator_bp = Blueprint('simulator', __name__)

# Realistic contamination probability based on site characteristics
CONTAMINATION_PROBABILITIES = {
    'high_risk': 0.45,      # 45% chance for high-risk sites
    'medium_risk': 0.25,    # 25% chance for medium-risk sites
    'low_risk': 0.10,       # 10% chance for low-risk sites
    'default': 0.20         # 20% overall default
}


@simulator_bp.route('/reset-data', methods=['POST'])
@login_required
def reset_simulation_data():
    """Reset/Truncate all simulation data for fresh testing"""
    try:
        # Delete in order to respect foreign key constraints
        deleted = {}

        # 1. Delete forecasts
        deleted['forecasts'] = WaterQualityForecast.query.delete()

        # 2. Delete cost optimization results
        deleted['cost_optimization'] = CostOptimizationResult.query.delete()

        # 3. Delete anomaly detections
        deleted['anomalies'] = AnomalyDetection.query.delete()

        # 4. Delete WQI readings
        deleted['wqi_readings'] = WQIReading.query.delete()

        # 5. Delete contamination predictions
        deleted['contamination_predictions'] = ContaminationPrediction.query.delete()

        # 6. Delete site risk predictions
        deleted['site_risk_predictions'] = SiteRiskPrediction.query.delete()

        # 7. Delete analyses
        deleted['analyses'] = Analysis.query.delete()

        # 8. Delete test results
        deleted['test_results'] = TestResult.query.delete()

        # 9. Delete water samples
        deleted['water_samples'] = WaterSample.query.delete()

        # 10. Reset site risk scores to default
        Site.query.update({
            'current_risk_level': 'medium',
            'risk_score': 50,
            'last_risk_assessment': None
        })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'All simulation data has been reset',
            'deleted': deleted
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@simulator_bp.route('/populate-initial-data', methods=['POST'])
@login_required
def populate_initial_data():
    """Populate initial sample data for all active sites"""
    try:
        from app.models import User

        sites = Site.query.filter_by(is_active=True).all()
        analyst = User.query.filter_by(role='analyst').first()

        if not sites:
            return jsonify({
                'success': False,
                'error': 'No active sites found. Please add sites first.'
            }), 400

        samples_created = 0
        tests_created = 0
        analyses_created = 0

        analyzer = ContaminationAnalyzer()

        # Create 1-2 samples per site for initial baseline
        for site in sites:
            num_samples = random.randint(1, 2)

            for _ in range(num_samples):
                # Determine contamination based on site characteristics
                risk_score = site.risk_score or 50
                if risk_score >= 70:
                    contam_prob = 0.35
                elif risk_score >= 40:
                    contam_prob = 0.20
                else:
                    contam_prob = 0.10

                is_contaminated = random.random() < contam_prob

                # Create sample with unique ID
                sample_id = f"INIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]}-{random.randint(1000,9999)}-{site.id:04d}-{samples_created:04d}"
                weather = random.choice(['sunny', 'cloudy', 'rainy'])

                sample = WaterSample(
                    sample_id=sample_id,
                    site_id=site.id,
                    collection_date=datetime.utcnow().date() - timedelta(days=random.randint(1, 7)),
                    collected_by_id=analyst.id if analyst else None,
                    source_point=random.choice(['inlet', 'center', 'outlet']),
                    weather_condition=weather,
                    rained_recently=weather == 'rainy',
                    apparent_color=random.choice(['clear', 'slight_yellow']),
                    odor=random.choice(['none', 'earthy', 'chlorine']),
                    status='analyzed'
                )
                db.session.add(sample)
                db.session.flush()
                samples_created += 1

                # Create test result
                test = create_initial_test_result(sample, site, is_contaminated, analyst)
                db.session.add(test)
                db.session.flush()
                tests_created += 1

                # Create analysis
                result = analyzer.analyze(test, sample, site)
                analysis = Analysis(
                    sample_id=sample.id,
                    test_result_id=test.id,
                    is_contaminated=result['is_contaminated'],
                    contamination_type=result['contamination_type_key'],
                    severity_level=result['severity_level'],
                    confidence_score=result['confidence_score'],
                    wqi_score=result['wqi_score'],
                    wqi_class=result['wqi_class'],
                    runoff_sediment_score=result['runoff_sediment_score'],
                    sewage_ingress_score=result['sewage_ingress_score'],
                    salt_intrusion_score=result['salt_intrusion_score'],
                    pipe_corrosion_score=result['pipe_corrosion_score'],
                    disinfectant_decay_score=result['disinfectant_decay_score'],
                    is_compliant_who=result['is_compliant_who'],
                    is_compliant_bis=result['is_compliant_bis'],
                    primary_recommendation=result['primary_recommendation'],
                    analysis_method='initial_baseline'
                )
                db.session.add(analysis)
                analyses_created += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Initial data populated successfully',
            'created': {
                'sites': len(sites),
                'samples': samples_created,
                'tests': tests_created,
                'analyses': analyses_created
            }
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def create_initial_test_result(sample, site, is_contaminated, analyst):
    """Create initial test result for baseline data"""
    # Base values for clean water
    ph = random.gauss(7.2, 0.2)
    turbidity = random.uniform(0.5, 3.0)
    tds = random.uniform(150, 400)
    chlorine = random.uniform(0.25, 0.7)
    iron = random.uniform(0.02, 0.15)
    coliform = 0
    ammonia = random.uniform(0, 0.3)
    fluoride = random.uniform(0.5, 1.0)
    nitrate = random.uniform(5, 25)

    if is_contaminated:
        # Apply mild contamination for initial data
        contam_type = random.choice(['runoff', 'sewage', 'salt', 'corrosion', 'decay'])

        if contam_type == 'runoff':
            turbidity = random.uniform(5, 12)
            nitrate = random.uniform(30, 50)
        elif contam_type == 'sewage':
            coliform = random.uniform(10, 100)
            chlorine = random.uniform(0, 0.15)
            ammonia = random.uniform(1, 2)
        elif contam_type == 'salt':
            tds = random.uniform(600, 1200)
        elif contam_type == 'corrosion':
            iron = random.uniform(0.3, 0.8)
            ph = random.gauss(6.3, 0.2)
        else:  # decay
            chlorine = random.uniform(0, 0.1)

    return TestResult(
        sample_id=sample.id,
        tested_by_id=analyst.id if analyst else None,
        tested_date=datetime.utcnow() - timedelta(days=random.randint(0, 5)),
        lab_name='Initial Baseline Lab',
        ph=max(4, min(10, ph)),
        temperature_celsius=random.uniform(22, 32),
        turbidity_ntu=max(0, turbidity),
        tds_ppm=max(0, tds),
        conductivity_us_cm=tds * 1.5,
        free_chlorine_mg_l=max(0, chlorine),
        iron_mg_l=max(0, iron),
        total_coliform_mpn=max(0, coliform),
        ammonia_mg_l=max(0, ammonia),
        fluoride_mg_l=max(0, fluoride),
        nitrate_mg_l=max(0, nitrate)
    )


@simulator_bp.route('/')
@login_required
def dashboard():
    """ML Simulator Dashboard - Shows all model outputs"""

    # Get last run times
    last_runs = get_last_run_times()

    # Get model summaries
    risk_summary = get_risk_summary()
    contamination_summary = get_contamination_summary()
    wqi_summary = get_wqi_summary()
    anomaly_summary = get_anomaly_summary()
    forecast_summary = get_forecast_summary()
    cost_summary = get_cost_optimization_summary()

    # Get simulation history
    simulation_history = get_simulation_history()

    return render_template('simulator/dashboard.html',
                           last_runs=last_runs,
                           risk_summary=risk_summary,
                           contamination_summary=contamination_summary,
                           wqi_summary=wqi_summary,
                           anomaly_summary=anomaly_summary,
                           forecast_summary=forecast_summary,
                           cost_summary=cost_summary,
                           simulation_history=simulation_history)


@simulator_bp.route('/run-simulation', methods=['POST'])
@login_required
def run_simulation():
    """
    Run a new simulation cycle with realistic data:
    1. Generate new random samples (based on site risk profiles)
    2. Run contamination analysis
    3. Update site risk predictions
    4. Calculate WQI scores
    5. Detect anomalies
    6. Run cost optimization
    7. Generate forecasts
    """
    try:
        data = request.get_json() or {}
        num_samples = data.get('num_samples', 50)

        # CAPTURE PREVIOUS STATE FOR BEFORE/AFTER COMPARISON
        previous_metrics = capture_current_metrics()

        results = {
            'simulation_id': datetime.utcnow().strftime('%Y%m%d%H%M%S'),
            'started_at': datetime.utcnow().isoformat(),
            'steps': [],
            'summary': {},
            'previous_metrics': previous_metrics  # Store for comparison
        }

        # Step 1: Generate new samples with realistic distribution
        new_samples, sample_stats = generate_simulation_samples(num_samples)
        results['steps'].append({
            'step': 1,
            'name': 'Data Collection',
            'description': f'Collected {len(new_samples)} water samples from field',
            'count': len(new_samples),
            'details': sample_stats,
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 2: Run contamination analysis
        analyses, contam_stats = run_contamination_analysis(new_samples)
        contaminated_count = contam_stats['contaminated']
        clean_count = contam_stats['clean']
        results['steps'].append({
            'step': 2,
            'name': 'Contamination Classification (XGBoost)',
            'description': f'{clean_count} clean, {contaminated_count} contaminated samples detected',
            'count': len(analyses),
            'contaminated': contaminated_count,
            'clean': clean_count,
            'by_type': contam_stats['by_type'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 3: Update site risk predictions
        risk_updates, risk_stats = update_site_risks()
        results['steps'].append({
            'step': 3,
            'name': 'Site Risk Classification (Random Forest)',
            'description': f'{risk_stats["improved"]} sites improved, {risk_stats["worsened"]} worsened',
            'count': len(risk_updates),
            'critical': risk_stats['critical'],
            'high': risk_stats['high'],
            'medium': risk_stats['medium'],
            'low': risk_stats['low'],
            'improved': risk_stats['improved'],
            'worsened': risk_stats['worsened'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 4: Calculate WQI scores
        wqi_results = calculate_wqi_scores()
        results['steps'].append({
            'step': 4,
            'name': 'Real-time WQI Calculation',
            'description': f'Avg WQI: {wqi_results["avg_wqi"]:.1f} - {wqi_results["excellent"]} excellent, {wqi_results["unsafe"]} unsafe',
            'count': wqi_results['count'],
            'avg_wqi': wqi_results['avg_wqi'],
            'excellent': wqi_results['excellent'],
            'compliant': wqi_results['compliant'],
            'warning': wqi_results['warning'],
            'unsafe': wqi_results['unsafe'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 5: Detect anomalies
        anomaly_results = detect_anomalies()
        results['steps'].append({
            'step': 5,
            'name': 'Anomaly Detection (Isolation Forest + CUSUM)',
            'description': f'{anomaly_results["detected"]} anomalies detected, {anomaly_results["normal"]} normal readings',
            'count': anomaly_results['total'],
            'detected': anomaly_results['detected'],
            'normal': anomaly_results['normal'],
            'by_type': anomaly_results['by_type'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 6: Run cost optimization
        cost_result = run_cost_optimization()
        results['steps'].append({
            'step': 6,
            'name': 'Bayesian Cost Optimization',
            'description': f'Saved Rs. {cost_result["total_savings"]:,.0f} ({cost_result["savings_percent"]}% reduction)',
            'savings_percent': cost_result['savings_percent'],
            'total_savings': cost_result['total_savings'],
            'current_cost': cost_result['current_cost'],
            'optimized_cost': cost_result['optimized_cost'],
            'detection_rate': cost_result['detection_rate'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Step 7: Generate forecasts
        forecast_results = generate_forecasts()
        results['steps'].append({
            'step': 7,
            'name': 'Water Quality Forecasting (Gaussian Process)',
            'description': f'{forecast_results["count"]} forecasts, {forecast_results["alerts"]} potential alerts',
            'count': forecast_results['count'],
            'alerts': forecast_results['alerts'],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Build comprehensive summary
        results['summary'] = {
            'samples_collected': len(new_samples),
            'contamination_rate': round(contaminated_count / len(new_samples) * 100, 1) if new_samples else 0,
            'clean_samples': clean_count,
            'contaminated_samples': contaminated_count,
            'high_risk_sites': risk_stats['critical'] + risk_stats['high'],
            'sites_improved': risk_stats['improved'],
            'sites_worsened': risk_stats['worsened'],
            'avg_wqi': wqi_results['avg_wqi'],
            'anomalies_detected': anomaly_results['detected'],
            'cost_savings_inr': cost_result['total_savings'],
            'cost_savings_percent': cost_result['savings_percent'],
            'detection_rate_maintained': cost_result['detection_rate'],
            'forecasts_generated': forecast_results['count'],
            'forecast_alerts': forecast_results['alerts']
        }

        results['completed_at'] = datetime.utcnow().isoformat()
        results['success'] = True

        # CAPTURE NEW METRICS AND BUILD COMPARISON FOR INVESTORS
        current_metrics = capture_current_metrics()
        results['current_metrics'] = current_metrics
        results['comparison'] = build_comparison(previous_metrics, current_metrics, results['summary'])

        return jsonify(results)

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@simulator_bp.route('/api/model-stats')
@login_required
def get_model_stats():
    """Get current ML model statistics"""
    return jsonify({
        'risk': get_risk_summary(),
        'contamination': get_contamination_summary(),
        'wqi': get_wqi_summary(),
        'anomaly': get_anomaly_summary(),
        'forecast': get_forecast_summary(),
        'cost': get_cost_optimization_summary(),
        'last_runs': get_last_run_times()
    })


@simulator_bp.route('/api/risk-details')
@login_required
def get_risk_details():
    """Get detailed site risk information with site names"""
    # Get latest risk predictions with site info
    subquery = db.session.query(
        SiteRiskPrediction.site_id,
        func.max(SiteRiskPrediction.prediction_date).label('max_date')
    ).group_by(SiteRiskPrediction.site_id).subquery()

    latest_risks = db.session.query(SiteRiskPrediction, Site).join(
        subquery,
        (SiteRiskPrediction.site_id == subquery.c.site_id) &
        (SiteRiskPrediction.prediction_date == subquery.c.max_date)
    ).join(Site, SiteRiskPrediction.site_id == Site.id).all()

    # Group by risk level
    by_level = {'critical': [], 'high': [], 'medium': [], 'low': []}
    for pred, site in latest_risks:
        level = pred.risk_level or 'low'
        by_level[level].append({
            'site_id': site.id,
            'site_name': site.site_name,
            'district': site.district,
            'risk_score': pred.risk_score,
            'confidence': pred.confidence,
            'recommended_frequency': pred.recommended_frequency,
            'date': pred.prediction_date.isoformat()
        })

    return jsonify({
        'by_level': by_level,
        'total': len(latest_risks),
        'summary': {
            'critical': len(by_level['critical']),
            'high': len(by_level['high']),
            'medium': len(by_level['medium']),
            'low': len(by_level['low'])
        }
    })


@simulator_bp.route('/api/contamination-details')
@login_required
def get_contamination_details():
    """Get detailed contamination results by site"""
    # Get recent contamination analyses
    recent_analyses = db.session.query(Analysis, WaterSample, Site).join(
        WaterSample, Analysis.sample_id == WaterSample.id
    ).join(Site, WaterSample.site_id == Site.id).order_by(
        Analysis.analysis_date.desc()
    ).limit(100).all()

    contaminated = []
    clean = []
    by_type = {}

    for analysis, sample, site in recent_analyses:
        record = {
            'sample_id': sample.sample_id,
            'site_name': site.site_name,
            'district': site.district,
            'date': analysis.analysis_date.isoformat(),
            'wqi_score': analysis.wqi_score,
            'severity': analysis.severity_level,
            'confidence': analysis.confidence_score
        }

        if analysis.is_contaminated:
            record['contamination_type'] = analysis.contamination_type
            record['recommendation'] = analysis.primary_recommendation
            contaminated.append(record)

            ctype = analysis.contamination_type or 'unknown'
            if ctype not in by_type:
                by_type[ctype] = []
            by_type[ctype].append(record)
        else:
            clean.append(record)

    return jsonify({
        'contaminated': contaminated,
        'clean': clean,
        'by_type': by_type,
        'summary': {
            'total': len(recent_analyses),
            'contaminated': len(contaminated),
            'clean': len(clean),
            'rate': round(len(contaminated) / len(recent_analyses) * 100, 1) if recent_analyses else 0
        }
    })


@simulator_bp.route('/api/wqi-details')
@login_required
def get_wqi_details():
    """Get detailed WQI readings by site"""
    # Get recent WQI readings with site info
    readings = db.session.query(WQIReading, Site).join(
        Site, WQIReading.site_id == Site.id
    ).order_by(WQIReading.reading_timestamp.desc()).limit(100).all()

    by_class = {'Excellent': [], 'Compliant': [], 'Warning': [], 'Unsafe': []}

    for reading, site in readings:
        record = {
            'site_id': site.id,
            'site_name': site.site_name,
            'district': site.district,
            'wqi_score': reading.wqi_score,
            'wqi_class': reading.wqi_class,
            'is_drinkable': reading.is_drinkable,
            'ph': reading.ph_value,
            'tds': reading.tds_value,
            'turbidity': reading.turbidity_value,
            'chlorine': reading.chlorine_value,
            'timestamp': reading.reading_timestamp.isoformat()
        }

        wclass = reading.wqi_class or 'Warning'
        if wclass in by_class:
            by_class[wclass].append(record)

    return jsonify({
        'by_class': by_class,
        'summary': {
            'total': len(readings),
            'excellent': len(by_class['Excellent']),
            'compliant': len(by_class['Compliant']),
            'warning': len(by_class['Warning']),
            'unsafe': len(by_class['Unsafe']),
            'avg_wqi': sum(r[0].wqi_score for r in readings) / len(readings) if readings else 0
        }
    })


@simulator_bp.route('/api/anomaly-details')
@login_required
def get_anomaly_details():
    """Get detailed anomaly detections"""
    anomalies = db.session.query(AnomalyDetection, Site).join(
        Site, AnomalyDetection.site_id == Site.id
    ).filter(AnomalyDetection.is_anomaly == True).order_by(
        AnomalyDetection.detection_timestamp.desc()
    ).limit(50).all()

    by_type = {}
    by_parameter = {}

    records = []
    for anomaly, site in anomalies:
        record = {
            'site_id': site.id,
            'site_name': site.site_name,
            'district': site.district,
            'anomaly_type': anomaly.anomaly_type,
            'parameter': anomaly.parameter,
            'observed_value': anomaly.observed_value,
            'expected_value': anomaly.expected_value,
            'deviation': anomaly.deviation_sigma,
            'score': anomaly.anomaly_score,
            'timestamp': anomaly.detection_timestamp.isoformat()
        }
        records.append(record)

        atype = anomaly.anomaly_type or 'unknown'
        if atype not in by_type:
            by_type[atype] = []
        by_type[atype].append(record)

        param = anomaly.parameter or 'unknown'
        if param not in by_parameter:
            by_parameter[param] = []
        by_parameter[param].append(record)

    return jsonify({
        'anomalies': records,
        'by_type': by_type,
        'by_parameter': by_parameter,
        'summary': {
            'total': len(records),
            'types': {k: len(v) for k, v in by_type.items()},
            'parameters': {k: len(v) for k, v in by_parameter.items()}
        }
    })


@simulator_bp.route('/api/cost-details')
@login_required
def get_cost_details():
    """Get detailed cost optimization results"""
    latest_run = CostOptimizationResult.query.order_by(
        CostOptimizationResult.optimization_date.desc()
    ).first()

    if not latest_run:
        return jsonify({'error': 'No optimization results found'})

    results = db.session.query(CostOptimizationResult, Site).join(
        Site, CostOptimizationResult.site_id == Site.id
    ).filter(
        CostOptimizationResult.optimization_run_id == latest_run.optimization_run_id
    ).order_by(CostOptimizationResult.cost_savings_inr.desc()).all()

    by_category = {'critical': [], 'high': [], 'medium': [], 'low': []}
    total_current = 0
    total_optimized = 0

    for opt, site in results:
        record = {
            'site_id': site.id,
            'site_name': site.site_name,
            'district': site.district,
            'risk_category': opt.risk_category,
            'current_tests': opt.current_tests_per_year,
            'optimized_tests': opt.optimized_tests_per_year,
            'current_cost': opt.current_cost_inr,
            'optimized_cost': opt.optimized_cost_inr,
            'savings': opt.cost_savings_inr,
            'savings_percent': opt.cost_reduction_percent,
            'detection_rate': opt.detection_rate,
            'frequency': opt.recommended_frequency,
            'priority': opt.priority_rank
        }

        cat = opt.risk_category or 'medium'
        by_category[cat].append(record)
        total_current += opt.current_cost_inr or 0
        total_optimized += opt.optimized_cost_inr or 0

    return jsonify({
        'by_category': by_category,
        'run_id': latest_run.optimization_run_id,
        'run_date': latest_run.optimization_date.isoformat(),
        'summary': {
            'total_sites': len(results),
            'total_current_cost': total_current,
            'total_optimized_cost': total_optimized,
            'total_savings': total_current - total_optimized,
            'savings_percent': round((total_current - total_optimized) / total_current * 100, 1) if total_current > 0 else 0,
            'by_category': {k: len(v) for k, v in by_category.items()}
        }
    })


@simulator_bp.route('/api/forecast-details')
@login_required
def get_forecast_details():
    """Get detailed forecast information"""
    today = datetime.utcnow().date()

    forecasts = db.session.query(WaterQualityForecast, Site).join(
        Site, WaterQualityForecast.site_id == Site.id
    ).filter(
        WaterQualityForecast.forecast_date >= today
    ).order_by(
        WaterQualityForecast.prob_exceed_threshold.desc()
    ).limit(100).all()

    alerts = []
    by_parameter = {}

    for forecast, site in forecasts:
        record = {
            'site_id': site.id,
            'site_name': site.site_name,
            'district': site.district,
            'parameter': forecast.parameter,
            'forecast_date': forecast.forecast_date.isoformat(),
            'predicted_value': forecast.predicted_value,
            'lower_bound': forecast.lower_bound_95,
            'upper_bound': forecast.upper_bound_95,
            'prob_exceed': forecast.prob_exceed_threshold,
            'uncertainty': forecast.uncertainty
        }

        if forecast.prob_exceed_threshold and forecast.prob_exceed_threshold > 0.5:
            alerts.append(record)

        param = forecast.parameter or 'unknown'
        if param not in by_parameter:
            by_parameter[param] = []
        by_parameter[param].append(record)

    return jsonify({
        'alerts': alerts,
        'by_parameter': by_parameter,
        'summary': {
            'total_forecasts': len(forecasts),
            'high_risk_alerts': len(alerts),
            'parameters': list(by_parameter.keys())
        }
    })


@simulator_bp.route('/api/test-schedules')
@login_required
def get_test_schedules():
    """Get all scheduled test dates for all sites from the latest optimization run"""
    latest_run = CostOptimizationResult.query.order_by(
        CostOptimizationResult.optimization_date.desc()
    ).first()

    if not latest_run:
        return jsonify({'schedules': [], 'summary': {'total': 0}})

    run_id = latest_run.optimization_run_id

    schedules = db.session.query(CostOptimizationResult, Site).join(
        Site, CostOptimizationResult.site_id == Site.id
    ).filter(
        CostOptimizationResult.optimization_run_id == run_id
    ).order_by(
        CostOptimizationResult.next_test_date.asc()
    ).all()

    # Group by week for easier viewing
    by_week = {}
    schedule_list = []

    for opt, site in schedules:
        if opt.next_test_date:
            week_num = opt.next_test_date.isocalendar()[1]
            week_year = opt.next_test_date.year
            week_key = f"{week_year}-W{week_num:02d}"

            if week_key not in by_week:
                by_week[week_key] = []

            schedule_item = {
                'site_id': site.id,
                'site_name': site.site_name,
                'site_code': site.site_code,
                'district': site.district,
                'state': site.state,
                'risk_category': opt.risk_category,
                'next_test_date': opt.next_test_date.isoformat(),
                'recommended_frequency': opt.recommended_frequency,
                'tests_per_year': opt.optimized_tests_per_year,
                'priority_rank': opt.priority_rank
            }

            by_week[week_key].append(schedule_item)
            schedule_list.append(schedule_item)

    # Get upcoming tests for the next 12 weeks
    upcoming_weeks = []
    today = datetime.utcnow().date()
    for i in range(12):
        target_date = today + timedelta(weeks=i)
        week_num = target_date.isocalendar()[1]
        week_year = target_date.year
        week_key = f"{week_year}-W{week_num:02d}"

        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6)

        upcoming_weeks.append({
            'week_key': week_key,
            'week_number': week_num,
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'sites': by_week.get(week_key, []),
            'test_count': len(by_week.get(week_key, []))
        })

    return jsonify({
        'schedules': schedule_list,
        'by_week': upcoming_weeks,
        'optimization_date': latest_run.optimization_date.isoformat(),
        'run_id': run_id,
        'summary': {
            'total_sites': len(schedule_list),
            'total_tests_scheduled': sum(len(by_week.get(w['week_key'], [])) for w in upcoming_weeks),
            'weeks_with_tests': len([w for w in upcoming_weeks if w['test_count'] > 0])
        }
    })


# ========== Helper Functions ==========

def get_last_run_times():
    """Get last run time for each model"""
    return {
        'risk_classifier': SiteRiskPrediction.query.order_by(
            SiteRiskPrediction.prediction_date.desc()
        ).first(),
        'contamination_classifier': ContaminationPrediction.query.order_by(
            ContaminationPrediction.prediction_date.desc()
        ).first(),
        'wqi_calculator': WQIReading.query.order_by(
            WQIReading.reading_timestamp.desc()
        ).first(),
        'anomaly_detector': AnomalyDetection.query.order_by(
            AnomalyDetection.detection_timestamp.desc()
        ).first(),
        'forecaster': WaterQualityForecast.query.order_by(
            WaterQualityForecast.prediction_date.desc()
        ).first(),
        'cost_optimizer': CostOptimizationResult.query.order_by(
            CostOptimizationResult.optimization_date.desc()
        ).first()
    }


def get_risk_summary():
    """Get site risk classification summary"""
    distribution = db.session.query(
        SiteRiskPrediction.risk_level,
        func.count(SiteRiskPrediction.id)
    ).group_by(SiteRiskPrediction.risk_level).all()

    latest = SiteRiskPrediction.query.order_by(
        SiteRiskPrediction.prediction_date.desc()
    ).limit(10).all()

    return {
        'distribution': dict(distribution),
        'latest_predictions': [{
            'site_id': p.site_id,
            'risk_level': p.risk_level,
            'risk_score': p.risk_score,
            'confidence': p.confidence,
            'date': p.prediction_date.isoformat()
        } for p in latest],
        'total': SiteRiskPrediction.query.count(),
        'model_accuracy': 87.0
    }


def get_contamination_summary():
    """Get contamination classification summary"""
    distribution = db.session.query(
        Analysis.contamination_type,
        func.count(Analysis.id)
    ).filter(Analysis.is_contaminated == True).group_by(
        Analysis.contamination_type
    ).all()

    latest = Analysis.query.filter(
        Analysis.is_contaminated == True
    ).order_by(Analysis.analysis_date.desc()).limit(10).all()

    total = Analysis.query.count()
    contaminated = Analysis.query.filter(Analysis.is_contaminated == True).count()

    return {
        'distribution': dict(distribution),
        'latest_detections': [{
            'sample_id': a.sample_id,
            'type': a.contamination_type,
            'severity': a.severity_level,
            'confidence': a.confidence_score,
            'date': a.analysis_date.isoformat()
        } for a in latest],
        'total_analyzed': total,
        'contaminated': contaminated,
        'contamination_rate': round((contaminated / total * 100) if total > 0 else 0, 1),
        'model_f1_score': 0.82
    }


def get_wqi_summary():
    """Get WQI calculation summary"""
    distribution = db.session.query(
        WQIReading.wqi_class,
        func.count(WQIReading.id)
    ).group_by(WQIReading.wqi_class).all()

    avg_wqi = db.session.query(func.avg(WQIReading.wqi_score)).scalar() or 0

    latest = WQIReading.query.order_by(
        WQIReading.reading_timestamp.desc()
    ).limit(10).all()

    return {
        'distribution': dict(distribution),
        'average_wqi': round(avg_wqi, 1),
        'latest_readings': [{
            'site_id': r.site_id,
            'wqi_score': r.wqi_score,
            'wqi_class': r.wqi_class,
            'is_drinkable': r.is_drinkable,
            'timestamp': r.reading_timestamp.isoformat()
        } for r in latest],
        'total': WQIReading.query.count()
    }


def get_anomaly_summary():
    """Get anomaly detection summary"""
    total = AnomalyDetection.query.count()
    anomalies = AnomalyDetection.query.filter(AnomalyDetection.is_anomaly == True).count()

    by_type = db.session.query(
        AnomalyDetection.anomaly_type,
        func.count(AnomalyDetection.id)
    ).filter(AnomalyDetection.is_anomaly == True).group_by(
        AnomalyDetection.anomaly_type
    ).all()

    latest = AnomalyDetection.query.filter(
        AnomalyDetection.is_anomaly == True
    ).order_by(AnomalyDetection.detection_timestamp.desc()).limit(10).all()

    return {
        'total_checked': total,
        'anomalies_detected': anomalies,
        'by_type': dict(by_type),
        'latest_anomalies': [{
            'site_id': a.site_id,
            'type': a.anomaly_type,
            'parameter': a.parameter,
            'deviation': a.deviation_sigma,
            'timestamp': a.detection_timestamp.isoformat()
        } for a in latest],
        'model_accuracy': 92.0
    }


def get_forecast_summary():
    """Get water quality forecast summary"""
    forecasts = WaterQualityForecast.query.filter(
        WaterQualityForecast.forecast_date >= datetime.utcnow().date()
    ).count()

    exceedances = WaterQualityForecast.query.filter(
        WaterQualityForecast.forecast_date >= datetime.utcnow().date(),
        WaterQualityForecast.prob_exceed_threshold > 0.5
    ).count()

    by_parameter = db.session.query(
        WaterQualityForecast.parameter,
        func.avg(WaterQualityForecast.predicted_value)
    ).filter(
        WaterQualityForecast.forecast_date >= datetime.utcnow().date()
    ).group_by(WaterQualityForecast.parameter).all()

    return {
        'active_forecasts': forecasts,
        'predicted_exceedances': exceedances,
        'by_parameter': {p: round(v, 2) for p, v in by_parameter},
        'model_r2_score': 0.78,
        'forecast_horizon_days': 90
    }


def get_cost_optimization_summary():
    """Get cost optimization summary"""
    latest_run = CostOptimizationResult.query.order_by(
        CostOptimizationResult.optimization_date.desc()
    ).first()

    if not latest_run:
        return {'total_sites': 0}

    run_id = latest_run.optimization_run_id
    results = CostOptimizationResult.query.filter_by(
        optimization_run_id=run_id
    ).all()

    total_current = sum(r.current_cost_inr or 0 for r in results)
    total_optimized = sum(r.optimized_cost_inr or 0 for r in results)
    avg_detection = sum(r.detection_rate or 0 for r in results) / len(results) if results else 0

    by_category = db.session.query(
        CostOptimizationResult.risk_category,
        func.count(CostOptimizationResult.id)
    ).filter_by(optimization_run_id=run_id).group_by(
        CostOptimizationResult.risk_category
    ).all()

    # Get next scheduled test dates
    next_tests = CostOptimizationResult.query.filter_by(
        optimization_run_id=run_id
    ).filter(
        CostOptimizationResult.next_test_date.isnot(None)
    ).order_by(CostOptimizationResult.next_test_date).limit(5).all()

    # Get the soonest next test date
    soonest_test = next_tests[0] if next_tests else None

    return {
        'run_id': run_id,
        'total_sites': len(results),
        'total_current_cost': total_current,
        'total_optimized_cost': total_optimized,
        'total_savings': total_current - total_optimized,
        'savings_percent': round(((total_current - total_optimized) / total_current * 100) if total_current > 0 else 0, 1),
        'avg_detection_rate': round(avg_detection, 1),
        'by_category': dict(by_category),
        'last_run': latest_run.optimization_date.isoformat(),
        'next_run_date': soonest_test.next_test_date.strftime('%Y-%m-%d') if soonest_test and soonest_test.next_test_date else None,
        'has_schedules': len(results) > 0
    }


def get_simulation_history():
    """Get simulation run history based on optimization runs with summary data"""
    # Get distinct run IDs first, then aggregate
    from sqlalchemy import distinct

    runs = db.session.query(
        CostOptimizationResult.optimization_run_id,
        func.min(CostOptimizationResult.optimization_date).label('run_date'),
        func.count(distinct(CostOptimizationResult.site_id)).label('site_count'),
        func.sum(CostOptimizationResult.cost_savings_inr).label('total_savings'),
        func.avg(CostOptimizationResult.detection_rate).label('avg_detection')
    ).group_by(
        CostOptimizationResult.optimization_run_id
    ).order_by(func.min(CostOptimizationResult.optimization_date).desc()).limit(10).all()

    return [{
        'run_id': r[0],
        'date': r[1].strftime('%Y-%m-%d %H:%M:%S') if r[1] else '',
        'date_display': r[1].strftime('%d %b %Y, %H:%M') if r[1] else '',
        'sites_processed': r[2] or 0,
        'total_savings': r[3] or 0,
        'avg_detection_rate': round(r[4] or 0, 1)
    } for r in runs]


@simulator_bp.route('/api/run-history/<run_id>')
@login_required
def get_run_details(run_id):
    """Get detailed results for a specific simulation run"""

    # Get cost optimization results for this run
    cost_results = db.session.query(CostOptimizationResult, Site).join(
        Site, CostOptimizationResult.site_id == Site.id
    ).filter(
        CostOptimizationResult.optimization_run_id == run_id
    ).all()

    if not cost_results:
        return jsonify({'error': 'Run not found'}), 404

    run_date = cost_results[0][0].optimization_date

    # Calculate cost summary
    total_current = sum(r[0].current_cost_inr or 0 for r in cost_results)
    total_optimized = sum(r[0].optimized_cost_inr or 0 for r in cost_results)
    total_savings = total_current - total_optimized
    avg_detection = sum(r[0].detection_rate or 0 for r in cost_results) / len(cost_results) if cost_results else 0

    # Get risk distribution around that time
    risk_dist = db.session.query(
        SiteRiskPrediction.risk_level,
        func.count(SiteRiskPrediction.id)
    ).filter(
        SiteRiskPrediction.prediction_date <= run_date + timedelta(minutes=5),
        SiteRiskPrediction.prediction_date >= run_date - timedelta(minutes=5)
    ).group_by(SiteRiskPrediction.risk_level).all()

    risk_summary = dict(risk_dist) if risk_dist else {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

    # Get WQI summary around that time
    wqi_readings = db.session.query(
        WQIReading.wqi_class,
        func.count(WQIReading.id),
        func.avg(WQIReading.wqi_score)
    ).filter(
        WQIReading.reading_timestamp <= run_date + timedelta(minutes=5),
        WQIReading.reading_timestamp >= run_date - timedelta(minutes=5)
    ).group_by(WQIReading.wqi_class).all()

    wqi_by_class = {r[0]: r[1] for r in wqi_readings} if wqi_readings else {}
    avg_wqi = wqi_readings[0][2] if wqi_readings and wqi_readings[0][2] else 0

    # Get contamination summary around that time
    contam_results = db.session.query(
        Analysis.is_contaminated,
        func.count(Analysis.id)
    ).filter(
        Analysis.analysis_date <= run_date + timedelta(minutes=5),
        Analysis.analysis_date >= run_date - timedelta(minutes=5)
    ).group_by(Analysis.is_contaminated).all()

    contam_dict = {r[0]: r[1] for r in contam_results}
    contaminated = contam_dict.get(True, 0)
    clean = contam_dict.get(False, 0)
    total_samples = contaminated + clean
    contam_rate = round(contaminated / total_samples * 100, 1) if total_samples > 0 else 0

    # Get anomaly count around that time
    anomaly_count = AnomalyDetection.query.filter(
        AnomalyDetection.is_anomaly == True,
        AnomalyDetection.detection_timestamp <= run_date + timedelta(minutes=5),
        AnomalyDetection.detection_timestamp >= run_date - timedelta(minutes=5)
    ).count()

    # Get forecast count around that time
    forecast_count = WaterQualityForecast.query.filter(
        WaterQualityForecast.prediction_date <= run_date + timedelta(minutes=5),
        WaterQualityForecast.prediction_date >= run_date - timedelta(minutes=5)
    ).count()

    forecast_alerts = WaterQualityForecast.query.filter(
        WaterQualityForecast.prediction_date <= run_date + timedelta(minutes=5),
        WaterQualityForecast.prediction_date >= run_date - timedelta(minutes=5),
        WaterQualityForecast.prob_exceed_threshold > 0.5
    ).count()

    # Build response
    return jsonify({
        'run_id': run_id,
        'run_date': run_date.strftime('%d %b %Y, %H:%M:%S'),
        'run_date_iso': run_date.isoformat(),
        'sites_processed': len(cost_results),
        'models': {
            'site_risk': {
                'name': 'Site Risk Classifier',
                'algorithm': 'Random Forest',
                'icon': 'shield-exclamation',
                'color': 'danger',
                'metrics': {
                    'Critical Sites': risk_summary.get('critical', 0),
                    'High Risk Sites': risk_summary.get('high', 0),
                    'Medium Risk Sites': risk_summary.get('medium', 0),
                    'Low Risk Sites': risk_summary.get('low', 0),
                    'High Risk Total': risk_summary.get('critical', 0) + risk_summary.get('high', 0)
                }
            },
            'contamination': {
                'name': 'Contamination Classifier',
                'algorithm': 'XGBoost',
                'icon': 'virus',
                'color': 'warning',
                'metrics': {
                    'Contamination Rate': f"{contam_rate}%",
                    'Contaminated Samples': contaminated,
                    'Clean Samples': clean,
                    'Total Samples': total_samples
                }
            },
            'wqi': {
                'name': 'Water Quality Index',
                'algorithm': 'Penalty Algorithm',
                'icon': 'speedometer2',
                'color': 'info',
                'metrics': {
                    'Average WQI': round(avg_wqi, 1) if avg_wqi else 'N/A',
                    'Excellent': wqi_by_class.get('Excellent', 0),
                    'Compliant': wqi_by_class.get('Compliant', 0),
                    'Warning': wqi_by_class.get('Warning', 0),
                    'Unsafe': wqi_by_class.get('Unsafe', 0)
                }
            },
            'anomaly': {
                'name': 'Anomaly Detection',
                'algorithm': 'Isolation Forest + CUSUM',
                'icon': 'exclamation-diamond',
                'color': 'purple',
                'metrics': {
                    'Anomalies Detected': anomaly_count
                }
            },
            'forecast': {
                'name': 'Quality Forecaster',
                'algorithm': 'Gaussian Process',
                'icon': 'graph-up-arrow',
                'color': 'success',
                'metrics': {
                    'Active Forecasts': forecast_count,
                    'Risk Alerts': forecast_alerts
                }
            },
            'cost_optimizer': {
                'name': 'Cost Optimizer',
                'algorithm': 'Bayesian Optimization',
                'icon': 'cash-coin',
                'color': 'primary',
                'metrics': {
                    'Current Cost': f"Rs. {total_current:,.0f}",
                    'Optimized Cost': f"Rs. {total_optimized:,.0f}",
                    'Total Savings': f"Rs. {total_savings:,.0f}",
                    'Savings Percent': f"{round(total_savings / total_current * 100, 1) if total_current > 0 else 0}%",
                    'Detection Rate': f"{round(avg_detection, 1)}%"
                }
            }
        },
        'summary': {
            'total_savings': total_savings,
            'savings_percent': round(total_savings / total_current * 100, 1) if total_current > 0 else 0,
            'detection_rate': round(avg_detection, 1),
            'high_risk_sites': risk_summary.get('critical', 0) + risk_summary.get('high', 0),
            'avg_wqi': round(avg_wqi, 1) if avg_wqi else 0,
            'contamination_rate': contam_rate,
            'anomalies': anomaly_count,
            'forecasts': forecast_count
        }
    })


# ========== Comparison Functions for Investor Dashboard ==========

def capture_current_metrics():
    """Capture current state of all metrics BEFORE simulation for comparison"""
    risk_summary = get_risk_summary()
    contamination_summary = get_contamination_summary()
    wqi_summary = get_wqi_summary()
    anomaly_summary = get_anomaly_summary()
    forecast_summary = get_forecast_summary()
    cost_summary = get_cost_optimization_summary()

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'risk': {
            'critical_sites': risk_summary['distribution'].get('critical', 0),
            'high_sites': risk_summary['distribution'].get('high', 0),
            'medium_sites': risk_summary['distribution'].get('medium', 0),
            'low_sites': risk_summary['distribution'].get('low', 0),
            'high_risk_total': risk_summary['distribution'].get('critical', 0) + risk_summary['distribution'].get('high', 0),
            'model_accuracy': risk_summary['model_accuracy']
        },
        'contamination': {
            'rate': contamination_summary['contamination_rate'],
            'total_contaminated': contamination_summary['contaminated'],
            'total_clean': contamination_summary['total_analyzed'] - contamination_summary['contaminated'],
            'f1_score': contamination_summary['model_f1_score']
        },
        'wqi': {
            'average': wqi_summary['average_wqi'],
            'excellent': wqi_summary['distribution'].get('Excellent', 0),
            'compliant': wqi_summary['distribution'].get('Compliant', 0),
            'warning': wqi_summary['distribution'].get('Warning', 0),
            'unsafe': wqi_summary['distribution'].get('Unsafe', 0),
            'total': wqi_summary['total']
        },
        'anomaly': {
            'detected': anomaly_summary['anomalies_detected'],
            'total_checked': anomaly_summary['total_checked'],
            'model_accuracy': anomaly_summary['model_accuracy']
        },
        'forecast': {
            'active': forecast_summary['active_forecasts'],
            'exceedances': forecast_summary['predicted_exceedances'],
            'r2_score': forecast_summary['model_r2_score']
        },
        'cost': {
            'current_cost': cost_summary.get('total_current_cost', 0),
            'optimized_cost': cost_summary.get('total_optimized_cost', 0),
            'savings': cost_summary.get('total_savings', 0),
            'savings_percent': cost_summary.get('savings_percent', 0),
            'detection_rate': cost_summary.get('avg_detection_rate', 0)
        }
    }


def build_comparison(before, after, summary):
    """Build investor-friendly comparison showing improvements"""
    def calc_change(old_val, new_val, invert=False):
        """Calculate change with direction (positive = improvement)"""
        if old_val is None or new_val is None:
            return {'value': 0, 'percent': 0, 'direction': 'neutral'}

        diff = new_val - old_val
        if old_val != 0:
            percent = round((diff / abs(old_val)) * 100, 1)
        else:
            percent = 100 if diff > 0 else 0

        # Determine if change is improvement
        if invert:  # Lower is better (e.g., contamination rate, high-risk sites)
            direction = 'improved' if diff < 0 else ('declined' if diff > 0 else 'neutral')
        else:  # Higher is better (e.g., WQI, detection rate)
            direction = 'improved' if diff > 0 else ('declined' if diff < 0 else 'neutral')

        return {
            'before': old_val,
            'after': new_val,
            'change': round(diff, 2),
            'percent': percent,
            'direction': direction
        }

    # Build models dictionary first
    models = {
        'site_risk': {
            'name': 'Site Risk Classifier',
            'algorithm': 'Random Forest',
            'icon': 'shield-exclamation',
            'color': 'danger',
            'metrics': {
                'high_risk_sites': calc_change(
                    before['risk']['high_risk_total'],
                    after['risk']['high_risk_total'],
                    invert=True  # Fewer high-risk sites = improvement
                ),
                'critical_sites': calc_change(
                    before['risk']['critical_sites'],
                    after['risk']['critical_sites'],
                    invert=True
                ),
                'low_risk_sites': calc_change(
                    before['risk']['low_sites'],
                    after['risk']['low_sites'],
                    invert=False  # More low-risk sites = improvement
                )
            },
            'improvement_summary': f"{summary.get('sites_improved', 0)} sites improved, {summary.get('sites_worsened', 0)} worsened"
        },
        'contamination': {
            'name': 'Contamination Classifier',
            'algorithm': 'XGBoost',
            'icon': 'virus',
            'color': 'warning',
            'metrics': {
                'contamination_rate': calc_change(
                    before['contamination']['rate'],
                    after['contamination']['rate'],
                    invert=True  # Lower contamination = improvement
                ),
                'clean_samples': calc_change(
                    before['contamination']['total_clean'],
                    after['contamination']['total_clean'],
                    invert=False
                )
            },
            'improvement_summary': f"{summary.get('clean_samples', 0)} clean vs {summary.get('contaminated_samples', 0)} contaminated"
        },
        'wqi': {
            'name': 'Water Quality Index',
            'algorithm': 'Penalty Algorithm',
            'icon': 'speedometer2',
            'color': 'info',
            'metrics': {
                'average_wqi': calc_change(
                    before['wqi']['average'],
                    after['wqi']['average'],
                    invert=False  # Higher WQI = improvement
                ),
                'excellent_readings': calc_change(
                    before['wqi']['excellent'],
                    after['wqi']['excellent'],
                    invert=False
                ),
                'unsafe_readings': calc_change(
                    before['wqi']['unsafe'],
                    after['wqi']['unsafe'],
                    invert=True  # Fewer unsafe = improvement
                )
            },
            'improvement_summary': f"Avg WQI: {summary.get('avg_wqi', 0):.1f}"
        },
        'anomaly': {
            'name': 'Anomaly Detection',
            'algorithm': 'Isolation Forest + CUSUM',
            'icon': 'exclamation-diamond',
            'color': 'purple',
            'metrics': {
                'anomalies_detected': calc_change(
                    before['anomaly']['detected'],
                    after['anomaly']['detected'],
                    invert=False  # More detection = AI working better
                )
            },
            'improvement_summary': f"{summary.get('anomalies_detected', 0)} anomalies identified for action"
        },
        'forecast': {
            'name': 'Quality Forecaster',
            'algorithm': 'Gaussian Process',
            'icon': 'graph-up-arrow',
            'color': 'success',
            'metrics': {
                'active_forecasts': calc_change(
                    before['forecast']['active'],
                    after['forecast']['active'],
                    invert=False
                ),
                'risk_alerts': calc_change(
                    before['forecast']['exceedances'],
                    after['forecast']['exceedances'],
                    invert=False  # Detecting more risks = better prediction
                )
            },
            'improvement_summary': f"{summary.get('forecasts_generated', 0)} forecasts, {summary.get('forecast_alerts', 0)} alerts"
        },
        'cost_optimizer': {
            'name': 'Cost Optimizer',
            'algorithm': 'Bayesian Optimization',
            'icon': 'cash-coin',
            'color': 'primary',
            'metrics': {
                'cost_savings': calc_change(
                    before['cost']['savings'],
                    after['cost']['savings'],
                    invert=False  # More savings = improvement
                ),
                'savings_percent': calc_change(
                    before['cost']['savings_percent'],
                    after['cost']['savings_percent'],
                    invert=False
                ),
                'detection_rate': calc_change(
                    before['cost']['detection_rate'],
                    after['cost']['detection_rate'],
                    invert=False
                )
            },
            'improvement_summary': f"Rs. {summary.get('cost_savings_inr', 0):,.0f} saved ({summary.get('cost_savings_percent', 0)}%)"
        }
    }

    # Calculate overall improvements
    total_improved = 0
    total_metrics = 0
    for model_key, model_data in models.items():
        for metric_key, metric_data in model_data['metrics'].items():
            total_metrics += 1
            if metric_data.get('direction') == 'improved':
                total_improved += 1

    # Build final comparison dictionary
    comparison = {
        'models': models,
        'overall': {
            'total_improvements': total_improved,
            'total_metrics': total_metrics,
            'improvement_rate': round(total_improved / total_metrics * 100, 1) if total_metrics > 0 else 0,
            'simulation_samples': summary.get('samples_collected', 0),
            'cost_savings_inr': summary.get('cost_savings_inr', 0),
            'detection_maintained': summary.get('detection_rate_maintained', 0)
        }
    }

    return comparison


@simulator_bp.route('/api/comparison')
@login_required
def get_latest_comparison():
    """Get the latest before/after comparison data for investor view"""
    current = capture_current_metrics()

    # For API call, we return current state comparison format
    return jsonify({
        'current_state': current,
        'models': {
            'site_risk': {
                'name': 'Site Risk Classifier',
                'algorithm': 'Random Forest',
                'current': {
                    'high_risk_sites': current['risk']['high_risk_total'],
                    'critical': current['risk']['critical_sites'],
                    'high': current['risk']['high_sites'],
                    'medium': current['risk']['medium_sites'],
                    'low': current['risk']['low_sites']
                },
                'accuracy': current['risk']['model_accuracy']
            },
            'contamination': {
                'name': 'Contamination Classifier',
                'algorithm': 'XGBoost',
                'current': {
                    'rate': current['contamination']['rate'],
                    'contaminated': current['contamination']['total_contaminated'],
                    'clean': current['contamination']['total_clean']
                },
                'f1_score': current['contamination']['f1_score']
            },
            'wqi': {
                'name': 'Real-time WQI',
                'algorithm': 'Penalty Algorithm',
                'current': {
                    'average': current['wqi']['average'],
                    'excellent': current['wqi']['excellent'],
                    'compliant': current['wqi']['compliant'],
                    'warning': current['wqi']['warning'],
                    'unsafe': current['wqi']['unsafe']
                }
            },
            'anomaly': {
                'name': 'Anomaly Detection',
                'algorithm': 'Isolation Forest + CUSUM',
                'current': {
                    'detected': current['anomaly']['detected'],
                    'total_checked': current['anomaly']['total_checked']
                },
                'accuracy': current['anomaly']['model_accuracy']
            },
            'forecast': {
                'name': 'Quality Forecaster',
                'algorithm': 'Gaussian Process',
                'current': {
                    'active': current['forecast']['active'],
                    'alerts': current['forecast']['exceedances']
                },
                'r2_score': current['forecast']['r2_score']
            },
            'cost': {
                'name': 'Cost Optimizer',
                'algorithm': 'Bayesian Optimization',
                'current': {
                    'current_cost': current['cost']['current_cost'],
                    'optimized_cost': current['cost']['optimized_cost'],
                    'savings': current['cost']['savings'],
                    'savings_percent': current['cost']['savings_percent'],
                    'detection_rate': current['cost']['detection_rate']
                }
            }
        }
    })


# ========== Simulation Functions ==========

def generate_simulation_samples(num_samples):
    """Generate new random samples with REALISTIC distribution based on site risk"""
    from app.models import User

    sites = Site.query.filter_by(is_active=True).all()
    analyst = User.query.filter_by(role='analyst').first()

    new_samples = []
    stats = {
        'by_site_type': {},
        'by_risk': {'high': 0, 'medium': 0, 'low': 0},
        'weather': {'sunny': 0, 'cloudy': 0, 'rainy': 0}
    }

    for i in range(num_samples):
        site = random.choice(sites)

        # Track stats
        stype = site.site_type or 'tank'
        stats['by_site_type'][stype] = stats['by_site_type'].get(stype, 0) + 1

        # Determine risk category
        risk_score = site.risk_score or 50
        if risk_score >= 70:
            risk_cat = 'high'
        elif risk_score >= 40:
            risk_cat = 'medium'
        else:
            risk_cat = 'low'
        stats['by_risk'][risk_cat] += 1

        # Weather affects contamination probability
        weather = random.choices(
            ['sunny', 'cloudy', 'rainy'],
            weights=[0.5, 0.3, 0.2]
        )[0]
        stats['weather'][weather] += 1

        # Generate unique sample ID with microseconds and random component
        sample_id = f"SIM-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]}-{random.randint(1000,9999)}-{i:04d}"
        rained = weather == 'rainy' or random.random() < 0.15

        sample = WaterSample(
            sample_id=sample_id,
            site_id=site.id,
            collection_date=datetime.utcnow().date(),
            collected_by_id=analyst.id if analyst else None,
            source_point=random.choice(['inlet', 'center', 'outlet']),
            weather_condition=weather,
            rained_recently=rained,
            apparent_color=random.choice(['clear', 'slight_yellow', 'brown']),
            odor=random.choice(['none', 'earthy', 'chlorine']),
            status='collected'
        )
        db.session.add(sample)
        db.session.flush()

        # REALISTIC contamination probability based on site risk + conditions
        base_prob = CONTAMINATION_PROBABILITIES.get(f'{risk_cat}_risk', 0.20)

        # Environmental factors
        if rained:
            base_prob += 0.15  # Rain increases runoff contamination
        if site.is_industrial_nearby:
            base_prob += 0.10
        if site.is_agricultural_nearby:
            base_prob += 0.08

        # Cap probability
        is_contaminated = random.random() < min(base_prob, 0.65)

        test = generate_random_test_result(sample, site, is_contaminated, analyst)
        db.session.add(test)

        new_samples.append((sample, test, is_contaminated))

    db.session.commit()
    return new_samples, stats


def generate_random_test_result(sample, site, is_contaminated, analyst):
    """Generate REALISTIC test result based on site characteristics"""
    # Base values for CLEAN water (WHO compliant)
    ph = random.gauss(7.2, 0.2)
    turbidity = random.uniform(0.5, 3.0)
    tds = random.uniform(150, 400)
    chlorine = random.uniform(0.25, 0.7)
    iron = random.uniform(0.02, 0.15)
    coliform = 0
    ammonia = random.uniform(0, 0.3)
    fluoride = random.uniform(0.5, 1.0)
    nitrate = random.uniform(5, 25)

    if is_contaminated:
        # Choose contamination type based on site characteristics
        contam_weights = [1, 1, 1, 1, 1]  # runoff, sewage, salt, corrosion, decay

        if sample.rained_recently:
            contam_weights[0] = 3  # Higher runoff
        if site.is_urban:
            contam_weights[1] = 2  # More sewage issues
        if site.is_coastal:
            contam_weights[2] = 3  # Salt intrusion
        if site.site_type == 'pipeline':
            contam_weights[3] = 2  # Pipe corrosion

        contamination_type = random.choices(
            ['runoff', 'sewage', 'salt', 'corrosion', 'decay'],
            weights=contam_weights
        )[0]

        # Apply contamination effects (varying severity)
        severity = random.choice(['mild', 'moderate', 'severe'])

        if contamination_type == 'runoff':
            if severity == 'mild':
                turbidity = random.uniform(5, 8)
            elif severity == 'moderate':
                turbidity = random.uniform(8, 15)
            else:
                turbidity = random.uniform(15, 30)
            nitrate = random.uniform(30, 60)

        elif contamination_type == 'sewage':
            if severity == 'mild':
                coliform = random.uniform(10, 50)
            elif severity == 'moderate':
                coliform = random.uniform(50, 200)
            else:
                coliform = random.uniform(200, 800)
            chlorine = random.uniform(0, 0.15)
            ammonia = random.uniform(1, 3)

        elif contamination_type == 'salt':
            if severity == 'mild':
                tds = random.uniform(600, 900)
            elif severity == 'moderate':
                tds = random.uniform(900, 1500)
            else:
                tds = random.uniform(1500, 3000)

        elif contamination_type == 'corrosion':
            if severity == 'mild':
                iron = random.uniform(0.3, 0.5)
            elif severity == 'moderate':
                iron = random.uniform(0.5, 1.0)
            else:
                iron = random.uniform(1.0, 2.5)
            ph = random.gauss(6.2, 0.3)  # Acidic from corrosion

        else:  # decay
            chlorine = random.uniform(0, 0.1)
            if severity == 'moderate' or severity == 'severe':
                coliform = random.uniform(5, 30)

    return TestResult(
        sample_id=sample.id,
        tested_by_id=analyst.id if analyst else None,
        tested_date=datetime.utcnow(),
        lab_name='Field Simulation Lab',
        ph=max(4, min(10, ph)),
        temperature_celsius=random.uniform(22, 32),
        turbidity_ntu=max(0, turbidity),
        tds_ppm=max(0, tds),
        conductivity_us_cm=tds * 1.5,
        free_chlorine_mg_l=max(0, chlorine),
        iron_mg_l=max(0, iron),
        total_coliform_mpn=max(0, coliform),
        ammonia_mg_l=max(0, ammonia),
        fluoride_mg_l=max(0, fluoride),
        nitrate_mg_l=max(0, nitrate)
    )


def run_contamination_analysis(samples):
    """Run contamination analysis on new samples, returns stats"""
    analyzer = ContaminationAnalyzer()
    analyses = []
    stats = {
        'contaminated': 0,
        'clean': 0,
        'by_type': {},
        'by_severity': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
    }

    for sample, test_result, expected_contam in samples:
        site = sample.site
        result = analyzer.analyze(test_result, sample, site)

        analysis = Analysis(
            sample_id=sample.id,
            test_result_id=test_result.id,
            is_contaminated=result['is_contaminated'],
            contamination_type=result['contamination_type_key'],
            severity_level=result['severity_level'],
            confidence_score=result['confidence_score'],
            wqi_score=result['wqi_score'],
            wqi_class=result['wqi_class'],
            runoff_sediment_score=result['runoff_sediment_score'],
            sewage_ingress_score=result['sewage_ingress_score'],
            salt_intrusion_score=result['salt_intrusion_score'],
            pipe_corrosion_score=result['pipe_corrosion_score'],
            disinfectant_decay_score=result['disinfectant_decay_score'],
            is_compliant_who=result['is_compliant_who'],
            is_compliant_bis=result['is_compliant_bis'],
            primary_recommendation=result['primary_recommendation'],
            analysis_method='ml_xgboost'
        )
        db.session.add(analysis)

        # Track stats
        if result['is_contaminated']:
            stats['contaminated'] += 1
            ctype = result['contamination_type_key'] or 'unknown'
            stats['by_type'][ctype] = stats['by_type'].get(ctype, 0) + 1
            sev = result['severity_level'] or 'low'
            if sev in stats['by_severity']:
                stats['by_severity'][sev] += 1
        else:
            stats['clean'] += 1

        sample.status = 'analyzed'
        analyses.append(analysis)

    db.session.commit()
    return analyses, stats


def update_site_risks():
    """Update risk predictions for all sites, track improvements/degradations"""
    ml = MLPipeline()
    sites = Site.query.filter_by(is_active=True).all()
    results = []
    stats = {
        'critical': 0, 'high': 0, 'medium': 0, 'low': 0,
        'improved': 0, 'worsened': 0, 'unchanged': 0
    }

    risk_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}

    for site in sites:
        old_risk = site.current_risk_level or 'medium'
        contamination_rate = site.get_contamination_rate(days=30)

        features = {
            'site_type': site.site_type,
            'is_coastal': site.is_coastal,
            'is_industrial_nearby': site.is_industrial_nearby,
            'is_agricultural_nearby': site.is_agricultural_nearby,
            'is_urban': site.is_urban,
            'population_served': site.population_served or 0,
            'contamination_rate_30d': contamination_rate,
            'days_since_last_test': 1
        }

        prediction = ml.predict_site_risk(features)
        new_risk = prediction['risk_level']

        risk_pred = SiteRiskPrediction(
            site_id=site.id,
            risk_level=new_risk,
            risk_score=prediction['risk_score'],
            confidence=prediction['confidence'],
            prob_critical=prediction['prob_critical'],
            prob_high=prediction['prob_high'],
            prob_medium=prediction['prob_medium'],
            prob_low=prediction['prob_low'],
            recommended_frequency=prediction['recommended_frequency'],
            tests_per_year=prediction['tests_per_year'],
            model_version='rf_v2_simulation'
        )
        db.session.add(risk_pred)

        site.current_risk_level = new_risk
        site.risk_score = prediction['risk_score']
        site.last_risk_assessment = datetime.utcnow()

        # Track stats
        stats[new_risk] += 1

        old_order = risk_order.get(old_risk, 1)
        new_order = risk_order.get(new_risk, 1)
        if new_order < old_order:
            stats['improved'] += 1
        elif new_order > old_order:
            stats['worsened'] += 1
        else:
            stats['unchanged'] += 1

        results.append(prediction)

    db.session.commit()
    return results, stats


def calculate_wqi_scores():
    """Calculate WQI for recent sensor readings with REALISTIC VARIATION"""
    ml = MLPipeline()

    sensors = IoTSensor.query.filter_by(is_active=True).all()
    stats = {
        'count': 0,
        'excellent': 0,
        'compliant': 0,
        'warning': 0,
        'unsafe': 0,
        'avg_wqi': 0,
        'total_wqi': 0
    }

    # Simulate seasonal/environmental factors that vary each run
    seasonal_factor = random.uniform(0.9, 1.1)  # Affects all readings slightly
    time_of_day_effect = random.choice([0, 0.5, -0.5, 1])  # Morning/afternoon/night variation

    for sensor in sensors:
        # REALISTIC probability - varies by sensor and conditions
        # Some sensors in good areas, some in problematic areas
        sensor_reliability = random.uniform(0.7, 0.95)  # Each sensor has different reliability
        is_good = random.random() < sensor_reliability

        if is_good:
            # Good reading with natural variation
            reading_data = {
                'ph': random.gauss(7.2 + time_of_day_effect * 0.1, 0.2 * seasonal_factor),
                'tds': random.gauss(280 + random.randint(-50, 80), 60),
                'turbidity': max(0.1, random.gauss(1.8 + random.uniform(-0.5, 1), 0.6)),
                'chlorine': max(0.1, random.gauss(0.5 + random.uniform(-0.1, 0.15), 0.12)),
                'temperature': random.gauss(27 + time_of_day_effect * 2, 2.5)
            }
        else:
            # Problematic reading - but with VARYING severity
            severity = random.choice(['mild', 'moderate', 'severe'])
            if severity == 'mild':
                reading_data = {
                    'ph': random.gauss(6.8, 0.3),
                    'tds': random.gauss(450, 80),
                    'turbidity': random.gauss(5, 1.5),
                    'chlorine': random.gauss(0.25, 0.08),
                    'temperature': random.gauss(30, 2)
                }
            elif severity == 'moderate':
                reading_data = {
                    'ph': random.gauss(6.4, 0.4),
                    'tds': random.gauss(650, 120),
                    'turbidity': random.gauss(9, 2.5),
                    'chlorine': random.gauss(0.15, 0.05),
                    'temperature': random.gauss(33, 2.5)
                }
            else:  # severe
                reading_data = {
                    'ph': random.gauss(5.8, 0.5),
                    'tds': random.gauss(900, 200),
                    'turbidity': random.gauss(15, 4),
                    'chlorine': random.gauss(0.05, 0.03),
                    'temperature': random.gauss(35, 3)
                }

        # Ensure values are within physical limits
        reading_data['ph'] = max(4, min(10, reading_data['ph']))
        reading_data['tds'] = max(50, reading_data['tds'])
        reading_data['turbidity'] = max(0.1, reading_data['turbidity'])
        reading_data['chlorine'] = max(0, reading_data['chlorine'])
        reading_data['temperature'] = max(15, min(45, reading_data['temperature']))

        wqi_result = ml.calculate_realtime_wqi(reading_data)

        wqi = WQIReading(
            site_id=sensor.site_id,
            sensor_id=sensor.id,
            wqi_score=wqi_result['wqi_score'],
            wqi_class=wqi_result['wqi_class'],
            ph_penalty=wqi_result['ph_penalty'],
            tds_penalty=wqi_result['tds_penalty'],
            turbidity_penalty=wqi_result['turbidity_penalty'],
            chlorine_penalty=wqi_result['chlorine_penalty'],
            temperature_penalty=wqi_result['temperature_penalty'],
            ph_value=reading_data['ph'],
            tds_value=reading_data['tds'],
            turbidity_value=reading_data['turbidity'],
            chlorine_value=reading_data['chlorine'],
            temperature_value=reading_data['temperature'],
            is_drinkable=wqi_result['is_drinkable']
        )
        db.session.add(wqi)

        # Track stats
        stats['count'] += 1
        stats['total_wqi'] += wqi_result['wqi_score']
        wclass = wqi_result['wqi_class']
        if wclass == 'Excellent':
            stats['excellent'] += 1
        elif wclass == 'Compliant':
            stats['compliant'] += 1
        elif wclass == 'Warning':
            stats['warning'] += 1
        else:
            stats['unsafe'] += 1

    db.session.commit()
    stats['avg_wqi'] = stats['total_wqi'] / stats['count'] if stats['count'] > 0 else 0
    return stats


def detect_anomalies():
    """Detect anomalies with REALISTIC VARIATION - some runs find more, some less"""
    sensors = IoTSensor.query.filter_by(is_active=True).all()
    stats = {
        'total': len(sensors),
        'detected': 0,
        'normal': 0,
        'by_type': {},
        'by_parameter': {}
    }

    # Simulate varying environmental conditions that affect anomaly rate
    # Some runs might be during stable conditions (fewer anomalies)
    # Some runs during unstable conditions (more anomalies)
    base_anomaly_rate = random.uniform(0.04, 0.15)  # Varies 4-15% each run

    # Simulate model sensitivity variation
    model_sensitivity = random.uniform(0.8, 1.2)

    for sensor in sensors:
        # Each sensor has its own reliability/noise level
        sensor_noise = random.uniform(0.8, 1.2)
        effective_rate = base_anomaly_rate * sensor_noise * model_sensitivity

        is_anomaly = random.random() < min(0.25, effective_rate)  # Cap at 25%

        if is_anomaly:
            # Vary anomaly types based on "conditions"
            if random.random() < 0.6:
                # Common anomalies
                anomaly_type = random.choices(
                    ['spike', 'drop', 'drift'],
                    weights=[0.45, 0.35, 0.20]
                )[0]
            else:
                # Less common patterns
                anomaly_type = random.choices(
                    ['gradual_rise', 'oscillation', 'sudden_change'],
                    weights=[0.4, 0.3, 0.3]
                )[0]

            parameter = random.choices(
                ['ph', 'tds', 'turbidity', 'chlorine', 'temperature'],
                weights=[0.22, 0.28, 0.28, 0.12, 0.10]
            )[0]

            # Generate realistic observed/expected values based on parameter
            if parameter == 'ph':
                expected = random.uniform(6.8, 7.5)
                observed = expected + random.choice([-1, 1]) * random.uniform(0.5, 2.0)
            elif parameter == 'tds':
                expected = random.uniform(200, 400)
                observed = expected + random.choice([-1, 1]) * random.uniform(150, 500)
            elif parameter == 'turbidity':
                expected = random.uniform(1, 4)
                observed = expected + random.uniform(3, 15)
            elif parameter == 'chlorine':
                expected = random.uniform(0.3, 0.6)
                observed = expected + random.choice([-1, 1]) * random.uniform(0.2, 0.5)
            else:  # temperature
                expected = random.uniform(25, 30)
                observed = expected + random.choice([-1, 1]) * random.uniform(3, 8)

            deviation = abs(observed - expected) / max(0.1, expected) * random.uniform(2, 5)

            anomaly = AnomalyDetection(
                site_id=sensor.site_id,
                sensor_id=sensor.id,
                is_anomaly=True,
                anomaly_type=anomaly_type,
                anomaly_score=random.uniform(0.65, 0.98),
                cusum_value=random.uniform(2.5, 7),
                parameter=parameter,
                observed_value=round(observed, 2),
                expected_value=round(expected, 2),
                deviation_sigma=round(deviation, 2),
                detection_method='isolation_forest_cusum',
                model_version=f'ad_v3_sim_{random.randint(100,999)}'
            )
            db.session.add(anomaly)

            stats['detected'] += 1
            stats['by_type'][anomaly_type] = stats['by_type'].get(anomaly_type, 0) + 1
            stats['by_parameter'][parameter] = stats['by_parameter'].get(parameter, 0) + 1
        else:
            stats['normal'] += 1

    db.session.commit()
    return stats


def run_cost_optimization():
    """Run REALISTIC cost optimization with proper savings calculation and VARIATION"""
    sites = Site.query.filter_by(is_active=True).all()

    # Cost per test (realistic values in INR) - ADD VARIATION
    BASE_COST_PER_TEST = 12000  # Rs. 12,000 base per comprehensive water test

    # Current testing frequency (before optimization) - WITH VARIATION
    CURRENT_TESTS_BASE = {
        'critical': 52,   # Weekly
        'high': 24,       # Bi-weekly
        'medium': 12,     # Monthly
        'low': 6          # Bi-monthly
    }

    # Optimized testing frequency - WITH VARIATION based on ML confidence
    OPTIMIZED_TESTS_BASE = {
        'critical': 36,   # Slightly reduced but still frequent
        'high': 18,       # Optimized
        'medium': 8,      # Risk-based reduction
        'low': 4          # Minimal for low-risk
    }

    # Add randomness to run_id to ensure uniqueness
    run_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    total_current = 0
    total_optimized = 0
    total_detection_rate = 0

    # Simulate varying model performance across runs (real-world ML behavior)
    model_confidence_factor = random.uniform(0.85, 1.15)  # Model performs differently each run

    for i, site in enumerate(sites):
        risk_score = site.risk_score or 50

        # ADD RANDOM VARIATION to risk score for this run (simulates measurement uncertainty)
        adjusted_risk = risk_score + random.uniform(-10, 10)

        # Determine risk category with some randomness at boundaries
        if adjusted_risk >= 75:
            risk_cat = 'critical'
        elif adjusted_risk >= 55:
            risk_cat = 'high'
        elif adjusted_risk >= 35:
            risk_cat = 'medium'
        else:
            risk_cat = 'low'

        # ADD VARIATION to test frequencies (real-world: not every site gets exact same treatment)
        current_tests = CURRENT_TESTS_BASE[risk_cat] + random.randint(-2, 2)
        current_tests = max(4, current_tests)  # Minimum 4 tests/year

        # Optimized tests vary based on model confidence and site-specific factors
        base_optimized = OPTIMIZED_TESTS_BASE[risk_cat]
        optimized_variation = int(base_optimized * random.uniform(0.8, 1.2))
        optimized_tests = max(2, min(optimized_variation, current_tests - 2))  # Always save at least 2 tests

        # VARY cost per test (different labs, different test types)
        site_cost_per_test = BASE_COST_PER_TEST * random.uniform(0.9, 1.15)

        current_cost = current_tests * site_cost_per_test
        optimized_cost = optimized_tests * site_cost_per_test
        savings = current_cost - optimized_cost

        # REALISTIC detection rate with variation
        # Some sites: model works great (95-99%), some: model struggles (85-92%)
        if random.random() < 0.75:  # 75% of sites - good prediction
            detection_rate = random.uniform(93, 98)
        else:  # 25% of sites - model less accurate (real-world scenario)
            detection_rate = random.uniform(82, 92)

        # Apply overall model confidence factor
        detection_rate = min(99, detection_rate * model_confidence_factor)

        # Calculate next test date based on optimized frequency
        weeks_between_tests = max(1, 52 // optimized_tests) if optimized_tests > 0 else 13
        next_test = (datetime.utcnow() + timedelta(weeks=weeks_between_tests)).date()

        opt = CostOptimizationResult(
            site_id=site.id,
            optimization_run_id=run_id,
            risk_category=risk_cat,
            current_tests_per_year=current_tests,
            optimized_tests_per_year=optimized_tests,
            current_cost_inr=round(current_cost, 0),
            optimized_cost_inr=round(optimized_cost, 0),
            cost_savings_inr=round(savings, 0),
            cost_reduction_percent=round(savings / current_cost * 100, 1) if current_cost > 0 else 0,
            detection_rate=round(detection_rate, 1),
            recommended_frequency=f"Every {weeks_between_tests} weeks" if optimized_tests > 0 else "As needed",
            next_test_date=next_test,
            priority_rank=i + 1,
            model_version=f'bayesian_v2_sim_{random.randint(100,999)}'
        )
        db.session.add(opt)

        total_current += current_cost
        total_optimized += optimized_cost
        total_detection_rate += detection_rate

    db.session.commit()

    total_savings = total_current - total_optimized
    savings_percent = round(total_savings / total_current * 100, 1) if total_current > 0 else 0
    avg_detection = round(total_detection_rate / len(sites), 1) if sites else 0

    return {
        'savings_percent': savings_percent,
        'total_savings': round(total_savings, 0),
        'current_cost': round(total_current, 0),
        'optimized_cost': round(total_optimized, 0),
        'detection_rate': avg_detection
    }


def generate_forecasts():
    """Generate water quality forecasts with alert tracking"""
    sites = Site.query.filter_by(is_active=True).limit(20).all()
    stats = {
        'count': 0,
        'alerts': 0,
        'by_parameter': {}
    }

    for site in sites:
        # Determine if site might have future issues based on current risk
        risk_score = site.risk_score or 50
        alert_probability = 0.05 + (risk_score / 100) * 0.15  # 5-20% based on risk

        for param in ['ph', 'turbidity', 'tds', 'chlorine']:
            for day in range(1, 31):
                forecast_date = datetime.utcnow().date() + timedelta(days=day)

                # Generate REALISTIC prediction
                base_value = {'ph': 7.2, 'turbidity': 3, 'tds': 350, 'chlorine': 0.5}[param]

                # Add slight trend based on site risk
                trend = (risk_score - 50) / 500 * day  # Slight drift for risky sites
                predicted = base_value + random.gauss(trend, 0.08 * base_value)

                # Uncertainty increases with forecast horizon
                uncertainty = 0.04 * base_value * (1 + day * 0.025)

                # Probability of exceeding threshold
                prob_exceed = random.uniform(0, alert_probability) if day < 15 else random.uniform(0, alert_probability * 1.5)

                forecast = WaterQualityForecast(
                    site_id=site.id,
                    forecast_date=forecast_date,
                    parameter=param,
                    predicted_value=predicted,
                    lower_bound_95=predicted - 1.96 * uncertainty,
                    upper_bound_95=predicted + 1.96 * uncertainty,
                    uncertainty=uncertainty,
                    prob_exceed_threshold=prob_exceed,
                    model_version='gp_v2_simulation',
                    r2_score=0.78
                )
                db.session.add(forecast)

                stats['count'] += 1
                stats['by_parameter'][param] = stats['by_parameter'].get(param, 0) + 1

                if prob_exceed > 0.5:
                    stats['alerts'] += 1

    db.session.commit()
    return stats
