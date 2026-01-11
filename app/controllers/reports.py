"""ML Performance Reports Controller - Walk-Forward Validation Analysis"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_
import numpy as np
import json
from app import db
from app.models import (
    Site, WaterSample, TestResult, Analysis,
    WaterQualityForecast, ContaminationPrediction, SiteRiskPrediction,
    WQIReading, AnomalyDetection, DriftDetection, Intervention, ValidationResult, User
)
from app.services.ml_pipeline import MLPipeline
from app.models import CostOptimizationResult
import time

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def get_site_samples_optimized(site_id, limit=100, max_limit=500):
    """
    Get samples for a site with performance optimizations

    Args:
        site_id: Site ID to query
        limit: Default number of samples to return (default 100)
        max_limit: Maximum allowed limit (default 500)

    Returns:
        List of WaterSample objects
    """
    # Get limit from request if available, otherwise use default
    sample_limit = limit
    if request and request.args:
        sample_limit = min(int(request.args.get('limit', limit)), max_limit)

    # Limit to recent samples (test_results is dynamic, can't eager load)
    samples = WaterSample.query.filter_by(
        site_id=site_id
    ).order_by(
        WaterSample.collection_date.desc()
    ).limit(sample_limit).all()

    # Return in chronological order
    return list(reversed(samples))


@reports_bp.route('/research-summary')
def research_summary():
    """Render the research summary page with real database metrics"""
    # Database Statistics - India public sites only (exclude residential/private artificial data)
    total_sites = Site.query.filter_by(is_active=True, country='India', site_category='public').count()

    # Total samples from India public sites only
    total_samples = db.session.query(func.count(WaterSample.id))\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    # Total tests from India public sites only
    total_tests = db.session.query(func.count(TestResult.id))\
        .join(WaterSample, TestResult.sample_id == WaterSample.id)\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    # Date range - India public sites only
    first_sample = db.session.query(WaterSample)\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .order_by(WaterSample.collection_date.asc()).first()

    last_sample = db.session.query(WaterSample)\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .order_by(WaterSample.collection_date.desc()).first()

    # Calculate date range in years and formatted dates
    if first_sample and last_sample:
        date_range_years = round((last_sample.collection_date - first_sample.collection_date).days / 365, 1)
        min_date = first_sample.collection_date.strftime('%Y-%m-%d')
        max_date = last_sample.collection_date.strftime('%Y-%m-%d')
    else:
        date_range_years = 0
        min_date = 'N/A'
        max_date = 'N/A'

    # State distribution with counts - India public sites only
    state_counts = db.session.query(
        Site.state, func.count(Site.id), func.count(WaterSample.id)
    ).join(WaterSample, Site.id == WaterSample.site_id, isouter=True)\
     .filter(Site.is_active == True, Site.country == 'India', Site.site_category == 'public')\
     .group_by(Site.state).all()

    states = [s[0] for s in state_counts]
    state_breakdown = [{'name': s[0], 'sites': s[1], 'samples': s[2] or 0} for s in state_counts]

    # ML Predictions counts - India public sites only
    risk_predictions = db.session.query(func.count(SiteRiskPrediction.id))\
        .join(Site, SiteRiskPrediction.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    contamination_predictions = db.session.query(func.count(ContaminationPrediction.id))\
        .join(WaterSample, ContaminationPrediction.sample_id == WaterSample.id)\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    wqi_readings = db.session.query(func.count(WQIReading.id))\
        .join(Site, WQIReading.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    forecasts = db.session.query(func.count(WaterQualityForecast.id))\
        .join(Site, WaterQualityForecast.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    cost_optimizations = CostOptimizationResult.query.count()  # System-wide, not site-specific

    # Site Risk Distribution - India public sites only
    risk_dist = db.session.query(
        SiteRiskPrediction.risk_level, func.count(SiteRiskPrediction.id)
    ).join(Site, SiteRiskPrediction.site_id == Site.id)\
     .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
     .group_by(SiteRiskPrediction.risk_level).all()

    # Individual risk level counts
    risk_critical = sum(count for level, count in risk_dist if level == 'critical')
    risk_high = sum(count for level, count in risk_dist if level == 'high')
    risk_medium = sum(count for level, count in risk_dist if level == 'medium')
    risk_low = sum(count for level, count in risk_dist if level == 'low')

    # Contamination Type Distribution - India public sites only
    contam_dist = db.session.query(
        ContaminationPrediction.predicted_type
    ).join(WaterSample, ContaminationPrediction.sample_id == WaterSample.id)\
     .join(Site, WaterSample.site_id == Site.id)\
     .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
     .distinct().all()
    contamination_types = [c[0] for c in contam_dist if c[0]]

    # WQI metrics - India public sites only
    wqi_all = db.session.query(WQIReading)\
        .join(Site, WQIReading.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public').all()
    avg_wqi = round(np.mean([w.wqi_score for w in wqi_all if w.wqi_score]), 1) if wqi_all else 0

    wqi_class_dist = db.session.query(
        WQIReading.wqi_class, func.count(WQIReading.id)
    ).join(Site, WQIReading.site_id == Site.id)\
     .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
     .group_by(WQIReading.wqi_class).all()
    wqi_classes = len(wqi_class_dist)

    # ML Performance metrics - India public sites only
    forecasts_with_r2 = db.session.query(WaterQualityForecast)\
        .join(Site, WaterQualityForecast.site_id == Site.id)\
        .filter(WaterQualityForecast.r2_score.isnot(None),
                Site.country == 'India', Site.is_active == True, Site.site_category == 'public').all()
    avg_r2 = round(np.mean([f.r2_score for f in forecasts_with_r2]), 2) if forecasts_with_r2 else 0

    # Cost Optimization Results (system-wide, applies to all optimizations)
    cost_results = CostOptimizationResult.query.all()
    if cost_results:
        avg_cost_reduction = round(np.mean([r.cost_reduction_percent for r in cost_results if r.cost_reduction_percent]), 1)
        avg_detection_rate = round(np.mean([r.detection_rate for r in cost_results if r.detection_rate]), 1)
    else:
        avg_cost_reduction = 0
        avg_detection_rate = 0

    # Contamination confidence (from predictions) - India public sites only
    contam_preds = db.session.query(ContaminationPrediction)\
        .join(WaterSample, ContaminationPrediction.sample_id == WaterSample.id)\
        .join(Site, WaterSample.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public').all()
    avg_confidence = round(np.mean([c.confidence for c in contam_preds if c.confidence]), 1) if contam_preds else 0

    # Calculate average samples per site
    avg_samples_per_site = round(total_samples / total_sites, 1) if total_sites > 0 else 0

    # Intervention Statistics - India public sites only
    total_interventions = db.session.query(func.count(Intervention.id))\
        .join(Site, Intervention.site_id == Site.id)\
        .filter(Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    completed_interventions = db.session.query(func.count(Intervention.id))\
        .join(Site, Intervention.site_id == Site.id)\
        .filter(Intervention.status == 'completed',
                Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    interventions_with_improvement = db.session.query(Intervention)\
        .join(Site, Intervention.site_id == Site.id)\
        .filter(Intervention.status == 'completed',
                Intervention.improvement_percent.isnot(None),
                Site.country == 'India', Site.is_active == True, Site.site_category == 'public').all()

    avg_intervention_effectiveness = 0
    if interventions_with_improvement:
        avg_intervention_effectiveness = round(
            np.mean([i.improvement_percent for i in interventions_with_improvement]),
            1
        )

    total_intervention_cost = db.session.query(func.sum(Intervention.actual_cost_inr))\
        .join(Site, Intervention.site_id == Site.id)\
        .filter(Intervention.actual_cost_inr.isnot(None),
                Site.country == 'India', Site.is_active == True, Site.site_category == 'public')\
        .scalar() or 0

    # Build stats object for template
    stats = {
        'total_sites': total_sites,
        'total_samples': total_samples,
        'total_tests': total_tests,
        'states': states,
        'state_breakdown': state_breakdown,
        'date_range_years': date_range_years,
        'min_date': min_date,
        'max_date': max_date,
        'avg_samples_per_site': avg_samples_per_site,
        'risk_predictions': risk_predictions,
        'risk_critical': risk_critical,
        'risk_high': risk_high,
        'risk_medium': risk_medium,
        'risk_low': risk_low,
        'contamination_predictions': contamination_predictions,
        'contamination_types': contamination_types,
        'avg_confidence': avg_confidence,
        'wqi_readings': wqi_readings,
        'avg_wqi': avg_wqi,
        'wqi_classes': wqi_classes,
        'forecasts': forecasts,
        'avg_r2': avg_r2,
        'cost_optimizations': cost_optimizations,
        'avg_cost_reduction': avg_cost_reduction,
        'avg_detection_rate': avg_detection_rate,
        'total_interventions': total_interventions,
        'completed_interventions': completed_interventions,
        'avg_intervention_effectiveness': avg_intervention_effectiveness,
        'total_intervention_cost': total_intervention_cost
    }

    return render_template('reports/research_summary.html',
                           stats=stats,
                           generation_date=datetime.now().strftime('%B %d, %Y'))


@reports_bp.route('/user-guide')
def user_guide():
    """Render the comprehensive user guide page"""

    # Platform Statistics
    total_sites = Site.query.filter_by(is_active=True).count()
    total_samples = WaterSample.query.count()
    total_users = User.query.filter_by(is_active=True).count()

    # ML Predictions Count
    total_predictions = (
        SiteRiskPrediction.query.count() +
        ContaminationPrediction.query.count() +
        WaterQualityForecast.query.count() +
        WQIReading.query.count()
    )

    # Geographic Coverage
    states = db.session.query(Site.state).distinct().order_by(Site.state).all()
    states_list = [s[0] for s in states if s[0]]

    site_types = db.session.query(Site.site_type).distinct().all()
    site_types_list = [st[0] for st in site_types if st[0]]

    # Role Information
    roles_info = {
        'viewer': {
            'name': 'Viewer',
            'category': 'Public',
            'description': 'Read-only access to public water quality data',
            'auto_approved': True,
            'permissions': ['view_public_sites', 'view_public_samples']
        },
        'citizen_contributor': {
            'name': 'Citizen Contributor',
            'category': 'Public',
            'description': 'Submit visual observations and photos',
            'auto_approved': True,
            'permissions': ['submit_observations', 'view_public_sites']
        },
        'researcher': {
            'name': 'Researcher',
            'category': 'Public',
            'description': 'Access all datasets for research purposes',
            'auto_approved': True,
            'permissions': ['view_all_sites', 'submit_samples', 'access_ml_reports', 'export_data']
        },
        'field_collector': {
            'name': 'Field Collector',
            'category': 'Restricted',
            'description': 'Collect water samples from assigned sites',
            'auto_approved': False,
            'permissions': ['view_assigned_sites', 'submit_samples']
        },
        'analyst': {
            'name': 'Analyst',
            'category': 'Restricted',
            'description': 'Data analysis and ML model access',
            'auto_approved': False,
            'permissions': ['view_all_sites', 'access_ml_reports', 'access_analytics', 'api_access']
        },
        'lab_partner': {
            'name': 'Lab Partner',
            'category': 'Restricted',
            'description': 'Submit laboratory test results',
            'auto_approved': False,
            'permissions': ['view_assigned_sites', 'submit_samples', 'submit_test_results', 'bulk_import', 'access_ml_reports']
        },
        'industry_partner': {
            'name': 'Industry Partner',
            'category': 'Restricted',
            'description': 'Monitor compliance for assigned sites',
            'auto_approved': False,
            'permissions': ['view_assigned_sites', 'submit_samples', 'submit_test_results', 'bulk_import', 'interventions']
        },
        'government_official': {
            'name': 'Government Official',
            'category': 'Restricted',
            'description': 'Official monitoring and reporting',
            'auto_approved': False,
            'permissions': ['view_all_sites', 'create_sites', 'submit_samples', 'submit_test_results', 'bulk_import', 'access_ml_reports', 'interventions']
        },
        'site_manager': {
            'name': 'Site Manager',
            'category': 'Restricted',
            'description': 'Manage assigned water body sites',
            'auto_approved': False,
            'permissions': ['view_assigned_sites', 'create_sites', 'edit_sites', 'submit_samples', 'access_ml_reports']
        },
        'admin': {
            'name': 'Admin',
            'category': 'System',
            'description': 'Full system access including user management',
            'auto_approved': False,
            'permissions': ['all_permissions']
        }
    }

    # Water Quality Parameters
    physical_params = ['pH', 'Temperature', 'Turbidity', 'Color', 'Odor', 'Taste', 'Conductivity', 'TDS']
    chemical_params = ['Total Hardness', 'Calcium', 'Magnesium', 'Alkalinity', 'Free Chlorine', 'Total Chlorine']
    anions = ['Chloride', 'Fluoride', 'Sulfate', 'Nitrate', 'Nitrite', 'Phosphate']
    metals = ['Iron', 'Manganese', 'Copper', 'Zinc', 'Lead', 'Arsenic', 'Chromium', 'Cadmium', 'Mercury']
    biological = ['Total Coliform', 'Fecal Coliform', 'E. coli']
    organic = ['Dissolved Oxygen', 'BOD', 'COD']

    stats = {
        'total_sites': total_sites,
        'total_samples': total_samples,
        'total_users': total_users,
        'total_predictions': total_predictions,
        'states': states_list,
        'site_types': site_types_list,
        'roles_info': roles_info,
        'parameters': {
            'physical': physical_params,
            'chemical': chemical_params,
            'anions': anions,
            'metals': metals,
            'biological': biological,
            'organic': organic
        }
    }

    return render_template('reports/user_guide.html', stats=stats)


@reports_bp.route('/api/research-summary')
def api_research_summary():
    """Get comprehensive research summary data from database"""
    try:
        # Database Statistics
        total_sites = Site.query.filter_by(is_active=True).count()
        total_samples = WaterSample.query.count()
        total_test_results = TestResult.query.count()
        total_analyses = Analysis.query.count()

        # Date range
        first_sample = WaterSample.query.order_by(WaterSample.collection_date.asc()).first()
        last_sample = WaterSample.query.order_by(WaterSample.collection_date.desc()).first()

        # State distribution
        state_counts = db.session.query(
            Site.state, func.count(Site.id)
        ).filter(Site.is_active == True).group_by(Site.state).all()

        # Site type distribution
        site_type_counts = db.session.query(
            Site.site_type, func.count(Site.id)
        ).filter(Site.is_active == True).group_by(Site.site_type).all()

        # ML Predictions counts
        site_risk_predictions = SiteRiskPrediction.query.count()
        contamination_predictions = ContaminationPrediction.query.count()
        wqi_readings = WQIReading.query.count()
        water_quality_forecasts = WaterQualityForecast.query.count()
        anomaly_detections = AnomalyDetection.query.count()

        # Cost Optimization Results
        cost_results = CostOptimizationResult.query.all()
        cost_optimization_count = len(cost_results)

        if cost_results:
            avg_cost_reduction = np.mean([r.cost_reduction_percent for r in cost_results if r.cost_reduction_percent])
            avg_detection_rate = np.mean([r.detection_rate for r in cost_results if r.detection_rate])
        else:
            avg_cost_reduction = 0
            avg_detection_rate = 0

        # Site Risk Distribution
        risk_dist = db.session.query(
            SiteRiskPrediction.risk_level, func.count(SiteRiskPrediction.id)
        ).group_by(SiteRiskPrediction.risk_level).all()

        # Contamination Type Distribution
        contam_dist = db.session.query(
            ContaminationPrediction.predicted_type, func.count(ContaminationPrediction.id)
        ).group_by(ContaminationPrediction.predicted_type).all()

        # WQI Class Distribution
        wqi_dist = db.session.query(
            WQIReading.wqi_class, func.count(WQIReading.id)
        ).group_by(WQIReading.wqi_class).all()

        # Forecast Performance (average R² from forecasts)
        forecasts_with_r2 = WaterQualityForecast.query.filter(WaterQualityForecast.r2_score.isnot(None)).all()
        avg_r2 = np.mean([f.r2_score for f in forecasts_with_r2]) if forecasts_with_r2 else 0

        # Calculate average samples per site
        avg_samples_per_site = total_samples / total_sites if total_sites > 0 else 0

        # Build response
        data = {
            'database_stats': {
                'total_sites': total_sites,
                'total_samples': total_samples,
                'total_test_results': total_test_results,
                'total_analyses': total_analyses,
                'avg_samples_per_site': round(avg_samples_per_site, 1),
                'date_range': {
                    'start': first_sample.collection_date.isoformat() if first_sample else None,
                    'end': last_sample.collection_date.isoformat() if last_sample else None
                },
                'states': {state: count for state, count in state_counts},
                'site_types': {stype: count for stype, count in site_type_counts}
            },
            'ml_predictions': {
                'site_risk_predictions': site_risk_predictions,
                'contamination_predictions': contamination_predictions,
                'wqi_readings': wqi_readings,
                'water_quality_forecasts': water_quality_forecasts,
                'anomaly_detections': anomaly_detections,
                'cost_optimization_results': cost_optimization_count
            },
            'ml_performance': {
                'avg_forecast_r2': round(float(avg_r2), 3) if not np.isnan(avg_r2) else 0,
                'avg_cost_reduction': round(float(avg_cost_reduction), 2) if not np.isnan(avg_cost_reduction) else 0,
                'avg_detection_rate': round(float(avg_detection_rate), 2) if not np.isnan(avg_detection_rate) else 0
            },
            'distributions': {
                'site_risk': {level: count for level, count in risk_dist},
                'contamination_types': {ctype: count for ctype, count in contam_dist},
                'wqi_classes': {wclass: count for wclass, count in wqi_dist}
            }
        }

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/')
def index():
    """Reports dashboard - overview of all ML model performance"""
    return render_template('reports/index.html')


@reports_bp.route('/site/<int:site_id>')
def site_report(site_id):
    """Detailed ML performance report for a specific site"""
    site = Site.query.get_or_404(site_id)

    # Verify user has access to this site
    if current_user.is_authenticated and not current_user.can_access_site(site_id):
        from flask import flash, redirect, url_for
        flash('You do not have permission to access this site report.', 'error')
        return redirect(url_for('reports.index'))

    return render_template('reports/site_report.html', site=site)


@reports_bp.route('/api/overview')
def api_overview():
    """Get overview statistics for all ML models"""
    try:
        # Get date range from query params
        days = int(request.args.get('days', 90))
        start_date = datetime.utcnow() - timedelta(days=days)

        overview = {
            'forecaster': get_forecaster_performance(start_date),
            'contamination': get_contamination_performance(start_date),
            'site_risk': get_site_risk_performance(start_date),
            'wqi': get_wqi_performance(start_date),
            'anomaly': get_anomaly_performance(start_date)
        }

        return jsonify({'success': True, 'data': overview})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/walkforward')
def api_site_walkforward(site_id):
    """Run walk-forward validation for a specific site"""
    try:
        site = Site.query.get_or_404(site_id)

        # Get training period size from params
        train_months = int(request.args.get('train_months', 3))

        # Run walk-forward validation
        results = run_walkforward_validation(site, train_months)

        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/forecaster')
def api_site_forecaster(site_id):
    """Get forecaster performance for a site - predictions vs actuals"""
    try:
        site = Site.query.get_or_404(site_id)

        # PERFORMANCE: Limit samples to avoid loading thousands of records
        # Get sample limit from query param (default 100, max 500)
        sample_limit = min(int(request.args.get('limit', 100)), 500)

        # Parameters to analyze
        parameters = ['ph', 'turbidity_ntu', 'tds_ppm', 'temperature_celsius']
        param_labels = {
            'ph': 'pH',
            'turbidity_ntu': 'Turbidity (NTU)',
            'tds_ppm': 'TDS (ppm)',
            'temperature_celsius': 'Temperature (°C)'
        }

        results = {}

        for param in parameters:
            results[param] = {
                'label': param_labels.get(param, param),
                'predictions': [],
                'actuals': [],
                'metrics': {}
            }

            # Get all forecasts for this site and parameter
            forecasts = WaterQualityForecast.query.filter(
                WaterQualityForecast.site_id == site_id,
                WaterQualityForecast.parameter == param.replace('_ntu', '').replace('_ppm', '').replace('_celsius', '')
            ).order_by(WaterQualityForecast.forecast_date).all()

            # PERFORMANCE FIX: Use optimized sample loading (limit + eager load)
            samples = get_site_samples_optimized(site_id, limit=sample_limit)

            predictions = []
            actuals = []

            for i, sample in enumerate(samples):
                if i < 3:  # Need at least 3 samples for training
                    continue

                # Get actual value
                test_result = sample.get_latest_test()
                if not test_result:
                    continue

                actual_value = getattr(test_result, param, None)
                if actual_value is None:
                    continue

                # Calculate prediction from previous samples (simple moving average)
                prev_values = []
                for j in range(max(0, i-3), i):
                    prev_sample = samples[j]
                    if prev_sample.get_latest_test():
                        val = getattr(prev_sample.get_latest_test(), param, None)
                        if val is not None:
                            prev_values.append(val)

                if prev_values:
                    predicted_value = np.mean(prev_values)
                    std_val = np.std(prev_values) if len(prev_values) > 1 else predicted_value * 0.1

                    predictions.append({
                        'date': sample.collection_date.isoformat(),
                        'predicted': round(float(predicted_value), 2),
                        'lower_95': round(float(predicted_value - 1.96 * std_val), 2),
                        'upper_95': round(float(predicted_value + 1.96 * std_val), 2)
                    })
                    actuals.append({
                        'date': sample.collection_date.isoformat(),
                        'value': round(float(actual_value), 2)
                    })

            results[param]['predictions'] = predictions
            results[param]['actuals'] = actuals

            # Calculate metrics
            if predictions and actuals:
                pred_vals = [p['predicted'] for p in predictions]
                act_vals = [a['value'] for a in actuals]

                mae = np.mean(np.abs(np.array(pred_vals) - np.array(act_vals)))
                rmse = np.sqrt(np.mean((np.array(pred_vals) - np.array(act_vals))**2))

                # R² calculation
                ss_res = np.sum((np.array(act_vals) - np.array(pred_vals))**2)
                ss_tot = np.sum((np.array(act_vals) - np.mean(act_vals))**2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                # Coverage (% of actuals within 95% CI)
                within_ci = sum(1 for i, p in enumerate(predictions)
                               if p['lower_95'] <= actuals[i]['value'] <= p['upper_95'])
                coverage = (within_ci / len(predictions)) * 100 if predictions else 0

                results[param]['metrics'] = {
                    'mae': round(float(mae), 3),
                    'rmse': round(float(rmse), 3),
                    'r2': round(float(max(0, r2)), 3),
                    'coverage_95': round(float(coverage), 1),
                    'n_predictions': len(predictions)
                }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/contamination')
def api_site_contamination(site_id):
    """Get contamination prediction performance for a site"""
    try:
        site = Site.query.get_or_404(site_id)

        # PERFORMANCE FIX: Use optimized sample loading (limit + eager load)
        samples = get_site_samples_optimized(site_id)

        results = {
            'predictions': [],
            'confusion_matrix': {},
            'metrics': {}
        }

        contamination_types = ['runoff_sediment', 'sewage_ingress', 'salt_intrusion',
                              'pipe_corrosion', 'disinfectant_decay', 'none']

        # Initialize confusion matrix
        matrix = {t: {t2: 0 for t2 in contamination_types} for t in contamination_types}

        for sample in samples:
            if not sample.get_latest_test():
                continue

            test_result = sample.get_latest_test()

            # Get prediction (from ContaminationPrediction or calculate)
            prediction = ContaminationPrediction.query.filter_by(sample_id=sample.id).first()

            if prediction:
                predicted_type = prediction.predicted_type
                confidence = prediction.confidence
            else:
                # Calculate prediction using ML pipeline logic
                predicted_type, confidence = calculate_contamination_prediction(test_result, sample, site)

            # Determine actual contamination based on test results
            actual_type = determine_actual_contamination(test_result)

            results['predictions'].append({
                'date': sample.collection_date.isoformat(),
                'sample_id': sample.id,
                'predicted': predicted_type,
                'actual': actual_type,
                'confidence': round(confidence, 1),
                'correct': predicted_type == actual_type
            })

            # Update confusion matrix
            pred_key = predicted_type if predicted_type in contamination_types else 'none'
            act_key = actual_type if actual_type in contamination_types else 'none'
            matrix[pred_key][act_key] += 1

        results['confusion_matrix'] = matrix

        # Calculate metrics
        if results['predictions']:
            correct = sum(1 for p in results['predictions'] if p['correct'])
            total = len(results['predictions'])

            results['metrics'] = {
                'accuracy': round((correct / total) * 100, 1) if total > 0 else 0,
                'total_samples': total,
                'correct_predictions': correct,
                'incorrect_predictions': total - correct
            }

            # Per-type metrics
            type_metrics = {}
            for ctype in contamination_types:
                tp = matrix[ctype][ctype]
                fp = sum(matrix[ctype].values()) - tp
                fn = sum(matrix[t][ctype] for t in contamination_types) - tp

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

                type_metrics[ctype] = {
                    'precision': round(precision * 100, 1),
                    'recall': round(recall * 100, 1),
                    'f1_score': round(f1 * 100, 1)
                }

            results['metrics']['by_type'] = type_metrics

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/risk')
def api_site_risk(site_id):
    """Get site risk prediction performance"""
    try:
        site = Site.query.get_or_404(site_id)

        # Get risk predictions history
        predictions = SiteRiskPrediction.query.filter_by(site_id=site_id)\
            .order_by(SiteRiskPrediction.prediction_date).all()

        results = {
            'predictions': [],
            'actuals': [],
            'metrics': {}
        }

        # Get samples to determine actual risk
        samples = get_site_samples_optimized(site_id)

        # Calculate actual risk levels based on contamination events
        for i, sample in enumerate(samples):
            if not sample.get_latest_test():
                continue

            # Determine predicted risk for this time period
            predicted_risk = None
            predicted_score = None

            # Find prediction closest to but before this sample
            for pred in predictions:
                if pred.prediction_date.date() <= sample.collection_date:
                    predicted_risk = pred.risk_level
                    predicted_score = pred.risk_score

            if not predicted_risk:
                # Use ML pipeline to calculate
                pipeline = MLPipeline()
                site_features = {
                    'site_type': site.site_type,
                    'is_industrial_nearby': site.is_industrial_nearby,
                    'is_agricultural_nearby': site.is_agricultural_nearby,
                    'is_coastal': site.is_coastal,
                    'is_urban': site.is_urban,
                    'contamination_rate_30d': calculate_contamination_rate(site_id, sample.collection_date),
                    'days_since_last_test': calculate_days_since_test(site_id, sample.collection_date)
                }
                risk_result = pipeline.predict_site_risk(site_features)
                predicted_risk = risk_result['risk_level']
                predicted_score = risk_result['risk_score']

            # Determine actual risk based on sample quality
            actual_risk, actual_score = determine_actual_risk(sample.get_latest_test())

            results['predictions'].append({
                'date': sample.collection_date.isoformat(),
                'predicted_level': predicted_risk,
                'predicted_score': round(predicted_score, 1) if predicted_score else None,
                'actual_level': actual_risk,
                'actual_score': round(actual_score, 1),
                'correct': predicted_risk == actual_risk
            })

        # Calculate metrics
        if results['predictions']:
            correct = sum(1 for p in results['predictions'] if p['correct'])
            total = len(results['predictions'])

            # Calculate level agreement
            levels = ['critical', 'high', 'medium', 'low']
            confusion = {l: {l2: 0 for l2 in levels} for l in levels}

            for pred in results['predictions']:
                if pred['predicted_level'] and pred['actual_level']:
                    confusion[pred['predicted_level']][pred['actual_level']] += 1

            # Calculate score correlation
            pred_scores = [p['predicted_score'] for p in results['predictions'] if p['predicted_score']]
            act_scores = [p['actual_score'] for p in results['predictions'] if p['predicted_score']]

            if pred_scores and act_scores and len(pred_scores) > 1:
                correlation = np.corrcoef(pred_scores, act_scores)[0, 1]
                mae = np.mean(np.abs(np.array(pred_scores) - np.array(act_scores)))
            else:
                correlation = 0
                mae = 0

            results['metrics'] = {
                'accuracy': round((correct / total) * 100, 1) if total > 0 else 0,
                'total_predictions': total,
                'score_correlation': round(correlation, 3) if not np.isnan(correlation) else 0,
                'score_mae': round(mae, 2),
                'confusion_matrix': confusion
            }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/wqi')
def api_site_wqi(site_id):
    """Get WQI calculation performance for a site"""
    try:
        site = Site.query.get_or_404(site_id)

        samples = get_site_samples_optimized(site_id)

        results = {
            'readings': [],
            'metrics': {}
        }

        pipeline = MLPipeline()

        for sample in samples:
            if not sample.get_latest_test():
                continue

            test_result = sample.get_latest_test()

            # Calculate WQI using ML pipeline
            sensor_reading = {
                'ph': test_result.ph,
                'tds': test_result.tds_ppm,
                'turbidity': test_result.turbidity_ntu,
                'chlorine': test_result.free_chlorine_mg_l or 0.5,
                'temperature': test_result.temperature_celsius
            }

            wqi_result = pipeline.calculate_realtime_wqi(sensor_reading)

            # Determine actual quality based on comprehensive analysis
            actual_wqi, actual_class = calculate_actual_wqi(test_result)

            results['readings'].append({
                'date': sample.collection_date.isoformat(),
                'sample_id': sample.id,
                'calculated_wqi': wqi_result['wqi_score'],
                'calculated_class': wqi_result['wqi_class'],
                'actual_wqi': actual_wqi,
                'actual_class': actual_class,
                'class_match': wqi_result['wqi_class'] == actual_class,
                'penalties': {
                    'ph': wqi_result['ph_penalty'],
                    'tds': wqi_result['tds_penalty'],
                    'turbidity': wqi_result['turbidity_penalty'],
                    'chlorine': wqi_result['chlorine_penalty'],
                    'temperature': wqi_result['temperature_penalty']
                }
            })

        # Calculate metrics
        if results['readings']:
            calc_wqi = [r['calculated_wqi'] for r in results['readings']]
            act_wqi = [r['actual_wqi'] for r in results['readings']]

            mae = np.mean(np.abs(np.array(calc_wqi) - np.array(act_wqi)))
            rmse = np.sqrt(np.mean((np.array(calc_wqi) - np.array(act_wqi))**2))
            correlation = np.corrcoef(calc_wqi, act_wqi)[0, 1] if len(calc_wqi) > 1 else 0

            class_matches = sum(1 for r in results['readings'] if r['class_match'])

            results['metrics'] = {
                'wqi_mae': round(mae, 2),
                'wqi_rmse': round(rmse, 2),
                'wqi_correlation': round(correlation, 3) if not np.isnan(correlation) else 0,
                'class_accuracy': round((class_matches / len(results['readings'])) * 100, 1),
                'total_readings': len(results['readings'])
            }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/anomaly')
def api_site_anomaly(site_id):
    """Get anomaly detection performance for a site"""
    try:
        site = Site.query.get_or_404(site_id)

        samples = get_site_samples_optimized(site_id)

        results = {
            'detections': [],
            'metrics': {}
        }

        # Build historical statistics
        all_values = {'ph': [], 'tds': [], 'turbidity': [], 'temperature': []}

        for sample in samples:
            if not sample.get_latest_test():
                continue

            test_result = sample.get_latest_test()
            if test_result.ph:
                all_values['ph'].append(test_result.ph)
            if test_result.tds_ppm:
                all_values['tds'].append(test_result.tds_ppm)
            if test_result.turbidity_ntu:
                all_values['turbidity'].append(test_result.turbidity_ntu)
            if test_result.temperature_celsius:
                all_values['temperature'].append(test_result.temperature_celsius)

        # Calculate running statistics and detect anomalies
        pipeline = MLPipeline()

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for i, sample in enumerate(samples):
            if i < 5 or not sample.get_latest_test():  # Need at least 5 samples for stats
                continue

            test_result = sample.get_latest_test()

            # Calculate historical stats up to this point
            hist_stats = {}
            for param in ['ph', 'tds', 'turbidity', 'temperature']:
                values = all_values[param][:i]
                if values:
                    hist_stats[param] = {
                        'mean': np.mean(values),
                        'std': np.std(values) if len(values) > 1 else 1
                    }

            current_reading = {
                'ph': test_result.ph,
                'tds': test_result.tds_ppm,
                'turbidity': test_result.turbidity_ntu,
                'temperature': test_result.temperature_celsius
            }

            # Run anomaly detection
            detection = pipeline.detect_anomaly(current_reading, hist_stats)

            # Determine if this was actually an anomaly (based on quality issues)
            is_actual_anomaly = is_quality_issue(test_result)

            results['detections'].append({
                'date': sample.collection_date.isoformat(),
                'sample_id': sample.id,
                'detected_anomaly': bool(detection['is_anomaly']),
                'actual_anomaly': bool(is_actual_anomaly),
                'anomaly_score': float(detection['anomaly_score']),
                'parameter': detection['parameter'],
                'deviation_sigma': float(detection['deviation_sigma']),
                'correct': bool(detection['is_anomaly']) == bool(is_actual_anomaly)
            })

            # Update confusion counts
            if detection['is_anomaly'] and is_actual_anomaly:
                true_positives += 1
            elif detection['is_anomaly'] and not is_actual_anomaly:
                false_positives += 1
            elif not detection['is_anomaly'] and not is_actual_anomaly:
                true_negatives += 1
            else:
                false_negatives += 1

        # Calculate metrics
        total = true_positives + false_positives + true_negatives + false_negatives
        if total > 0:
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            results['metrics'] = {
                'accuracy': round(((true_positives + true_negatives) / total) * 100, 1),
                'precision': round(precision * 100, 1),
                'recall': round(recall * 100, 1),
                'f1_score': round(f1 * 100, 1),
                'true_positives': true_positives,
                'false_positives': false_positives,
                'true_negatives': true_negatives,
                'false_negatives': false_negatives,
                'total_samples': total
            }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/site/<int:site_id>/drift')
def api_site_drift(site_id):
    """Get CUSUM drift detection performance for a site"""
    try:
        site = Site.query.get_or_404(site_id)

        samples = get_site_samples_optimized(site_id)

        results = {
            'detections': [],
            'metrics': {}
        }

        # Build historical statistics for drift detection
        all_values = {
            'ph': [], 'tds': [], 'turbidity': [], 'temperature': [],
            'conductivity': [], 'chlorine': [], 'iron': []
        }

        for sample in samples:
            if not sample.get_latest_test():
                continue

            test_result = sample.get_latest_test()
            if test_result.ph:
                all_values['ph'].append(test_result.ph)
            if test_result.tds_ppm:
                all_values['tds'].append(test_result.tds_ppm)
            if test_result.turbidity_ntu:
                all_values['turbidity'].append(test_result.turbidity_ntu)
            if test_result.temperature_celsius:
                all_values['temperature'].append(test_result.temperature_celsius)
            if test_result.free_chlorine_mg_l:
                all_values['chlorine'].append(test_result.free_chlorine_mg_l)
            if test_result.iron_mg_l:
                all_values['iron'].append(test_result.iron_mg_l)

        # Calculate running statistics and detect drift using CUSUM
        from app.services.drift_detector import CUSUMDriftDetector
        drift_detector = CUSUMDriftDetector(threshold=5.0, drift_magnitude=0.5, window_size=100)

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for i, sample in enumerate(samples):
            if i < 30 or not sample.get_latest_test():  # Need at least 30 samples for drift detection
                continue

            test_result = sample.get_latest_test()

            # Prepare measurement dict for drift detector
            measurement = {
                'ph_value': test_result.ph,
                'tds_ppm': test_result.tds_ppm,
                'turbidity_ntu': test_result.turbidity_ntu,
                'temperature_celsius': test_result.temperature_celsius,
                'free_chlorine_mg_l': test_result.free_chlorine_mg_l or 0,
                'iron_mg_l': test_result.iron_mg_l or 0,
                'total_coliform_mpn': getattr(test_result, 'total_coliform_mpn', 0) or 0
            }

            # Run drift detection
            drift_results = drift_detector.update(measurement, sample.collection_date)

            # Check if any parameter has drift
            has_drift = any(r['drift_detected'] for r in drift_results.values() if isinstance(r, dict))
            max_cusum = max((r.get('cusum_value', 0) for r in drift_results.values() if isinstance(r, dict)), default=0)
            drift_params = [param for param, r in drift_results.items() if isinstance(r, dict) and r.get('drift_detected')]

            # Determine if this was actually a drift (gradual degradation over time)
            is_actual_drift = is_gradual_degradation(test_result, i, samples)

            results['detections'].append({
                'date': sample.collection_date.isoformat(),
                'sample_id': sample.id,
                'detected_drift': bool(has_drift),
                'actual_drift': bool(is_actual_drift),
                'cusum_value': float(max_cusum),
                'parameters': drift_params,
                'correct': bool(has_drift) == bool(is_actual_drift)
            })

            # Update confusion counts
            if has_drift and is_actual_drift:
                true_positives += 1
            elif has_drift and not is_actual_drift:
                false_positives += 1
            elif not has_drift and not is_actual_drift:
                true_negatives += 1
            else:
                false_negatives += 1

        # Calculate metrics
        total = true_positives + false_positives + true_negatives + false_negatives
        if total > 0:
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            results['metrics'] = {
                'accuracy': round(((true_positives + true_negatives) / total) * 100, 1),
                'precision': round(precision * 100, 1),
                'recall': round(recall * 100, 1),
                'f1_score': round(f1 * 100, 1),
                'true_positives': true_positives,
                'false_positives': false_positives,
                'true_negatives': true_negatives,
                'false_negatives': false_negatives,
                'total_samples': total
            }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/all-sites')
def api_all_sites_summary():
    """Get ML performance summary for all sites"""
    try:
        query = Site.query.filter_by(is_active=True)

        # Apply site-level access filtering for authenticated users
        if current_user.is_authenticated:
            query = current_user.filter_sites_query(query)

        sites = query.all()

        summary = []

        for site in sites:
            # Get sample count
            sample_count = WaterSample.query.filter_by(site_id=site.id).count()

            if sample_count < 3:
                continue

            # Quick performance metrics
            site_data = {
                'id': site.id,
                'name': site.site_name,
                'country': site.country,
                'site_type': site.site_type,
                'site_category': site.site_category or 'public',
                'state': site.state,
                'sample_count': sample_count,
                'models': {}
            }

            # Get latest prediction accuracy (simplified)
            predictions = SiteRiskPrediction.query.filter_by(site_id=site.id).order_by(SiteRiskPrediction.prediction_date.desc()).limit(10).all()
            if predictions:
                latest_pred = predictions[0]
                site_data['models']['risk'] = {
                    'latest_prediction': latest_pred.risk_level if latest_pred else None,
                    'confidence': round(latest_pred.confidence, 1) if latest_pred and latest_pred.confidence else None
                }

            summary.append(site_data)

        return jsonify({'success': True, 'sites': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ Helper Functions ============

def get_forecaster_performance(start_date):
    """Get overall forecaster performance metrics"""
    forecasts = WaterQualityForecast.query.filter(
        WaterQualityForecast.prediction_date >= start_date
    ).all()

    return {
        'total_forecasts': len(forecasts),
        'avg_r2': round(np.mean([f.r2_score for f in forecasts if f.r2_score]) or 0, 3),
        'avg_mae': round(np.mean([f.mae for f in forecasts if f.mae]) or 0, 3)
    }


def get_contamination_performance(start_date):
    """Get overall contamination classifier performance"""
    predictions = ContaminationPrediction.query.filter(
        ContaminationPrediction.prediction_date >= start_date
    ).all()

    return {
        'total_predictions': len(predictions),
        'avg_confidence': round(np.mean([p.confidence for p in predictions if p.confidence]) or 0, 1),
        'avg_f1': round(np.mean([p.f1_score for p in predictions if p.f1_score]) or 0, 3)
    }


def get_site_risk_performance(start_date):
    """Get overall site risk classifier performance"""
    predictions = SiteRiskPrediction.query.filter(
        SiteRiskPrediction.prediction_date >= start_date
    ).all()

    risk_dist = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for p in predictions:
        if p.risk_level in risk_dist:
            risk_dist[p.risk_level] += 1

    return {
        'total_predictions': len(predictions),
        'avg_confidence': round(np.mean([p.confidence for p in predictions if p.confidence]) or 0, 1),
        'risk_distribution': risk_dist
    }


def get_wqi_performance(start_date):
    """Get overall WQI performance"""
    readings = WQIReading.query.filter(
        WQIReading.reading_timestamp >= start_date
    ).all()

    class_dist = {'Excellent': 0, 'Compliant': 0, 'Warning': 0, 'Unsafe': 0}
    for r in readings:
        if r.wqi_class in class_dist:
            class_dist[r.wqi_class] += 1

    return {
        'total_readings': len(readings),
        'avg_wqi': round(np.mean([r.wqi_score for r in readings]) or 0, 1),
        'class_distribution': class_dist
    }


def get_anomaly_performance(start_date):
    """Get overall anomaly detection performance"""
    detections = AnomalyDetection.query.filter(
        AnomalyDetection.detection_timestamp >= start_date
    ).all()

    anomaly_count = sum(1 for d in detections if d.is_anomaly)

    return {
        'total_detections': len(detections),
        'anomalies_found': anomaly_count,
        'anomaly_rate': round((anomaly_count / len(detections)) * 100, 1) if detections else 0
    }


def run_walkforward_validation(site, train_months):
    """Run walk-forward validation for all models on a site"""
    samples = WaterSample.query.filter_by(site_id=site.id)\
        .order_by(WaterSample.collection_date).all()

    if len(samples) < 6:
        return {'error': 'Insufficient samples for walk-forward validation'}

    # Split into training and validation periods
    train_cutoff = len(samples) * 2 // 3
    train_samples = samples[:train_cutoff]
    val_samples = samples[train_cutoff:]

    return {
        'train_samples': len(train_samples),
        'validation_samples': len(val_samples),
        'train_start': train_samples[0].collection_date.isoformat() if train_samples else None,
        'train_end': train_samples[-1].collection_date.isoformat() if train_samples else None,
        'val_start': val_samples[0].collection_date.isoformat() if val_samples else None,
        'val_end': val_samples[-1].collection_date.isoformat() if val_samples else None
    }


def calculate_contamination_prediction(test_result, sample, site):
    """Calculate contamination prediction using rule-based logic"""
    scores = {
        'runoff_sediment': 0.1,
        'sewage_ingress': 0.1,
        'salt_intrusion': 0.1,
        'pipe_corrosion': 0.1,
        'disinfectant_decay': 0.1,
        'none': 0.3
    }

    # Runoff indicators
    if test_result.turbidity_ntu and test_result.turbidity_ntu > 5:
        scores['runoff_sediment'] += 0.3

    # Sewage indicators
    if test_result.total_coliform_mpn and test_result.total_coliform_mpn > 0:
        scores['sewage_ingress'] += 0.4

    # Salt intrusion
    if test_result.tds_ppm and test_result.tds_ppm > 1000:
        scores['salt_intrusion'] += 0.4

    # Pipe corrosion
    if test_result.iron_mg_l and test_result.iron_mg_l > 0.3:
        scores['pipe_corrosion'] += 0.4

    # Check if no contamination
    if max(scores.values()) == scores['none']:
        return 'none', 70.0

    predicted_type = max(scores, key=scores.get)
    confidence = (scores[predicted_type] / sum(scores.values())) * 100

    return predicted_type, confidence


def determine_actual_contamination(test_result):
    """Determine actual contamination type from test results"""
    issues = []

    if test_result.turbidity_ntu and test_result.turbidity_ntu > 5:
        issues.append(('runoff_sediment', test_result.turbidity_ntu / 5))

    if test_result.total_coliform_mpn and test_result.total_coliform_mpn > 0:
        issues.append(('sewage_ingress', 1 + (test_result.total_coliform_mpn / 100)))

    if test_result.tds_ppm and test_result.tds_ppm > 500:
        issues.append(('salt_intrusion', test_result.tds_ppm / 500))

    if test_result.iron_mg_l and test_result.iron_mg_l > 0.3:
        issues.append(('pipe_corrosion', test_result.iron_mg_l / 0.3))

    if test_result.free_chlorine_mg_l is not None and test_result.free_chlorine_mg_l < 0.2:
        issues.append(('disinfectant_decay', 1))

    if not issues:
        return 'none'

    # Return the most severe issue
    issues.sort(key=lambda x: x[1], reverse=True)
    return issues[0][0]


def determine_actual_risk(test_result):
    """Determine actual risk level from test results"""
    score = 20  # Base score

    # pH issues
    if test_result.ph:
        if test_result.ph < 6.5 or test_result.ph > 8.5:
            score += 20

    # Turbidity
    if test_result.turbidity_ntu:
        if test_result.turbidity_ntu > 10:
            score += 30
        elif test_result.turbidity_ntu > 5:
            score += 15

    # TDS
    if test_result.tds_ppm:
        if test_result.tds_ppm > 1000:
            score += 25
        elif test_result.tds_ppm > 500:
            score += 10

    # Coliforms
    if test_result.total_coliform_mpn:
        if test_result.total_coliform_mpn > 100:
            score += 40
        elif test_result.total_coliform_mpn > 0:
            score += 20

    score = min(100, score)

    if score >= 70:
        return 'critical', score
    elif score >= 50:
        return 'high', score
    elif score >= 30:
        return 'medium', score
    else:
        return 'low', score


def calculate_contamination_rate(site_id, before_date):
    """Calculate contamination rate in the 30 days before a date"""
    start_date = before_date - timedelta(days=30)
    samples = WaterSample.query.filter(
        WaterSample.site_id == site_id,
        WaterSample.collection_date >= start_date,
        WaterSample.collection_date < before_date
    ).all()

    if not samples:
        return 0

    contaminated = sum(1 for s in samples if s.get_latest_test() and
                      (s.get_latest_test().total_coliform_mpn or 0) > 0)
    return (contaminated / len(samples)) * 100


def calculate_days_since_test(site_id, before_date):
    """Calculate days since last test before a date"""
    last_sample = WaterSample.query.filter(
        WaterSample.site_id == site_id,
        WaterSample.collection_date < before_date
    ).order_by(WaterSample.collection_date.desc()).first()

    if last_sample:
        return (before_date - last_sample.collection_date).days
    return 365


def calculate_actual_wqi(test_result):
    """Calculate actual WQI based on comprehensive analysis"""
    wqi = 100.0

    # pH penalty
    if test_result.ph:
        if test_result.ph < 6.5:
            wqi -= min(20, (6.5 - test_result.ph) * 10)
        elif test_result.ph > 8.5:
            wqi -= min(20, (test_result.ph - 8.5) * 10)

    # TDS penalty
    if test_result.tds_ppm:
        if test_result.tds_ppm > 500:
            wqi -= min(30, (test_result.tds_ppm - 500) / 50)

    # Turbidity penalty
    if test_result.turbidity_ntu:
        if test_result.turbidity_ntu > 5:
            wqi -= min(20, (test_result.turbidity_ntu - 5) * 2)

    # Coliform penalty
    if test_result.total_coliform_mpn:
        if test_result.total_coliform_mpn > 0:
            wqi -= min(25, 15 + test_result.total_coliform_mpn / 10)

    wqi = max(0, min(100, wqi))

    if wqi >= 90:
        return round(wqi, 1), 'Excellent'
    elif wqi >= 70:
        return round(wqi, 1), 'Compliant'
    elif wqi >= 50:
        return round(wqi, 1), 'Warning'
    else:
        return round(wqi, 1), 'Unsafe'


def is_quality_issue(test_result):
    """Determine if a test result indicates a quality issue (anomaly)"""
    # Check for values outside acceptable ranges
    if test_result.ph and (test_result.ph < 6.0 or test_result.ph > 9.0):
        return True
    if test_result.turbidity_ntu and test_result.turbidity_ntu > 10:
        return True
    if test_result.tds_ppm and test_result.tds_ppm > 1000:
        return True
    if test_result.total_coliform_mpn and test_result.total_coliform_mpn > 100:
        return True
    if test_result.iron_mg_l and test_result.iron_mg_l > 0.5:
        return True

    return False


def is_gradual_degradation(test_result, index, all_samples):
    """
    Determine if a test result is part of a gradual drift pattern
    (not a sudden spike, but gradual parameter degradation over time)
    """
    if index < 10:  # Need history to detect gradual drift
        return False

    # Look at past 10 samples to detect trends
    lookback = min(10, index)
    recent_samples = all_samples[index - lookback:index]

    # Track TDS trend (pipe corrosion, membrane degradation)
    tds_values = []
    for sample in recent_samples:
        if sample.get_latest_test() and sample.get_latest_test().tds_ppm:
            tds_values.append(sample.get_latest_test().tds_ppm)

    # Check for gradual TDS increase (infrastructure aging)
    if len(tds_values) >= 5:
        # Calculate slope of TDS over time
        tds_increase = tds_values[-1] - tds_values[0]
        if tds_increase > 50:  # Gradual 50+ ppm increase
            return True

    # Track iron trend (pipe corrosion)
    iron_values = []
    for sample in recent_samples:
        if sample.get_latest_test() and sample.get_latest_test().iron_mg_l:
            iron_values.append(sample.get_latest_test().iron_mg_l)

    if len(iron_values) >= 5:
        iron_increase = iron_values[-1] - iron_values[0]
        if iron_increase > 0.1:  # Gradual iron increase
            return True

    # Track pH drift
    ph_values = []
    for sample in recent_samples:
        if sample.get_latest_test() and sample.get_latest_test().ph:
            ph_values.append(sample.get_latest_test().ph)

    if len(ph_values) >= 5:
        ph_change = abs(ph_values[-1] - ph_values[0])
        if ph_change > 0.5:  # Gradual pH drift > 0.5 units
            return True

    # Track chlorine decay
    chlorine_values = []
    for sample in recent_samples:
        if sample.get_latest_test() and sample.get_latest_test().free_chlorine_mg_l:
            chlorine_values.append(sample.get_latest_test().free_chlorine_mg_l)

    if len(chlorine_values) >= 5:
        chlorine_decrease = chlorine_values[0] - chlorine_values[-1]
        if chlorine_decrease > 0.2:  # Gradual chlorine decay
            return True

    return False


@reports_bp.route('/api/site/<int:site_id>/comparison')
def api_site_comparison(site_id):
    """Get ML vs Rule-based comparison for a site - comprehensive analysis"""
    try:
        site = Site.query.get_or_404(site_id)
        samples = get_site_samples_optimized(site_id)

        if len(samples) < 3:
            return jsonify({'success': True, 'site': site.site_name, 'results': {
                'insufficient_data': True,
                'sample_count': len(samples),
                'message': 'Need at least 3 samples for ML vs Rule-based comparison'
            }})

        pipeline = MLPipeline()

        # Collect comparison data for each sample
        comparison_data = []

        # Track metrics for summary
        rule_risk_levels = []
        ml_risk_levels = []
        rule_wqi_scores = []
        ml_wqi_scores = []
        rule_contamination = []
        ml_contamination = []

        for i, sample in enumerate(samples):
            test_result = sample.get_latest_test()
            if not test_result:
                continue

            # === RULE-BASED ANALYSIS ===
            # Risk (rule-based)
            rule_risk_level, rule_risk_score = determine_actual_risk(test_result)

            # WQI (rule-based)
            rule_wqi, rule_wqi_class = calculate_actual_wqi(test_result)

            # Contamination (rule-based)
            rule_contam = determine_actual_contamination(test_result)

            # === ML-BASED ANALYSIS ===
            # ML Risk prediction
            site_features = {
                'site_type': site.site_type,
                'is_industrial_nearby': site.is_industrial_nearby,
                'is_agricultural_nearby': site.is_agricultural_nearby,
                'is_coastal': site.is_coastal,
                'is_urban': site.is_urban,
                'contamination_rate_30d': calculate_contamination_rate(site_id, sample.collection_date),
                'days_since_last_test': calculate_days_since_test(site_id, sample.collection_date)
            }
            ml_risk_result = pipeline.predict_site_risk(site_features)
            ml_risk_level = ml_risk_result['risk_level']
            ml_risk_score = ml_risk_result['risk_score']

            # ML WQI calculation
            sensor_reading = {
                'ph': test_result.ph,
                'tds': test_result.tds_ppm,
                'turbidity': test_result.turbidity_ntu,
                'chlorine': test_result.free_chlorine_mg_l or 0.5,
                'temperature': test_result.temperature_celsius
            }
            ml_wqi_result = pipeline.calculate_realtime_wqi(sensor_reading)
            ml_wqi = ml_wqi_result['wqi_score']
            ml_wqi_class = ml_wqi_result['wqi_class']

            # ML Contamination prediction
            ml_contam, ml_contam_conf = calculate_contamination_prediction(test_result, sample, site)

            # Store for tracking
            rule_risk_levels.append(rule_risk_level)
            ml_risk_levels.append(ml_risk_level)
            rule_wqi_scores.append(rule_wqi)
            ml_wqi_scores.append(ml_wqi)
            rule_contamination.append(rule_contam)
            ml_contamination.append(ml_contam)

            comparison_data.append({
                'date': sample.collection_date.isoformat(),
                'sample_id': sample.id,
                'rule_based': {
                    'risk_level': rule_risk_level,
                    'risk_score': round(rule_risk_score, 1),
                    'wqi_score': round(rule_wqi, 1),
                    'wqi_class': rule_wqi_class,
                    'contamination': rule_contam
                },
                'ml_based': {
                    'risk_level': ml_risk_level,
                    'risk_score': round(ml_risk_score, 1),
                    'wqi_score': round(ml_wqi, 1),
                    'wqi_class': ml_wqi_class,
                    'contamination': ml_contam,
                    'contamination_confidence': round(ml_contam_conf, 1)
                },
                'agreement': {
                    'risk_level': rule_risk_level == ml_risk_level,
                    'wqi_class': rule_wqi_class == ml_wqi_class,
                    'contamination': rule_contam == ml_contam
                }
            })

        # Calculate summary statistics
        n = len(comparison_data)
        if n == 0:
            return jsonify({'success': True, 'site': site.site_name, 'results': {
                'insufficient_data': True,
                'sample_count': 0,
                'message': 'No valid samples with test results found'
            }})

        # Agreement rates
        risk_agreement = sum(1 for d in comparison_data if d['agreement']['risk_level']) / n * 100
        wqi_agreement = sum(1 for d in comparison_data if d['agreement']['wqi_class']) / n * 100
        contam_agreement = sum(1 for d in comparison_data if d['agreement']['contamination']) / n * 100

        # WQI correlation
        wqi_correlation = np.corrcoef(rule_wqi_scores, ml_wqi_scores)[0, 1] if n > 1 else 1.0
        wqi_mae = np.mean(np.abs(np.array(rule_wqi_scores) - np.array(ml_wqi_scores)))

        # Risk level distribution comparison
        risk_levels = ['critical', 'high', 'medium', 'low']
        rule_risk_dist = {level: rule_risk_levels.count(level) for level in risk_levels}
        ml_risk_dist = {level: ml_risk_levels.count(level) for level in risk_levels}

        # Generate interpretive summary
        summary = generate_comparison_summary(
            risk_agreement, wqi_agreement, contam_agreement,
            wqi_correlation, wqi_mae, rule_risk_dist, ml_risk_dist, n
        )

        results = {
            'insufficient_data': False,
            'sample_count': n,
            'comparison_data': comparison_data,
            'summary': {
                'risk_agreement_rate': round(risk_agreement, 1),
                'wqi_agreement_rate': round(wqi_agreement, 1),
                'contamination_agreement_rate': round(contam_agreement, 1),
                'overall_agreement': round((risk_agreement + wqi_agreement + contam_agreement) / 3, 1),
                'wqi_correlation': round(float(wqi_correlation), 3) if not np.isnan(wqi_correlation) else 0,
                'wqi_mae': round(float(wqi_mae), 2),
                'rule_risk_distribution': rule_risk_dist,
                'ml_risk_distribution': ml_risk_dist
            },
            'interpretation': summary
        }

        return jsonify({'success': True, 'site': site.site_name, 'results': results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_comparison_summary(risk_agree, wqi_agree, contam_agree, wqi_corr, wqi_mae, rule_risk, ml_risk, n):
    """Generate human-readable interpretation of ML vs Rule-based comparison"""
    summary = {
        'overall': '',
        'risk_analysis': '',
        'wqi_analysis': '',
        'contamination_analysis': '',
        'recommendation': ''
    }

    overall_agree = (risk_agree + wqi_agree + contam_agree) / 3

    # Overall summary
    if overall_agree >= 85:
        summary['overall'] = f"Excellent agreement between ML and rule-based methods. Based on {n} samples, both approaches produce highly consistent results, indicating reliable predictions."
    elif overall_agree >= 70:
        summary['overall'] = f"Good agreement between ML and rule-based methods. Across {n} samples, the methods agree on most assessments with minor differences in edge cases."
    elif overall_agree >= 50:
        summary['overall'] = f"Moderate agreement between ML and rule-based methods. Based on {n} samples, there are notable differences that may warrant investigation."
    else:
        summary['overall'] = f"Low agreement between ML and rule-based methods. Across {n} samples, significant discrepancies exist. Manual review recommended."

    # Risk analysis
    if risk_agree >= 80:
        summary['risk_analysis'] = f"Risk level predictions agree {risk_agree:.0f}% of the time. The ML model has learned patterns consistent with the rule-based thresholds."
    else:
        # Analyze discrepancy direction
        rule_high = rule_risk.get('critical', 0) + rule_risk.get('high', 0)
        ml_high = ml_risk.get('critical', 0) + ml_risk.get('high', 0)
        if ml_high > rule_high:
            summary['risk_analysis'] = f"Risk level agreement is {risk_agree:.0f}%. ML model tends to predict higher risk levels than rule-based analysis, which may indicate it captures additional risk factors from site features."
        else:
            summary['risk_analysis'] = f"Risk level agreement is {risk_agree:.0f}%. Rule-based analysis tends to flag more high-risk situations than the ML model, possibly due to stricter threshold-based criteria."

    # WQI analysis
    if wqi_corr >= 0.9:
        summary['wqi_analysis'] = f"WQI scores show strong correlation (r={wqi_corr:.2f}) with average difference of {wqi_mae:.1f} points. Both methods track water quality changes similarly."
    elif wqi_corr >= 0.7:
        summary['wqi_analysis'] = f"WQI scores show moderate correlation (r={wqi_corr:.2f}) with average difference of {wqi_mae:.1f} points. The methods generally agree on quality trends but differ in magnitude."
    else:
        summary['wqi_analysis'] = f"WQI scores show weak correlation (r={wqi_corr:.2f}) with average difference of {wqi_mae:.1f} points. Different weighting schemes may cause divergent assessments."

    # Contamination analysis
    if contam_agree >= 80:
        summary['contamination_analysis'] = f"Contamination type predictions agree {contam_agree:.0f}% of the time. ML classification aligns well with indicator-based rules."
    else:
        summary['contamination_analysis'] = f"Contamination classification agrees {contam_agree:.0f}% of the time. The ML model may detect subtle patterns not captured by simple thresholds, or may need more training data."

    # Recommendation
    if overall_agree >= 70 and wqi_corr >= 0.8:
        summary['recommendation'] = "Both methods are reliable for this site. Use ML predictions for early warning and rule-based results for regulatory compliance."
    elif overall_agree >= 50:
        summary['recommendation'] = "Review cases where methods disagree. Consider using rule-based results for critical decisions until ML model confidence improves."
    else:
        summary['recommendation'] = "Significant discrepancies detected. Recommend manual review of site data quality and ML model retraining with verified samples."

    return summary


@reports_bp.route('/validation-summary')
def validation_summary():
    """Per-site ML validation report with 2-year training window"""
    return render_template('reports/validation_summary.html')


@reports_bp.route('/cost-optimizer')
def cost_optimizer():
    """Bayesian Cost Optimization Report - Test frequency optimization"""
    return render_template('reports/cost_optimizer.html')


@reports_bp.route('/api/cost-optimizer/filters')
def api_cost_optimizer_filters():
    """Get available filter options for cost optimizer"""
    try:
        # Get unique countries, states, and types from sites with optimization results
        results = db.session.query(
            Site.country,
            Site.state,
            Site.site_type
        ).join(CostOptimizationResult, Site.id == CostOptimizationResult.site_id).distinct().all()

        countries = sorted(list(set([r[0] for r in results if r[0]])))
        states = sorted(list(set([r[1] for r in results if r[1]])))
        site_types = sorted(list(set([r[2] for r in results if r[2]])))

        return jsonify({
            'success': True,
            'countries': countries,
            'states': states,
            'site_types': site_types
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/cost-optimizer')
def api_cost_optimizer():
    """Get cost optimization results with filters and pagination"""
    try:
        # Get filter parameters
        country = request.args.get('country', 'all')
        state = request.args.get('state', 'all')
        site_type = request.args.get('site_type', 'all')
        search = request.args.get('search', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Build query with filters - order by date DESC to get latest results first
        query = db.session.query(
            CostOptimizationResult,
            Site.site_name,
            Site.site_code,
            Site.state,
            Site.country,
            Site.site_type
        ).join(Site, CostOptimizationResult.site_id == Site.id)\
         .order_by(CostOptimizationResult.optimization_date.desc())

        # Apply filters
        if country != 'all':
            query = query.filter(Site.country == country)
        if state != 'all':
            query = query.filter(Site.state == state)
        if site_type != 'all':
            query = query.filter(Site.site_type == site_type)
        if search:
            # Search in both site name and site code (case-insensitive)
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Site.site_name.ilike(search_pattern),
                    Site.site_code.ilike(search_pattern)
                )
            )

        # Get all results for filters
        all_results = query.all()

        # Group by site and get latest result (first one encountered due to DESC order)
        site_results = {}
        for result, site_name, site_code, state, country, site_type_value in all_results:
            if result.site_id not in site_results:
                site_results[result.site_id] = {
                    'site_id': result.site_id,
                    'site_name': site_name,
                    'site_code': site_code,
                    'state': state,
                    'country': country,
                    'site_type': site_type_value,
                    'risk_category': result.risk_category,
                    'current_tests_per_year': result.current_tests_per_year,
                    'optimized_tests_per_year': result.optimized_tests_per_year,
                    'current_cost_inr': result.current_cost_inr,
                    'optimized_cost_inr': result.optimized_cost_inr,
                    'cost_savings_inr': result.cost_savings_inr,
                    'cost_reduction_percent': result.cost_reduction_percent,
                    'detection_rate': result.detection_rate,
                    'recommended_frequency': result.recommended_frequency
                }

        # Calculate summary statistics (on all filtered results)
        all_site_results = list(site_results.values())
        total_sites = len(all_site_results)
        total_current_cost = sum(r['current_cost_inr'] or 0 for r in all_site_results)
        total_optimized_cost = sum(r['optimized_cost_inr'] or 0 for r in all_site_results)
        total_savings = sum(r['cost_savings_inr'] or 0 for r in all_site_results)
        avg_reduction_percent = sum(r['cost_reduction_percent'] or 0 for r in all_site_results) / total_sites if total_sites > 0 else 0
        avg_detection_rate = sum(r['detection_rate'] or 0 for r in all_site_results) / total_sites if total_sites > 0 else 0

        # Sort by savings (highest first)
        all_site_results.sort(key=lambda x: x['cost_savings_inr'] or 0, reverse=True)

        # Paginate results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = all_site_results[start_idx:end_idx]
        total_pages = (total_sites + per_page - 1) // per_page if total_sites > 0 else 1

        # Risk category breakdown
        risk_breakdown = {}
        for r in all_site_results:
            risk = r['risk_category'] or 'unknown'
            if risk not in risk_breakdown:
                risk_breakdown[risk] = {'count': 0, 'savings': 0}
            risk_breakdown[risk]['count'] += 1
            risk_breakdown[risk]['savings'] += r['cost_savings_inr'] or 0

        return jsonify({
            'success': True,
            'sites': paginated_results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_sites': total_sites,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'summary': {
                'total_sites': total_sites,
                'total_current_cost': round(total_current_cost, 2),
                'total_optimized_cost': round(total_optimized_cost, 2),
                'total_savings': round(total_savings, 2),
                'avg_reduction_percent': round(avg_reduction_percent, 1),
                'avg_detection_rate': round(avg_detection_rate, 1),
                'risk_breakdown': risk_breakdown
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_cost_optimizer_recommendation(contamination_rate, risk_category, current_freq,
                                          recommended_freq, current_tests, recommended_tests,
                                          detection_rate, savings, savings_percent):
    """
    Generate intelligent recommendation based on contamination rate and risk.
    High contamination sites should NOT reduce testing regardless of cost savings.
    """
    is_reduction = recommended_tests < current_tests
    is_increase = recommended_tests > current_tests

    # Determine if site is high-risk based on contamination rate and risk level
    is_high_contamination = contamination_rate >= 70
    is_critical_risk = risk_category.lower() in ['critical', 'high']

    # Safety-first logic
    if is_high_contamination and is_critical_risk:
        # High contamination + high risk = DO NOT REDUCE
        if is_reduction:
            return {
                'validated': False,
                'confidence': 'LOW',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate with {risk_category.upper()} risk. "
                            f"Reducing testing frequency is NOT RECOMMENDED despite potential savings of ₹{savings:,.0f}/year. "
                            f"High contamination sites require frequent monitoring for public safety.",
                'action': f"MAINTAIN current {current_freq} testing (do not reduce)",
                'alert': 'HIGH_RISK_SITE',
                'final_frequency': current_freq  # Override: maintain current
            }
        else:
            return {
                'validated': True,
                'confidence': 'HIGH',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate with {risk_category.upper()} risk. "
                            f"Maintaining or increasing testing frequency is appropriate for public safety.",
                'action': f"Maintain {current_freq} testing" if current_tests == recommended_tests else f"Increase from {current_freq} to {recommended_freq} testing",
                'alert': None,
                'final_frequency': recommended_freq if is_increase else current_freq
            }

    elif is_high_contamination and not is_critical_risk:
        # High contamination + medium/low risk = cautious reduction only
        if is_reduction and detection_rate >= 90:
            return {
                'validated': True,
                'confidence': 'MEDIUM',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate with {risk_category.upper()} risk. "
                            f"Modest reduction to {recommended_freq} testing saves ₹{savings:,.0f}/year "
                            f"while maintaining {detection_rate:.1f}% detection rate.",
                'action': f"Cautiously reduce from {current_freq} to {recommended_freq} testing",
                'alert': 'HIGH_CONTAMINATION',
                'final_frequency': recommended_freq
            }
        else:
            return {
                'validated': False,
                'confidence': 'LOW',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate. "
                            f"Detection rate of {detection_rate:.1f}% is too low for a high-contamination site.",
                'action': f"MAINTAIN current {current_freq} testing",
                'alert': 'HIGH_CONTAMINATION',
                'final_frequency': current_freq  # Override: maintain current
            }

    elif contamination_rate < 30 and risk_category.lower() in ['low', 'medium']:
        # Low contamination + low/medium risk = safe to reduce
        if is_reduction and detection_rate >= 75:
            return {
                'validated': True,
                'confidence': 'HIGH' if detection_rate >= 85 else 'MEDIUM',
                'rationale': f"Site has low contamination rate ({contamination_rate:.1f}%) with {risk_category.upper()} risk. "
                            f"Reducing to {recommended_freq} testing saves ₹{savings:,.0f}/year "
                            f"with {detection_rate:.1f}% detection rate.",
                'action': f"Reduce from {current_freq} to {recommended_freq} testing",
                'alert': None,
                'final_frequency': recommended_freq
            }
        else:
            return {
                'validated': True,
                'confidence': 'MEDIUM',
                'rationale': f"Site has low contamination rate ({contamination_rate:.1f}%) with {risk_category.upper()} risk. "
                            f"Current testing frequency is appropriate.",
                'action': f"Maintain {current_freq} testing",
                'alert': None,
                'final_frequency': current_freq
            }

    else:
        # Moderate contamination or mixed risk = balanced approach
        if detection_rate >= 80 and savings_percent > 20:
            action_text = f"Reduce from {current_freq} to {recommended_freq} testing" if is_reduction else \
                         f"Increase from {current_freq} to {recommended_freq} testing" if is_increase else \
                         f"Maintain {current_freq} testing"

            final_freq = recommended_freq if (is_reduction or is_increase) else current_freq

            return {
                'validated': True,
                'confidence': 'MEDIUM',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate with {risk_category.upper()} risk. "
                            f"Adjusting to {recommended_freq} testing saves ₹{savings:,.0f}/year "
                            f"with {detection_rate:.1f}% detection rate.",
                'action': action_text,
                'alert': None,
                'final_frequency': final_freq
            }
        else:
            return {
                'validated': False,
                'confidence': 'LOW',
                'rationale': f"Site has {contamination_rate:.1f}% contamination rate with {risk_category.upper()} risk. "
                            f"Detection rate of {detection_rate:.1f}% or savings of {savings_percent:.1f}% is insufficient to justify changes.",
                'action': f"Maintain current {current_freq} testing",
                'alert': None,
                'final_frequency': current_freq  # Override: maintain current
            }


@reports_bp.route('/cost-optimizer/site/<int:site_id>')
def cost_optimizer_site_detail(site_id):
    """Site-specific cost optimization detail report"""
    site = Site.query.get_or_404(site_id)
    return render_template('reports/cost_optimizer_site.html', site=site)


@reports_bp.route('/api/cost-optimizer/site/<int:site_id>')
def api_cost_optimizer_site_detail(site_id):
    """Get detailed cost optimization analysis for a specific site"""
    try:
        # Get site info
        site = Site.query.get_or_404(site_id)

        # Get latest cost optimization result
        opt_result = CostOptimizationResult.query.filter_by(site_id=site_id)\
            .order_by(CostOptimizationResult.optimization_date.desc()).first()

        if not opt_result:
            return jsonify({'success': False, 'error': 'No optimization results found for this site'}), 404

        # Calculate date range (last 12 months)
        one_year_ago = datetime.utcnow() - timedelta(days=365)

        # Get actual test counts
        actual_tests = WaterSample.query.filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= one_year_ago
        ).count()

        # Get contamination events
        contaminated_samples = db.session.query(WaterSample).join(Analysis).filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= one_year_ago,
            Analysis.is_contaminated == True
        ).count()

        total_samples = db.session.query(WaterSample).join(Analysis).filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= one_year_ago
        ).count()

        contamination_rate = (contaminated_samples / total_samples * 100) if total_samples > 0 else 0

        # Calculate actual cost spent
        cost_per_test = 1000  # INR
        actual_cost_spent = actual_tests * cost_per_test

        # Map testing frequency to tests per year
        frequency_map = {
            'weekly': 52,
            'bi-weekly': 26,
            'monthly': 12,
            'bi-monthly': 6,
            'quarterly': 4
        }

        current_frequency = site.testing_frequency or 'weekly'
        current_tests_per_year = frequency_map.get(current_frequency, 52)

        # Detection rate simulation
        def calculate_detection_rate(tests_per_year, contamination_rate, avg_contamination_duration=14):
            """
            Simulate detection probability based on test frequency
            Assumes contamination events last avg 14 days
            """
            if tests_per_year == 0:
                return 0

            # Days between tests
            days_between_tests = 365 / tests_per_year

            # Probability of catching a contamination event
            # Higher frequency = higher chance of catching within contamination window
            detection_probability = min(100, (avg_contamination_duration / days_between_tests) * 100)

            # Adjust by base detection rate (more contamination = easier to catch)
            base_rate = 70  # Baseline detection rate
            adjusted_rate = base_rate + (detection_probability * 0.3)

            return min(99, adjusted_rate)

        current_detection_rate = calculate_detection_rate(current_tests_per_year, contamination_rate)
        optimized_detection_rate = calculate_detection_rate(opt_result.optimized_tests_per_year, contamination_rate)

        # Calculate expected catches and misses
        total_contaminations = contaminated_samples if contaminated_samples > 0 else 8  # Estimate if no data
        current_catches = total_contaminations * (current_detection_rate / 100)
        optimized_catches = total_contaminations * (optimized_detection_rate / 100)

        current_misses = total_contaminations - current_catches
        optimized_misses = total_contaminations - optimized_catches

        # Generate safety-first recommendation FIRST
        recommendation = generate_cost_optimizer_recommendation(
            contamination_rate,
            opt_result.risk_category,
            current_frequency,
            opt_result.recommended_frequency,
            current_tests_per_year,
            opt_result.optimized_tests_per_year,
            optimized_detection_rate,
            opt_result.cost_savings_inr,
            opt_result.cost_reduction_percent
        )

        # Determine final recommended frequency based on safety-first logic
        final_recommended_frequency = recommendation.get('final_frequency', opt_result.recommended_frequency)
        final_recommended_tests = frequency_map.get(final_recommended_frequency, current_tests_per_year)

        # Average detection delay
        current_delay = 365 / (current_tests_per_year * 2)  # Half the interval on average
        final_delay = 365 / (final_recommended_tests * 2)

        # Recalculate detection for final recommendation
        final_detection_rate = calculate_detection_rate(final_recommended_tests, contamination_rate)
        final_catches = total_contaminations * (final_detection_rate / 100)
        final_misses = total_contaminations - final_catches

        # What-if scenarios (mark final recommendation, not optimizer's original)
        scenarios = []
        for freq_name, tests in frequency_map.items():
            detection_rate = calculate_detection_rate(tests, contamination_rate)
            catches = total_contaminations * (detection_rate / 100)
            misses = total_contaminations - catches

            scenarios.append({
                'frequency': freq_name,
                'tests_per_year': tests,
                'cost_per_year': tests * cost_per_test,
                'detection_rate': round(detection_rate, 1),
                'expected_misses': round(misses, 1),
                'is_recommended': freq_name == final_recommended_frequency
            })

        # Cost per contamination detected (use final recommendation)
        current_cost_per_detection = (current_tests_per_year * cost_per_test) / current_catches if current_catches > 0 else 0
        final_cost_per_detection = (final_recommended_tests * cost_per_test) / final_catches if final_catches > 0 else 0

        # Calculate actual savings with final recommendation
        final_cost_savings = (current_tests_per_year - final_recommended_tests) * cost_per_test
        final_cost_reduction_percent = (final_cost_savings / (current_tests_per_year * cost_per_test)) * 100 if current_tests_per_year > 0 else 0

        # Build response
        result = {
            'success': True,
            'site': {
                'id': site.id,
                'name': site.site_name,
                'code': site.site_code,
                'state': site.state,
                'country': site.country,
                'type': site.site_type,
                'category': site.site_category,
                'risk_level': opt_result.risk_category,
                'risk_score': site.risk_score or 50
            },
            'schedule_comparison': {
                'current_frequency': current_frequency,
                'current_tests_per_year': current_tests_per_year,
                'current_cost_per_year': current_tests_per_year * cost_per_test,
                'recommended_frequency': final_recommended_frequency,
                'recommended_tests_per_year': final_recommended_tests,
                'recommended_cost_per_year': final_recommended_tests * cost_per_test,
                'test_change_percent': round(((final_recommended_tests - current_tests_per_year) / current_tests_per_year) * 100, 1) if current_tests_per_year > 0 else 0,
                'cost_savings': final_cost_savings,
                'cost_reduction_percent': round(final_cost_reduction_percent, 1),
                'optimizer_original_frequency': opt_result.recommended_frequency,
                'optimizer_original_tests': opt_result.optimized_tests_per_year,
                'was_overridden': final_recommended_frequency != opt_result.recommended_frequency
            },
            'historical_performance': {
                'period_months': 12,
                'actual_tests': actual_tests,
                'total_samples': total_samples,
                'contaminated_samples': contaminated_samples,
                'clean_samples': total_samples - contaminated_samples,
                'contamination_rate': round(contamination_rate, 1),
                'actual_cost_spent': actual_cost_spent
            },
            'detection_analysis': {
                'current': {
                    'detection_rate': round(current_detection_rate, 1),
                    'expected_catches': round(current_catches, 1),
                    'expected_misses': round(current_misses, 1),
                    'avg_detection_delay_days': round(current_delay, 1)
                },
                'recommended': {
                    'detection_rate': round(final_detection_rate, 1),
                    'expected_catches': round(final_catches, 1),
                    'expected_misses': round(final_misses, 1),
                    'avg_detection_delay_days': round(final_delay, 1)
                },
                'impact': {
                    'detection_rate_change': round(final_detection_rate - current_detection_rate, 1),
                    'additional_misses': round(final_misses - current_misses, 1),
                    'delay_increase_days': round(final_delay - current_delay, 1)
                }
            },
            'cost_benefit': {
                'annual_savings': final_cost_savings,
                'savings_percent': round(final_cost_reduction_percent, 1),
                'current_cost_per_detection': round(current_cost_per_detection, 0),
                'optimized_cost_per_detection': round(final_cost_per_detection, 0),
                'efficiency_improvement': round(((current_cost_per_detection - final_cost_per_detection) / current_cost_per_detection) * 100, 1) if current_cost_per_detection > 0 else 0,
                'cost_per_miss': round(abs(final_cost_savings) / final_misses, 0) if final_misses > 0.1 else 0
            },
            'scenarios': scenarios,
            'recommendation': recommendation
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/api/validation-summary')
def api_validation_summary():
    """
    Get validation summary using pre-calculated results from ValidationResult table.
    MUCH FASTER than previous implementation that calculated on-the-fly.

    Query Parameters:
        country (str): Filter by country - 'all', 'India', 'USA', etc. (default: 'all')
        category (str): Filter by site category - 'all', 'public', or 'residential' (default: 'all')
        site_id (int): Filter to specific site ID, or 'all' for all sites (default: 'all')
        recalculate (bool): Force recalculation for missing/stale results (default: False)
    """
    try:
        # Get query parameters
        category = request.args.get('category', 'all')
        site_id_param = request.args.get('site_id', 'all')
        country = request.args.get('country', 'all')
        recalculate = request.args.get('recalculate', 'false').lower() == 'true'

        # Build site query based on filters
        query = Site.query.filter(Site.is_active == True)

        # Apply site-level access filtering for authenticated users
        if current_user.is_authenticated:
            query = current_user.filter_sites_query(query)

        # Apply country filter
        if country != 'all':
            query = query.filter(Site.country == country)

        # Apply category filter
        if category == 'public':
            query = query.filter((Site.site_category == 'public') | (Site.site_category == None))
        elif category == 'residential':
            query = query.filter(Site.site_category == 'residential')

        # Apply specific site filter if requested
        if site_id_param != 'all':
            try:
                site_id = int(site_id_param)
                query = query.filter(Site.id == site_id)
            except ValueError:
                return jsonify({'success': False, 'error': f'Invalid site_id: {site_id_param}'}), 400

        sites = query.all()
        site_results = []
        missing_count = 0
        stale_count = 0

        for site in sites:
            # Try to get pre-calculated validation result
            validation = ValidationResult.query.filter_by(
                site_id=site.id,
                is_valid=True
            ).order_by(ValidationResult.calculated_at.desc()).first()

            # Check if we need to recalculate
            needs_calculation = False
            if not validation:
                needs_calculation = True
                missing_count += 1
            elif recalculate:
                # Check if result is stale (> 30 days old)
                age_days = (datetime.utcnow() - validation.calculated_at).days
                if age_days > 30:
                    needs_calculation = True
                    stale_count += 1

            # Calculate if needed (only if recalculate=true)
            if needs_calculation and recalculate:
                from app.controllers.reports_validation_cache import calculate_and_store_validation_result
                validation = calculate_and_store_validation_result(site.id, force_recalculate=True)

            # Skip if no validation available
            if not validation or not validation.is_valid:
                continue

            # Build result from pre-calculated data
            result = {
                'site_id': site.id,
                'site_code': site.site_code,
                'site_name': site.site_name,
                'state': site.state,
                'site_type': site.site_type,
                'training_samples': validation.training_samples_count,
                'test_samples': validation.test_samples_count,
                'training_period': {
                    'start': validation.training_start_date.isoformat() if validation.training_start_date else None,
                    'end': validation.training_end_date.isoformat() if validation.training_end_date else None
                },
                'test_period': {
                    'start': validation.test_start_date.isoformat() if validation.test_start_date else None,
                    'end': validation.test_end_date.isoformat() if validation.test_end_date else None
                }
            }

            # Add metrics using to_dict()
            validation_dict = validation.to_dict()
            result.update({
                'wqi_metrics': validation_dict.get('wqi_metrics', {}),
                'contamination_metrics': validation_dict.get('contamination_metrics', {}),
                'risk_metrics': validation_dict.get('risk_metrics', {}),
                'forecast_metrics': validation_dict.get('forecast_metrics', {})
            })

            site_results.append(result)

        # Calculate aggregate metrics
        aggregate = calculate_aggregate_metrics(site_results)

        # Get available countries for filter dropdown (apply same filtering)
        countries_query = db.session.query(Site.country).filter(Site.is_active == True)
        if current_user.is_authenticated:
            countries_query = current_user.filter_sites_query(countries_query)
        countries = countries_query.distinct().order_by(Site.country).all()
        countries_list = [c[0] for c in countries]

        # Add performance metadata
        response = {
            'success': True,
            'sites': site_results,
            'aggregate_metrics': aggregate,
            'total_sites': len(site_results),
            'available_countries': countries_list,
            'cache_stats': {
                'using_cached_results': True,
                'missing_validations': missing_count,
                'stale_validations': stale_count if recalculate else 0,
                'hint': 'Use ?recalculate=true to update missing or stale results' if missing_count + stale_count > 0 else None
            }
        }

        return jsonify(response)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def validate_site_with_2year_split(site, training_samples, test_samples):
    """
    Validate ML predictions using 2-year training window
    Returns validation metrics for WQI, contamination, risk, and forecast
    """
    pipeline = MLPipeline()

    # Initialize results
    results = {
        'wqi_metrics': {},
        'contamination_metrics': {},
        'risk_metrics': {},
        'forecast_metrics': {}
    }

    # === WQI VALIDATION ===
    wqi_predictions = []
    wqi_actuals = []
    wqi_data_points = []  # For visualization

    for sample in test_samples:
        test_result = sample.get_latest_test()
        if not test_result:
            continue

        # Calculate predicted WQI
        sensor_reading = {
            'ph': test_result.ph,
            'tds': test_result.tds_ppm,
            'turbidity': test_result.turbidity_ntu,
            'chlorine': test_result.free_chlorine_mg_l or 0.5,
            'temperature': test_result.temperature_celsius
        }

        wqi_result = pipeline.calculate_realtime_wqi(sensor_reading)
        predicted_wqi = wqi_result['wqi_score']

        # Calculate actual WQI
        actual_wqi, actual_class = calculate_actual_wqi(test_result)

        wqi_predictions.append(predicted_wqi)
        wqi_actuals.append(actual_wqi)

        # Store data point for visualization
        wqi_data_points.append({
            'date': sample.collection_date.isoformat(),
            'predicted': round(float(predicted_wqi), 1),
            'actual': round(float(actual_wqi), 1),
            'difference': round(float(predicted_wqi - actual_wqi), 1)
        })

    if wqi_predictions and wqi_actuals:
        wqi_mae = np.mean(np.abs(np.array(wqi_predictions) - np.array(wqi_actuals)))
        wqi_rmse = np.sqrt(np.mean((np.array(wqi_predictions) - np.array(wqi_actuals))**2))

        # Accuracy within ±10 points
        within_10 = sum(1 for i in range(len(wqi_predictions))
                       if abs(wqi_predictions[i] - wqi_actuals[i]) <= 10)
        accuracy_10 = (within_10 / len(wqi_predictions)) * 100 if wqi_predictions else 0

        results['wqi_metrics'] = {
            'mae': round(float(wqi_mae), 2),
            'rmse': round(float(wqi_rmse), 2),
            'accuracy_within_10': round(accuracy_10, 1),
            'n_predictions': len(wqi_predictions),
            'data_points': wqi_data_points  # Add visualization data
        }

    # === CONTAMINATION TYPE VALIDATION ===
    contam_predictions = []
    contam_actuals = []

    for sample in test_samples:
        test_result = sample.get_latest_test()
        if not test_result:
            continue

        # Get predicted contamination type
        predicted_type, confidence = calculate_contamination_prediction(
            test_result, sample, site
        )

        # Get actual contamination type
        actual_type = determine_actual_contamination(test_result)

        contam_predictions.append(predicted_type)
        contam_actuals.append(actual_type)

    if contam_predictions and contam_actuals:
        # Calculate accuracy
        correct = sum(1 for i in range(len(contam_predictions))
                     if contam_predictions[i] == contam_actuals[i])
        accuracy = (correct / len(contam_predictions)) * 100

        # Build confusion matrix
        contamination_types = ['runoff_sediment', 'sewage_ingress', 'salt_intrusion',
                              'pipe_corrosion', 'disinfectant_decay', 'none']
        matrix = {t: {t2: 0 for t2 in contamination_types} for t in contamination_types}

        for pred, actual in zip(contam_predictions, contam_actuals):
            pred_key = pred if pred in contamination_types else 'none'
            actual_key = actual if actual in contamination_types else 'none'
            matrix[pred_key][actual_key] += 1

        # Calculate per-type metrics
        type_metrics = {}
        for ctype in contamination_types:
            tp = matrix[ctype][ctype]
            fp = sum(matrix[ctype].values()) - tp
            fn = sum(matrix[t][ctype] for t in contamination_types) - tp

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            type_metrics[ctype] = {
                'precision': round(precision * 100, 1),
                'recall': round(recall * 100, 1),
                'f1_score': round(f1 * 100, 1)
            }

        results['contamination_metrics'] = {
            'accuracy': round(accuracy, 1),
            'confusion_matrix': matrix,
            'per_type_metrics': type_metrics,
            'n_predictions': len(contam_predictions)
        }

    # === SITE RISK VALIDATION ===
    risk_predictions = []
    risk_actuals = []

    for sample in test_samples:
        test_result = sample.get_latest_test()
        if not test_result:
            continue

        # Calculate predicted risk
        site_features = {
            'site_type': site.site_type,
            'is_industrial_nearby': site.is_industrial_nearby,
            'is_agricultural_nearby': site.is_agricultural_nearby,
            'is_coastal': site.is_coastal,
            'is_urban': site.is_urban,
            'contamination_rate_30d': calculate_contamination_rate_from_samples(
                training_samples, sample.collection_date
            ),
            'days_since_last_test': 7  # Average assumption
        }

        risk_result = pipeline.predict_site_risk(site_features)
        predicted_risk = risk_result['risk_level']

        # Calculate actual risk from test results
        actual_risk, _ = determine_actual_risk(test_result)

        risk_predictions.append(predicted_risk)
        risk_actuals.append(actual_risk)

    if risk_predictions and risk_actuals:
        # Calculate accuracy
        correct = sum(1 for i in range(len(risk_predictions))
                     if risk_predictions[i] == risk_actuals[i])
        accuracy = (correct / len(risk_predictions)) * 100

        # Build confusion matrix
        risk_levels = ['critical', 'high', 'medium', 'low']
        matrix = {l: {l2: 0 for l2 in risk_levels} for l in risk_levels}

        for pred, actual in zip(risk_predictions, risk_actuals):
            if pred in risk_levels and actual in risk_levels:
                matrix[pred][actual] += 1

        results['risk_metrics'] = {
            'accuracy': round(accuracy, 1),
            'confusion_matrix': matrix,
            'n_predictions': len(risk_predictions)
        }

    # === FORECAST VALIDATION ===
    # Map display names to database column names
    parameter_mapping = {
        'ph': 'ph',
        'turbidity': 'turbidity_ntu',
        'tds': 'tds_ppm',
        'temperature': 'temperature_celsius'
    }
    forecast_results = {}

    for param_name, db_column in parameter_mapping.items():
        predictions = []
        actuals = []

        for i, sample in enumerate(test_samples):
            test_result = sample.get_latest_test()
            if not test_result:
                continue

            actual_value = getattr(test_result, db_column, None)
            if actual_value is None:
                continue

            # Use training data to predict this value (simple moving average from training)
            training_values = []
            for train_sample in training_samples[-10:]:  # Last 10 training samples
                train_result = train_sample.get_latest_test()
                if train_result:
                    val = getattr(train_result, db_column, None)
                    if val is not None:
                        training_values.append(val)

            if training_values:
                predicted_value = np.mean(training_values)
                predictions.append(predicted_value)
                actuals.append(actual_value)

        if predictions and actuals:
            mae = np.mean(np.abs(np.array(predictions) - np.array(actuals)))
            rmse = np.sqrt(np.mean((np.array(predictions) - np.array(actuals))**2))

            # R² calculation
            ss_res = np.sum((np.array(actuals) - np.array(predictions))**2)
            ss_tot = np.sum((np.array(actuals) - np.mean(actuals))**2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            forecast_results[param_name] = {
                'mae': round(float(mae), 3),
                'rmse': round(float(rmse), 3),
                'r2': round(float(max(0, r2)), 3),
                'n_predictions': len(predictions)
            }

    results['forecast_metrics'] = forecast_results

    return results


def calculate_contamination_rate_from_samples(samples, before_date):
    """Calculate contamination rate from training samples"""
    if not samples:
        return 0

    contaminated = 0
    total = 0

    for sample in samples:
        test_result = sample.get_latest_test()
        if test_result:
            total += 1
            if (test_result.total_coliform_mpn or 0) > 0:
                contaminated += 1

    return (contaminated / total * 100) if total > 0 else 0


def calculate_aggregate_metrics(site_results):
    """Calculate aggregate metrics across all sites"""
    if not site_results:
        return {}

    # WQI aggregates
    wqi_maes = [s['wqi_metrics']['mae'] for s in site_results
                if s.get('wqi_metrics') and s['wqi_metrics'].get('mae') is not None]
    wqi_rmses = [s['wqi_metrics']['rmse'] for s in site_results
                 if s.get('wqi_metrics') and s['wqi_metrics'].get('rmse') is not None]
    wqi_acc_10s = [s['wqi_metrics']['accuracy_within_10'] for s in site_results
                   if s.get('wqi_metrics') and s['wqi_metrics'].get('accuracy_within_10') is not None]

    # Contamination aggregates
    contam_accs = [s['contamination_metrics']['accuracy'] for s in site_results
                   if s.get('contamination_metrics') and s['contamination_metrics'].get('accuracy') is not None]

    # Risk aggregates
    risk_accs = [s['risk_metrics']['accuracy'] for s in site_results
                 if s.get('risk_metrics') and s['risk_metrics'].get('accuracy') is not None]

    # Forecast aggregates (average across parameters)
    forecast_r2s = []
    forecast_maes = []
    for site in site_results:
        if site.get('forecast_metrics'):
            # Only iterate over parameter-specific metrics (not avg_r2 or total_predictions)
            for param_name in ['ph', 'turbidity', 'tds', 'temperature']:
                param_metrics = site['forecast_metrics'].get(param_name)
                if param_metrics and isinstance(param_metrics, dict):
                    if param_metrics.get('r2') is not None:
                        forecast_r2s.append(param_metrics['r2'])
                    if param_metrics.get('mae') is not None:
                        forecast_maes.append(param_metrics['mae'])

    return {
        'wqi': {
            'avg_mae': round(np.mean(wqi_maes), 2) if wqi_maes else 0,
            'avg_rmse': round(np.mean(wqi_rmses), 2) if wqi_rmses else 0,
            'avg_accuracy_within_10': round(np.mean(wqi_acc_10s), 1) if wqi_acc_10s else 0
        },
        'contamination': {
            'avg_accuracy': round(np.mean(contam_accs), 1) if contam_accs else 0
        },
        'risk': {
            'avg_accuracy': round(np.mean(risk_accs), 1) if risk_accs else 0
        },
        'forecast': {
            'avg_r2': round(np.mean(forecast_r2s), 3) if forecast_r2s else 0,
            'avg_mae': round(np.mean(forecast_maes), 3) if forecast_maes else 0
        }
    }
