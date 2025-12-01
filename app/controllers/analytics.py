"""
Analytics Controller
Provides trend analysis, forecasting, and advanced analytics dashboard
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app import db
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.services.trend_analyzer import TrendAnalyzer


# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


# ============================================================================
# ANALYTICS DASHBOARD
# ============================================================================

@analytics_bp.route('/')
@login_required
def dashboard():
    """Main analytics dashboard showing system-wide trends and alerts"""

    # Get all sites with recent data
    cutoff_date = datetime.now() - timedelta(days=90)
    sites_with_data = db.session.query(Site).join(WaterSample).filter(
        WaterSample.collection_date >= cutoff_date
    ).distinct().all()

    # Analyze each site to get warning scores
    analyzer = TrendAnalyzer()
    site_warnings = []

    for site in sites_with_data[:20]:  # Limit to 20 for dashboard
        try:
            trend_result = analyzer.analyze_site_trends(site.id, days=90)
            if 'error' not in trend_result:
                site_warnings.append({
                    'site_id': site.id,
                    'site_name': site.site_name,
                    'site_code': site.site_code,
                    'warning_score': trend_result['warning_score'],
                    'warning_level': trend_result['warning_level'],
                    'overall_trend': trend_result['overall_trend'],
                    'samples_analyzed': trend_result['samples_analyzed']
                })
        except Exception as e:
            print(f"Error analyzing site {site.id}: {str(e)}")
            continue

    # Sort by warning score (highest first)
    site_warnings.sort(key=lambda x: x['warning_score'], reverse=True)

    # Get top alerts (critical and high)
    critical_sites = [s for s in site_warnings if s['warning_level'] == 'critical']
    high_warning_sites = [s for s in site_warnings if s['warning_level'] == 'high']

    # Calculate summary statistics
    summary_stats = {
        'total_sites_analyzed': len(site_warnings),
        'critical_sites': len(critical_sites),
        'high_warning_sites': len(high_warning_sites),
        'improving_sites': len([s for s in site_warnings if s['overall_trend'] == 'improving']),
        'declining_sites': len([s for s in site_warnings if s['overall_trend'] == 'declining']),
        'stable_sites': len([s for s in site_warnings if s['overall_trend'] == 'stable'])
    }

    return render_template('analytics/dashboard.html',
                         site_warnings=site_warnings[:15],  # Top 15 for display
                         critical_sites=critical_sites,
                         high_warning_sites=high_warning_sites,
                         summary_stats=summary_stats)


@analytics_bp.route('/sites')
@login_required
def sites():
    """Display all sites for analysis selection"""

    # Get all sites with sample counts
    sites_list = []
    all_sites = Site.query.order_by(Site.site_name).all()

    for site in all_sites:
        # Count samples from last 365 days
        cutoff_date = datetime.now() - timedelta(days=365)
        sample_count = WaterSample.query.filter(
            WaterSample.site_id == site.id,
            WaterSample.collection_date >= cutoff_date
        ).count()

        sites_list.append({
            'id': site.id,
            'site_name': site.site_name,
            'site_code': site.site_code,
            'district': site.district,
            'state': site.state,
            'sample_count': sample_count
        })

    return render_template('analytics/sites.html', sites=sites_list)


@analytics_bp.route('/site/<int:site_id>')
@login_required
def site_trends(site_id):
    """Detailed trend analysis for a specific site"""
    site = Site.query.get_or_404(site_id)

    # Get analysis period from query params (default 365 days)
    days = request.args.get('days', 365, type=int)

    # Analyze trends
    analyzer = TrendAnalyzer()
    trend_result = analyzer.analyze_site_trends(site_id, days=days)

    if 'error' in trend_result:
        flash(trend_result.get('message', 'Unable to analyze trends for this site'), 'warning')
        return redirect(url_for('analytics.dashboard'))

    # Prepare data for charts
    chart_data = _prepare_chart_data(trend_result)

    return render_template('analytics/site_trends.html',
                         site=site,
                         trend_result=trend_result,
                         chart_data=chart_data,
                         analysis_days=days)


@analytics_bp.route('/site/<int:site_id>/forecast')
@login_required
def site_forecast(site_id):
    """Forecast future water quality trends"""
    site = Site.query.get_or_404(site_id)

    # Get parameters and forecast period
    parameter = request.args.get('parameter', 'turbidity_ntu')
    days_ahead = request.args.get('days', 90, type=int)

    # Get forecast
    analyzer = TrendAnalyzer()
    forecast_result = analyzer.get_parameter_forecast(site_id, parameter, days_ahead)

    if not forecast_result:
        flash('Insufficient data for forecasting this parameter', 'warning')
        return redirect(url_for('analytics.site_trends', site_id=site_id))

    return render_template('analytics/forecast.html',
                         site=site,
                         forecast_result=forecast_result,
                         parameter=parameter,
                         days_ahead=days_ahead)


@analytics_bp.route('/alerts')
@login_required
def alerts():
    """View all sites with warning alerts"""

    # Get warning level filter
    level_filter = request.args.get('level', 'all')

    # Analyze all sites
    cutoff_date = datetime.now() - timedelta(days=90)
    sites_with_data = db.session.query(Site).join(WaterSample).filter(
        WaterSample.collection_date >= cutoff_date
    ).distinct().all()

    analyzer = TrendAnalyzer()
    alerts_list = []

    for site in sites_with_data:
        try:
            trend_result = analyzer.analyze_site_trends(site.id, days=90)
            if 'error' not in trend_result:
                warning_level = trend_result['warning_level']

                # Apply filter
                if level_filter == 'all' or warning_level == level_filter:
                    alerts_list.append({
                        'site_id': site.id,
                        'site_name': site.site_name,
                        'site_code': site.site_code,
                        'warning_score': trend_result['warning_score'],
                        'warning_level': warning_level,
                        'overall_trend': trend_result['overall_trend'],
                        'recommendations': trend_result['recommendations'],
                        'change_points': len(trend_result.get('change_points', []))
                    })
        except Exception as e:
            continue

    # Sort by warning score
    alerts_list.sort(key=lambda x: x['warning_score'], reverse=True)

    return render_template('analytics/alerts.html',
                         alerts=alerts_list,
                         level_filter=level_filter)


# ============================================================================
# COMPARISON & REPORTS
# ============================================================================

@analytics_bp.route('/compare')
@login_required
def compare_sites():
    """Compare trends across multiple sites"""

    # Get site IDs from query params
    site_ids_str = request.args.get('sites', '')
    if not site_ids_str:
        # Show site selection page
        all_sites = Site.query.order_by(Site.site_name).all()
        return render_template('analytics/select_comparison.html',
                             sites=all_sites)

    # Parse site IDs
    try:
        site_ids = [int(id) for id in site_ids_str.split(',')]
    except ValueError:
        flash('Invalid site IDs provided', 'error')
        return redirect(url_for('analytics.compare_sites'))

    if len(site_ids) < 2:
        flash('Please select at least 2 sites to compare', 'warning')
        return redirect(url_for('analytics.compare_sites'))

    if len(site_ids) > 5:
        flash('Maximum 5 sites can be compared at once', 'warning')
        site_ids = site_ids[:5]

    # Analyze each site
    analyzer = TrendAnalyzer()
    comparison_data = []

    for site_id in site_ids:
        site = Site.query.get(site_id)
        if not site:
            continue

        try:
            trend_result = analyzer.analyze_site_trends(site_id, days=180)
            if 'error' not in trend_result:
                comparison_data.append({
                    'site': site,
                    'trends': trend_result
                })
        except Exception as e:
            flash(f'Error analyzing {site.site_name}: {str(e)}', 'error')

    if not comparison_data:
        flash('No valid data for comparison', 'error')
        return redirect(url_for('analytics.compare_sites'))

    return render_template('analytics/compare.html',
                         comparison_data=comparison_data)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@analytics_bp.route('/api/site/<int:site_id>/trends', methods=['GET'])
@login_required
def api_site_trends(site_id):
    """API: Get trend analysis for a site (JSON)"""

    days = request.args.get('days', 365, type=int)

    analyzer = TrendAnalyzer()
    trend_result = analyzer.analyze_site_trends(site_id, days=days)

    return jsonify(trend_result)


@analytics_bp.route('/api/site/<int:site_id>/forecast', methods=['GET'])
@login_required
def api_forecast(site_id):
    """API: Get forecast for a parameter (JSON)"""

    parameter = request.args.get('parameter', 'turbidity_ntu')
    days_ahead = request.args.get('days', 90, type=int)

    analyzer = TrendAnalyzer()
    forecast_result = analyzer.get_parameter_forecast(site_id, parameter, days_ahead)

    if not forecast_result:
        return jsonify({'error': 'Insufficient data for forecast'}), 404

    return jsonify(forecast_result)


@analytics_bp.route('/api/alerts', methods=['GET'])
@login_required
def api_alerts():
    """API: Get all site alerts (JSON)"""

    level = request.args.get('level', 'all')

    cutoff_date = datetime.now() - timedelta(days=90)
    sites_with_data = db.session.query(Site).join(WaterSample).filter(
        WaterSample.collection_date >= cutoff_date
    ).distinct().all()

    analyzer = TrendAnalyzer()
    alerts_list = []

    for site in sites_with_data:
        try:
            trend_result = analyzer.analyze_site_trends(site.id, days=90)
            if 'error' not in trend_result:
                warning_level = trend_result['warning_level']

                if level == 'all' or warning_level == level:
                    alerts_list.append({
                        'site_id': site.id,
                        'site_code': site.site_code,
                        'site_name': site.site_name,
                        'warning_score': trend_result['warning_score'],
                        'warning_level': warning_level,
                        'overall_trend': trend_result['overall_trend'],
                        'recommendations': trend_result['recommendations']
                    })
        except Exception:
            continue

    return jsonify({
        'total_alerts': len(alerts_list),
        'alerts': sorted(alerts_list, key=lambda x: x['warning_score'], reverse=True)
    })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _prepare_chart_data(trend_result):
    """Prepare data for Plotly charts"""

    chart_data = {
        'parameters': [],
        'trends': {},
        'compliance': {}
    }

    parameter_trends = trend_result.get('parameter_trends', {})

    for param, data in parameter_trends.items():
        chart_data['parameters'].append(param)

        # Store trend information
        chart_data['trends'][param] = {
            'trend': data['trend'],
            'monthly_change': data['monthly_change_pct'],
            'current_value': data['current_value'],
            'mean_value': data['mean_value'],
            'r_squared': data['r_squared']
        }

        # Store compliance status
        chart_data['compliance'][param] = data['compliance']['status']

    # Convert to JSON for template
    return json.dumps(chart_data)
