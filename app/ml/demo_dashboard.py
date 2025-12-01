#!/usr/bin/env python3
"""
Interactive ML Demo Dashboard for Amrit Sarovar Water Quality Optimization
Web interface to showcase all trained ML models and cost savings
"""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'amrit-sarovar-ml-demo-2025'

# Global storage for loaded models and data
MODELS = {}
DATA = {}
REPORTS = {}


def load_all_assets():
    """Load ML models, data, and reports on startup"""
    global MODELS, DATA, REPORTS

    print("Loading ML models and data...")

    try:
        # Load trained models
        MODELS['site_risk_classifier'] = joblib.load('app/ml/trained_models/site_risk_classifier.pkl')
        MODELS['contamination_classifier'] = joblib.load('app/ml/trained_models/contamination_classifier.pkl')
        MODELS['quality_forecaster'] = joblib.load('app/ml/trained_models/quality_forecaster_ph.pkl')

        # Load testing schedule
        MODELS['testing_schedule'] = pd.read_csv('app/ml/trained_models/testing_schedule.csv')

        # Load demo data
        DATA['sites'] = pd.read_csv('demo_data/amrit_sarovar_sites.csv')
        DATA['samples'] = pd.read_csv('demo_data/water_samples.csv')
        DATA['test_results'] = pd.read_csv('demo_data/test_results.csv')
        DATA['analyses'] = pd.read_csv('demo_data/analyses.csv')

        # Load reports
        with open('reports/ml_model_report.json', 'r') as f:
            REPORTS['ml_models'] = json.load(f)

        with open('reports/cost_analysis_report_full.json', 'r') as f:
            REPORTS['cost_full'] = json.load(f)

        with open('reports/cost_analysis_report_demo.json', 'r') as f:
            REPORTS['cost_demo'] = json.load(f)

        print("✓ All assets loaded successfully!")
        return True

    except Exception as e:
        print(f"✗ Error loading assets: {e}")
        return False


@app.route('/')
def index():
    """Main dashboard page"""

    # Calculate summary statistics
    total_sites = len(DATA['sites'])
    total_samples = len(DATA['samples'])

    # Get model metrics
    site_risk_acc = REPORTS['ml_models']['metrics']['site_risk_classifier']['accuracy']
    contam_acc = REPORTS['ml_models']['metrics']['contamination_classifier']['accuracy']
    forecast_rmse = REPORTS['ml_models']['metrics']['quality_forecaster_ph']['rmse']

    # Get cost savings
    baseline_cost = REPORTS['cost_full']['baseline']['total_annual_cost']
    ml_cost = REPORTS['cost_full']['ml_optimized']['total_annual_cost']
    savings_percent = REPORTS['cost_full']['savings']['savings_percentage']

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

    return render_template('dashboard.html', stats=summary_stats)


@app.route('/site-risk-predictor')
def site_risk_predictor():
    """Site risk prediction interface"""

    # Get sample site for demo
    sample_site = DATA['sites'].iloc[0].to_dict()

    # Get model metrics
    metrics = REPORTS['ml_models']['metrics']['site_risk_classifier']

    return render_template('site_risk.html',
                         sample_site=sample_site,
                         metrics=metrics)


@app.route('/api/predict-site-risk', methods=['POST'])
def predict_site_risk():
    """API endpoint for site risk prediction"""

    try:
        # Get site code from request
        site_code = request.json.get('site_code')

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
            'confidence': 'High'  # Could add probability scores from model
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/contamination-classifier')
def contamination_classifier():
    """Contamination classification interface"""

    # Get sample test result
    sample_test = DATA['test_results'].iloc[0].to_dict()

    # Get model metrics
    metrics = REPORTS['ml_models']['metrics']['contamination_classifier']

    return render_template('contamination.html',
                         sample_test=sample_test,
                         metrics=metrics)


