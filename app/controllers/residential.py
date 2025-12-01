"""
Residential Monitoring Controller - Homes and apartment water monitoring
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.residential_site import (
    ResidentialSite,
    ResidentialMeasurement,
    ResidentialAlert,
    ResidentialSubscription
)
from app.models.user import User
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

residential_bp = Blueprint('residential', __name__, url_prefix='/residential')


# ============= WEB VIEWS (Frontend) =============

@residential_bp.route('/dashboard')
@login_required
def dashboard():
    """Main residential dashboard for homeowners"""

    # Get user's residential sites
    my_sites = ResidentialSite.query.filter_by(
        owner_user_id=current_user.id,
        is_active=True
    ).all()

    if not my_sites:
        # No sites registered - show registration prompt
        return render_template('residential/no_sites.html')

    # Get statistics across all user's sites
    total_measurements = 0
    active_alerts_count = 0
    avg_water_quality = []

    for site in my_sites:
        total_measurements += ResidentialMeasurement.query.filter_by(
            site_id=site.id
        ).count()

        active_alerts_count += ResidentialAlert.query.filter_by(
            site_id=site.id,
            resolved=False
        ).count()

        # Get recent measurements for quality average
        recent = ResidentialMeasurement.query.filter_by(
            site_id=site.id
        ).order_by(ResidentialMeasurement.measurement_datetime.desc()).limit(100).all()

        if recent:
            valid_wqi = [m.water_quality_index for m in recent if m.water_quality_index is not None]
            if valid_wqi:
                avg_water_quality.extend(valid_wqi)

    # Calculate overall statistics
    overall_wqi = round(sum(avg_water_quality) / len(avg_water_quality), 1) if avg_water_quality else None
    safe_percentage = round(sum(1 for wqi in avg_water_quality if wqi >= 70) / len(avg_water_quality) * 100, 1) if avg_water_quality else None

    # Get active subscriptions
    active_subscriptions = ResidentialSubscription.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).all()

    return render_template('residential/dashboard.html',
                          my_sites=my_sites,
                          total_measurements=total_measurements,
                          active_alerts_count=active_alerts_count,
                          overall_wqi=overall_wqi,
                          safe_percentage=safe_percentage,
                          active_subscriptions=active_subscriptions)


@residential_bp.route('/site/<int:site_id>')
@login_required
def site_detail(site_id):
    """Detailed view for a specific residential site"""

    site = ResidentialSite.query.get_or_404(site_id)

    # Check authorization
    if site.owner_user_id != current_user.id:
        flash('You do not have access to this site.', 'error')
        return redirect(url_for('residential.dashboard'))

    # Get recent measurements (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_measurements = ResidentialMeasurement.query.filter(
        ResidentialMeasurement.site_id == site_id,
        ResidentialMeasurement.measurement_datetime >= thirty_days_ago
    ).order_by(
        ResidentialMeasurement.measurement_datetime.desc()
    ).all()

    # Get active alerts
    active_alerts = ResidentialAlert.query.filter_by(
        site_id=site_id,
        resolved=False
    ).order_by(
        ResidentialAlert.alert_datetime.desc()
    ).all()

    # Calculate statistics
    if recent_measurements:
        valid_wqi = [m.water_quality_index for m in recent_measurements if m.water_quality_index is not None]
        avg_wqi = round(sum(valid_wqi) / len(valid_wqi), 1) if valid_wqi else None
        safe_count = sum(1 for m in recent_measurements if m.is_safe_to_drink)
        safe_percentage = round(safe_count / len(recent_measurements) * 100, 1)

        # Calculate parameter averages
        avg_ph = round(sum(m.ph_value for m in recent_measurements if m.ph_value) /
                       sum(1 for m in recent_measurements if m.ph_value), 2) if any(m.ph_value for m in recent_measurements) else None
        avg_tds = round(sum(m.tds_ppm for m in recent_measurements if m.tds_ppm) /
                        sum(1 for m in recent_measurements if m.tds_ppm), 1) if any(m.tds_ppm for m in recent_measurements) else None
        avg_turbidity = round(sum(m.turbidity_ntu for m in recent_measurements if m.turbidity_ntu) /
                              sum(1 for m in recent_measurements if m.turbidity_ntu), 2) if any(m.turbidity_ntu for m in recent_measurements) else None
    else:
        avg_wqi = None
        safe_percentage = None
        avg_ph = None
        avg_tds = None
        avg_turbidity = None

    # Get subscription info
    subscription = ResidentialSubscription.query.filter_by(
        site_id=site_id,
        status='active'
    ).first()

    return render_template('residential/site_detail.html',
                          site=site,
                          recent_measurements=recent_measurements[:20],  # Show latest 20
                          active_alerts=active_alerts,
                          avg_wqi=avg_wqi,
                          safe_percentage=safe_percentage,
                          avg_ph=avg_ph,
                          avg_tds=avg_tds,
                          avg_turbidity=avg_turbidity,
                          subscription=subscription)


@residential_bp.route('/alerts')
@login_required
def alerts():
    """View all alerts across user's sites"""

    # Get all user's sites
    site_ids = [site.id for site in ResidentialSite.query.filter_by(
        owner_user_id=current_user.id
    ).all()]

    # Get all alerts
    all_alerts = ResidentialAlert.query.filter(
        ResidentialAlert.site_id.in_(site_ids)
    ).order_by(
        ResidentialAlert.alert_datetime.desc()
    ).all()

    # Separate by status
    active_alerts = [a for a in all_alerts if not a.resolved]
    resolved_alerts = [a for a in all_alerts if a.resolved]

    return render_template('residential/alerts.html',
                          active_alerts=active_alerts,
                          resolved_alerts=resolved_alerts)