@app.route('/api/classify-contamination', methods=['POST'])
def classify_contamination():
    """API endpoint for contamination classification"""

    try:
        sample_id = request.json.get('sample_id')

        # Find analysis for sample
        analysis = DATA['analyses'][DATA['analyses']['sample_id'] == sample_id]

        if len(analysis) == 0:
            return jsonify({'error': 'Sample not found'}), 404

        analysis_info = analysis.iloc[0]

        result = {
            'sample_id': sample_id,
            'primary_contamination': analysis_info['primary_contamination_type'],
            'overall_quality_score': float(analysis_info['overall_quality_score']),
            'who_compliant': bool(analysis_info['who_compliant']),
            'follow_up_required': bool(analysis_info['follow_up_required']),
            'contamination_scores': {
                'runoff_sediment': float(analysis_info['runoff_sediment_score']),
                'sewage_ingress': float(analysis_info['sewage_ingress_score']),
                'salt_intrusion': float(analysis_info['salt_intrusion_score']),
                'pipe_corrosion': float(analysis_info['pipe_corrosion_score']),
                'disinfectant_decay': float(analysis_info['disinfectant_decay_score'])
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cost-analysis')
def cost_analysis():
    """Cost analysis and ROI visualization"""

    # Create cost comparison chart
    cost_chart = create_cost_comparison_chart()

    # Create savings breakdown chart
    savings_chart = create_savings_breakdown_chart()

    # Get detailed cost metrics
    cost_metrics = {
        'baseline': REPORTS['cost_full']['baseline'],
        'ml_optimized': REPORTS['cost_full']['ml_optimized'],
        'savings': REPORTS['cost_full']['savings'],
        'roi': REPORTS['cost_full']['roi_analysis']
    }

    return render_template('cost_analysis.html',
                         cost_chart=cost_chart,
                         savings_chart=savings_chart,
                         metrics=cost_metrics)


def create_cost_comparison_chart():
    """Create interactive cost comparison chart"""

    baseline_cost = REPORTS['cost_full']['baseline']['total_annual_cost'] / 10000000
    ml_cost = REPORTS['cost_full']['ml_optimized']['total_annual_cost'] / 10000000

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


@app.route('/model-performance')
def model_performance():
    """Model performance metrics and visualizations"""

    # Create feature importance chart
    feature_chart = create_feature_importance_chart()

    # Create confusion matrix
    confusion_chart = create_confusion_matrix_chart()

    metrics = REPORTS['ml_models']['metrics']

    return render_template('model_performance.html',
                         feature_chart=feature_chart,
                         confusion_chart=confusion_chart,
                         metrics=metrics)


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


@app.route('/data-explorer')
def data_explorer():
    """Interactive data exploration interface"""

    # Sample sites for display
    sample_sites = DATA['sites'].head(10).to_dict('records')

    # Summary statistics
    stats = {
        'total_sites': len(DATA['sites']),
        'total_samples': len(DATA['samples']),
        'states_covered': DATA['sites']['state'].nunique(),
        'who_compliant': int(DATA['analyses']['who_compliant'].sum()),
        'non_compliant': int((~DATA['analyses']['who_compliant']).sum()),
        'urgent_priority': int((DATA['analyses']['overall_quality_score'] > 0.7).sum())
    }

    return render_template('data_explorer.html',
                         sample_sites=sample_sites,
                         stats=stats)


@app.route('/api/site-details/<site_code>')
def site_details(site_code):
    """Get detailed information for a specific site"""

    try:
        # Get site info
        site = DATA['sites'][DATA['sites']['site_code'] == site_code]
        if len(site) == 0:
            return jsonify({'error': 'Site not found'}), 404

        site_info = site.iloc[0].to_dict()

        # Get samples for this site
        samples = DATA['samples'][DATA['samples']['site_code'] == site_code]
        sample_ids = samples['sample_id'].tolist()

        # Get test results
        test_results = DATA['test_results'][
            DATA['test_results']['sample_id'].isin(sample_ids)
        ]

        # Get analyses
        analyses = DATA['analyses'][
            DATA['analyses']['sample_id'].isin(sample_ids)
        ]

        # Calculate statistics
        result = {
            'site_info': site_info,
            'total_samples': len(samples),
            'avg_quality_score': float(analyses['overall_quality_score'].mean()),
            'who_compliant_rate': float(analyses['who_compliant'].mean()),
            'primary_contaminations': analyses['primary_contamination_type'].value_counts().to_dict(),
            'recent_samples': samples.tail(5).to_dict('records')
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/about')
def about():
    """About page with project information"""

    info = {
        'project_name': 'Amrit Sarovar ML Cost Optimization',
        'generation_date': REPORTS['ml_models']['generation_date'],
        'models_trained': REPORTS['ml_models']['models_trained'],
        'total_sites_target': 68000,
        'demo_sites': len(DATA['sites']),
        'mission': 'Mission Amrit Sarovar - Water Quality Monitoring Optimization'
    }

    return render_template('about.html', info=info)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("AMRIT SAROVAR ML DEMO DASHBOARD")
    print("="*70 + "\n")

    # Load all assets
    if not load_all_assets():
        print("Failed to load assets. Exiting.")
        sys.exit(1)

    print("\nStarting Flask server...")
    print("Dashboard will be available at: http://127.0.0.1:5001")
    print("\nPress Ctrl+C to stop the server\n")

    app.run(host='0.0.0.0', port=5001, debug=True)