@residential_bp.route('/alert/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""

    alert = ResidentialAlert.query.get_or_404(alert_id)

    # Check authorization
    site = ResidentialSite.query.get(alert.site_id)
    if site.owner_user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by_user_id = current_user.id

    db.session.commit()

    flash('Alert acknowledged successfully.', 'success')
    return redirect(url_for('residential.alerts'))


@residential_bp.route('/alert/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Mark an alert as resolved"""

    alert = ResidentialAlert.query.get_or_404(alert_id)

    # Check authorization
    site = ResidentialSite.query.get(alert.site_id)
    if site.owner_user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolution_notes = request.form.get('resolution_notes', '')

    db.session.commit()

    flash('Alert resolved successfully.', 'success')
    return redirect(url_for('residential.alerts'))


# ============= API ENDPOINTS (Backend) =============

@residential_bp.route('/api/upload', methods=['POST'])
def api_upload_measurement():
    """
    API endpoint for residential sensors to upload measurements

    POST /residential/api/upload
    {
        "device_id": "WFLOW-HOME-12345",
        "timestamp": "2025-11-17T10:30:00",
        "ph_value": 7.2,
        "tds_ppm": 180,
        "temperature_celsius": 24.5,
        "turbidity_ntu": 0.8,
        "conductivity_us_cm": 350,
        "free_chlorine_mg_l": 0.4,
        "ro_inlet_tds": 450,
        "ro_outlet_tds": 50
    }
    """
    data = request.get_json()

    if not data or 'device_id' not in data:
        return jsonify({'error': 'device_id is required'}), 400

    # Validate device
    site = ResidentialSite.query.filter_by(
        device_id=data['device_id'],
        is_active=True
    ).first()

    if not site:
        return jsonify({'error': 'Invalid or inactive device_id'}), 401

    # Create measurement
    measurement = ResidentialMeasurement(
        site_id=site.id,
        measurement_datetime=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.utcnow(),
        measurement_type=data.get('measurement_type', 'continuous'),
        ph_value=data.get('ph_value'),
        tds_ppm=data.get('tds_ppm'),
        temperature_celsius=data.get('temperature_celsius'),
        turbidity_ntu=data.get('turbidity_ntu'),
        conductivity_us_cm=data.get('conductivity_us_cm'),
        free_chlorine_mg_l=data.get('free_chlorine_mg_l'),
        orp_mv=data.get('orp_mv'),
        flow_rate_lpm=data.get('flow_rate_lpm'),
        cumulative_flow_liters=data.get('cumulative_flow_liters'),
        daily_consumption_liters=data.get('daily_consumption_liters'),
        ro_inlet_tds=data.get('ro_inlet_tds'),
        ro_outlet_tds=data.get('ro_outlet_tds'),
        device_battery_percent=data.get('device_battery_percent'),
        device_signal_strength=data.get('device_signal_strength'),
        uploaded_at=datetime.utcnow()
    )

    # Calculate RO rejection rate if inlet and outlet available
    if measurement.ro_inlet_tds and measurement.ro_outlet_tds and measurement.ro_inlet_tds > 0:
        measurement.ro_rejection_rate_percent = round(
            (measurement.ro_inlet_tds - measurement.ro_outlet_tds) / measurement.ro_inlet_tds * 100,
            1
        )
        # Estimate membrane health (should be >90% for good membrane)
        measurement.ro_membrane_health_percent = min(100, max(0, measurement.ro_rejection_rate_percent))

    # Calculate water quality index
    measurement.calculate_water_quality_index()

    # Check for anomalies and create alerts
    alerts_created = []

    # Alert: Unsafe water
    if measurement.compliance_status == 'unsafe':
        alert = ResidentialAlert(
            site_id=site.id,
            measurement_id=measurement.id,
            alert_type='water_unsafe',
            alert_severity='critical',
            alert_title='⚠️ Unsafe Drinking Water Detected',
            alert_message=f'Water quality index: {measurement.water_quality_index}/100. Water is not safe to drink.',
            trigger_parameter='water_quality_index',
            trigger_value=measurement.water_quality_index,
            threshold_value=70.0,
            recommended_action='Do not drink this water. Use bottled water. Contact service center for inspection.'
        )
        db.session.add(alert)
        alerts_created.append('water_unsafe')

    # Alert: High TDS
    if measurement.tds_ppm and measurement.tds_ppm > 500:
        alert = ResidentialAlert(
            site_id=site.id,
            measurement_id=measurement.id,
            alert_type='high_tds',
            alert_severity='warning' if measurement.tds_ppm < 1000 else 'critical',
            alert_title='High TDS Detected',
            alert_message=f'TDS level: {measurement.tds_ppm} ppm (limit: 500 ppm)',
            trigger_parameter='tds_ppm',
            trigger_value=measurement.tds_ppm,
            threshold_value=500.0,
            recommended_action='Water is hard. Consider RO system maintenance or replacement if TDS is very high.'
        )
        db.session.add(alert)
        alerts_created.append('high_tds')

    # Alert: Low chlorine (if municipal supply)
    if site.water_source == 'municipal' and measurement.free_chlorine_mg_l and measurement.free_chlorine_mg_l < 0.2:
        alert = ResidentialAlert(
            site_id=site.id,
            measurement_id=measurement.id,
            alert_type='low_chlorine',
            alert_severity='warning',
            alert_title='Low Chlorine Level',
            alert_message=f'Free chlorine: {measurement.free_chlorine_mg_l} mg/L (minimum: 0.2 mg/L)',
            trigger_parameter='free_chlorine_mg_l',
            trigger_value=measurement.free_chlorine_mg_l,
            threshold_value=0.2,
            recommended_action='Municipal supply may have insufficient disinfection. Boil water before drinking or use UV filter.'
        )
        db.session.add(alert)
        alerts_created.append('low_chlorine')

    # Alert: RO failure
    if measurement.ro_rejection_rate_percent and measurement.ro_rejection_rate_percent < 70:
        alert = ResidentialAlert(
            site_id=site.id,
            measurement_id=measurement.id,
            alert_type='ro_failure',
            alert_severity='critical',
            alert_title='RO System Failure',
            alert_message=f'RO rejection rate: {measurement.ro_rejection_rate_percent}% (should be >90%)',
            trigger_parameter='ro_rejection_rate_percent',
            trigger_value=measurement.ro_rejection_rate_percent,
            threshold_value=90.0,
            recommended_action='RO membrane needs replacement. Contact service technician immediately.',
            estimated_cost=2500.0  # Typical RO membrane cost in INR
        )
        db.session.add(alert)
        alerts_created.append('ro_failure')

    # Save measurement
    db.session.add(measurement)
    db.session.commit()

    # TODO: Send notifications based on site.alert_email_enabled, site.alert_sms_enabled, etc.

    return jsonify({
        'status': 'success',
        'measurement_id': measurement.id,
        'water_quality_index': measurement.water_quality_index,
        'is_safe_to_drink': measurement.is_safe_to_drink,
        'compliance_status': measurement.compliance_status,
        'ro_rejection_rate_percent': measurement.ro_rejection_rate_percent,
        'ro_membrane_health_percent': measurement.ro_membrane_health_percent,
        'alerts_created': alerts_created
    }), 201


@residential_bp.route('/api/site/<int:site_id>/statistics', methods=['GET'])
def api_get_site_statistics(site_id):
    """Get statistics for a residential site (API endpoint)"""

    site = ResidentialSite.query.get_or_404(site_id)

    # Get date range from query params (default: last 30 days)
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get measurements in date range
    measurements = ResidentialMeasurement.query.filter(
        ResidentialMeasurement.site_id == site_id,
        ResidentialMeasurement.measurement_datetime >= start_date
    ).order_by(
        ResidentialMeasurement.measurement_datetime.asc()
    ).all()

    if not measurements:
        return jsonify({
            'site_id': site_id,
            'period_days': days,
            'total_measurements': 0,
            'statistics': None
        })

    # Calculate statistics
    valid_wqi = [m.water_quality_index for m in measurements if m.water_quality_index is not None]
    safe_count = sum(1 for m in measurements if m.is_safe_to_drink)

    statistics = {
        'total_measurements': len(measurements),
        'safe_percentage': round(safe_count / len(measurements) * 100, 1) if measurements else 0,
        'avg_water_quality_index': round(sum(valid_wqi) / len(valid_wqi), 1) if valid_wqi else None,
        'min_water_quality_index': round(min(valid_wqi), 1) if valid_wqi else None,
        'max_water_quality_index': round(max(valid_wqi), 1) if valid_wqi else None,
        'avg_ph': round(sum(m.ph_value for m in measurements if m.ph_value) /
                        sum(1 for m in measurements if m.ph_value), 2) if any(m.ph_value for m in measurements) else None,
        'avg_tds': round(sum(m.tds_ppm for m in measurements if m.tds_ppm) /
                         sum(1 for m in measurements if m.tds_ppm), 1) if any(m.tds_ppm for m in measurements) else None,
        'avg_turbidity': round(sum(m.turbidity_ntu for m in measurements if m.turbidity_ntu) /
                               sum(1 for m in measurements if m.turbidity_ntu), 2) if any(m.turbidity_ntu for m in measurements) else None,
        'avg_chlorine': round(sum(m.free_chlorine_mg_l for m in measurements if m.free_chlorine_mg_l) /
                              sum(1 for m in measurements if m.free_chlorine_mg_l), 3) if any(m.free_chlorine_mg_l for m in measurements) else None,
    }

    # RO system statistics (if applicable)
    if site.has_ro_system:
        ro_measurements = [m for m in measurements if m.ro_rejection_rate_percent is not None]
        if ro_measurements:
            statistics['ro_avg_rejection_rate'] = round(
                sum(m.ro_rejection_rate_percent for m in ro_measurements) / len(ro_measurements), 1
            )
            statistics['ro_avg_membrane_health'] = round(
                sum(m.ro_membrane_health_percent for m in ro_measurements if m.ro_membrane_health_percent) /
                sum(1 for m in ro_measurements if m.ro_membrane_health_percent), 1
            ) if any(m.ro_membrane_health_percent for m in ro_measurements) else None

    return jsonify({
        'site_id': site_id,
        'site_type': site.site_type,
        'water_source': site.water_source,
        'has_ro_system': site.has_ro_system,
        'period_days': days,
        'statistics': statistics
    })


@residential_bp.route('/api/city/<city_name>/aggregated', methods=['GET'])
def api_get_city_aggregated_statistics(city_name):
    """
    Get aggregated residential water quality statistics for a city
    (For government users to monitor municipal supply issues)
    """

    # Get all residential sites in the city with data sharing consent
    sites = ResidentialSite.query.filter(
        ResidentialSite.city == city_name,
        ResidentialSite.data_sharing_consent == True,
        ResidentialSite.is_active == True
    ).all()

    if not sites:
        return jsonify({
            'city': city_name,
            'total_sites': 0,
            'message': 'No residential sites with data sharing consent in this city'
        })

    # Get measurements from last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    site_ids = [site.id for site in sites]

    measurements = ResidentialMeasurement.query.filter(
        ResidentialMeasurement.site_id.in_(site_ids),
        ResidentialMeasurement.measurement_datetime >= seven_days_ago
    ).all()

    if not measurements:
        return jsonify({
            'city': city_name,
            'total_sites': len(sites),
            'total_measurements': 0
        })

    # Aggregate statistics
    valid_wqi = [m.water_quality_index for m in measurements if m.water_quality_index is not None]
    unsafe_count = sum(1 for m in measurements if not m.is_safe_to_drink)

    # Group by water source
    municipal_measurements = [m for m in measurements if ResidentialSite.query.get(m.site_id).water_source == 'municipal']
    borewell_measurements = [m for m in measurements if ResidentialSite.query.get(m.site_id).water_source == 'borewell']

    return jsonify({
        'city': city_name,
        'total_sites': len(sites),
        'total_measurements': len(measurements),
        'period_days': 7,
        'aggregated_statistics': {
            'avg_water_quality_index': round(sum(valid_wqi) / len(valid_wqi), 1) if valid_wqi else None,
            'unsafe_percentage': round(unsafe_count / len(measurements) * 100, 1) if measurements else 0,
            'municipal_supply_avg_wqi': round(
                sum(m.water_quality_index for m in municipal_measurements if m.water_quality_index) /
                sum(1 for m in municipal_measurements if m.water_quality_index), 1
            ) if any(m.water_quality_index for m in municipal_measurements) else None,
            'borewell_avg_wqi': round(
                sum(m.water_quality_index for m in borewell_measurements if m.water_quality_index) /
                sum(1 for m in borewell_measurements if m.water_quality_index), 1
            ) if any(m.water_quality_index for m in borewell_measurements) else None,
        }
    })
