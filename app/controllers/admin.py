"""
Admin Controller - Data Import Management
Handles bulk data import for both Residential and Public monitoring
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.residential_site import (
    ResidentialSite, ResidentialMeasurement,
    ResidentialAlert, ResidentialSubscription
)
from app.models import WaterSample, TestResult, Analysis, Site
from datetime import datetime
import pandas as pd
import os
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'csv'}

# Get absolute paths relative to project root
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / 'import_templates'
SAMPLES_DIR = PROJECT_ROOT / 'demo_data'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You must be an administrator to access this page.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/data-import')
@login_required
@admin_required
def data_import():
    """Main data import page"""
    return render_template('admin/data_import.html')

# ==================== RESIDENTIAL IMPORT ROUTES ====================

@admin_bp.route('/import/residential/sites', methods=['POST'])
@login_required
@admin_required
def import_residential_sites():
    """Import residential sites from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin.data_import'))
    
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    site = ResidentialSite(
                        site_type=row['site_type'],
                        installation_type=row['installation_type'],
                        address_line1=row['address_line1'],
                        address_line2=row['address_line2'],
                        city=row['city'],
                        state=row['state'],
                        pincode=row['pincode'],
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        building_name=row['building_name'] if pd.notna(row['building_name']) else None,
                        flat_number=row['flat_number'] if pd.notna(row['flat_number']) else None,
                        floor_number=int(row['floor_number']) if pd.notna(row['floor_number']) else None,
                        total_flats_in_building=int(row['total_flats_in_building']) if pd.notna(row['total_flats_in_building']) else None,
                        is_community_monitor=bool(row['is_community_monitor']),
                        household_size=int(row['household_size']),
                        occupancy_type=row['occupancy_type'],
                        water_source=row['water_source'],
                        municipal_connection_number=row['municipal_connection_number'] if pd.notna(row['municipal_connection_number']) else None,
                        has_ro_system=bool(row['has_ro_system']),
                        ro_brand=row['ro_brand'] if pd.notna(row['ro_brand']) else None,
                        ro_installation_date=datetime.strptime(row['ro_installation_date'], '%Y-%m-%d').date() if pd.notna(row['ro_installation_date']) else None,
                        has_water_softener=bool(row['has_water_softener']),
                        has_uv_filter=bool(row['has_uv_filter']),
                        storage_tank_capacity_liters=int(row['storage_tank_capacity_liters']) if pd.notna(row['storage_tank_capacity_liters']) else None,
                        device_id=row['device_id'],
                        device_model=row['device_model'],
                        installation_date=datetime.strptime(row['installation_date'], '%Y-%m-%d').date(),
                        last_calibration_date=datetime.strptime(row['last_calibration_date'], '%Y-%m-%d').date() if pd.notna(row['last_calibration_date']) else None,
                        next_calibration_due=datetime.strptime(row['next_calibration_due'], '%Y-%m-%d').date() if pd.notna(row['next_calibration_due']) else None,
                        subscription_tier=row['subscription_tier'],
                        subscription_start_date=datetime.strptime(row['subscription_start_date'], '%Y-%m-%d').date() if pd.notna(row['subscription_start_date']) else None,
                        subscription_end_date=datetime.strptime(row['subscription_end_date'], '%Y-%m-%d').date() if pd.notna(row['subscription_end_date']) else None,
                        subscription_status=row['subscription_status'],
                        monthly_fee=float(row['monthly_fee']),
                        data_sharing_consent=bool(row['data_sharing_consent']),
                        public_dashboard_visible=bool(row['public_dashboard_visible']),
                        owner_user_id=int(row['owner_user_id']),
                        contact_phone=str(row['contact_phone']),
                        contact_email=row['contact_email'],
                        alert_phone_enabled=bool(row['alert_phone_enabled']),
                        alert_email_enabled=bool(row['alert_email_enabled']),
                        alert_sms_enabled=bool(row['alert_sms_enabled']),
                        alert_whatsapp_enabled=bool(row['alert_whatsapp_enabled']),
                        is_active=bool(row['is_active']),
                        notes=row['notes'] if pd.notna(row['notes']) else None
                    )
                    db.session.add(site)
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
            
            db.session.commit()
            
            if errors:
                flash(f'Imported {imported} sites with {len(errors)} errors. First error: {errors[0]}', 'warning')
            else:
                flash(f'Successfully imported {imported} residential sites!', 'success')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing sites: {str(e)}', 'error')
    else:
        flash('Invalid file format. Please upload a CSV file.', 'error')
    
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/residential/measurements', methods=['POST'])
@login_required
@admin_required
def import_residential_measurements():
    """Import residential measurements from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            
            for idx, row in df.iterrows():
                try:
                    measurement = ResidentialMeasurement(
                        site_id=int(row['site_id']),
                        measurement_datetime=datetime.strptime(row['measurement_datetime'], '%Y-%m-%d %H:%M:%S'),
                        measurement_type=row['measurement_type'],
                        ph_value=float(row['ph_value']) if pd.notna(row['ph_value']) else None,
                        tds_ppm=float(row['tds_ppm']) if pd.notna(row['tds_ppm']) else None,
                        temperature_celsius=float(row['temperature_celsius']) if pd.notna(row['temperature_celsius']) else None,
                        turbidity_ntu=float(row['turbidity_ntu']) if pd.notna(row['turbidity_ntu']) else None,
                        conductivity_us_cm=float(row['conductivity_us_cm']) if pd.notna(row['conductivity_us_cm']) else None,
                        free_chlorine_mg_l=float(row['free_chlorine_mg_l']) if pd.notna(row['free_chlorine_mg_l']) else None,
                        orp_mv=float(row['orp_mv']) if pd.notna(row['orp_mv']) else None,
                        flow_rate_lpm=float(row['flow_rate_lpm']) if pd.notna(row['flow_rate_lpm']) else None,
                        ro_inlet_tds=float(row['ro_inlet_tds']) if pd.notna(row['ro_inlet_tds']) else None,
                        ro_outlet_tds=float(row['ro_outlet_tds']) if pd.notna(row['ro_outlet_tds']) else None,
                        ro_rejection_rate_percent=float(row['ro_rejection_rate_percent']) if pd.notna(row['ro_rejection_rate_percent']) else None,
                        ro_membrane_health_percent=float(row['ro_membrane_health_percent']) if pd.notna(row['ro_membrane_health_percent']) else None,
                        water_quality_index=float(row['water_quality_index']) if pd.notna(row['water_quality_index']) else None,
                        is_safe_to_drink=bool(row['is_safe_to_drink']),
                        compliance_status=row['compliance_status'],
                        anomaly_detected=bool(row['anomaly_detected']),
                        anomaly_type=row['anomaly_type'] if pd.notna(row['anomaly_type']) else None,
                        anomaly_severity=row['anomaly_severity'] if pd.notna(row['anomaly_severity']) else None,
                        device_battery_percent=int(row['device_battery_percent']) if pd.notna(row['device_battery_percent']) else None,
                        device_signal_strength=int(row['device_signal_strength']) if pd.notna(row['device_signal_strength']) else None,
                        sensor_health_status=row['sensor_health_status'] if pd.notna(row['sensor_health_status']) else None
                    )
                    db.session.add(measurement)
                    imported += 1
                    
                    if (idx + 1) % 100 == 0:
                        db.session.commit()
                except Exception as e:
                    continue
            
            db.session.commit()
            flash(f'Successfully imported {imported} measurements!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing measurements: {str(e)}', 'error')
    
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/residential/alerts', methods=['POST'])
@login_required
@admin_required
def import_residential_alerts():
    """Import residential alerts from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            
            for idx, row in df.iterrows():
                try:
                    alert = ResidentialAlert(
                        site_id=int(row['site_id']),
                        measurement_id=int(row['measurement_id']) if pd.notna(row['measurement_id']) else None,
                        alert_datetime=datetime.strptime(row['alert_datetime'], '%Y-%m-%d %H:%M:%S'),
                        alert_type=row['alert_type'],
                        alert_severity=row['alert_severity'],
                        alert_title=row['alert_title'],
                        alert_message=row['alert_message'],
                        trigger_parameter=row['trigger_parameter'] if pd.notna(row['trigger_parameter']) else None,
                        trigger_value=float(row['trigger_value']) if pd.notna(row['trigger_value']) else None,
                        threshold_value=float(row['threshold_value']) if pd.notna(row['threshold_value']) else None,
                        recommended_action=row['recommended_action'] if pd.notna(row['recommended_action']) else None,
                        estimated_cost=float(row['estimated_cost']) if pd.notna(row['estimated_cost']) else None,
                        notification_sent_sms=bool(row['notification_sent_sms']),
                        notification_sent_email=bool(row['notification_sent_email']),
                        notification_sent_push=bool(row['notification_sent_push']),
                        notification_sent_whatsapp=bool(row['notification_sent_whatsapp']),
                        acknowledged=bool(row['acknowledged']),
                        acknowledged_at=datetime.strptime(row['acknowledged_at'], '%Y-%m-%d %H:%M:%S') if pd.notna(row['acknowledged_at']) else None,
                        acknowledged_by_user_id=int(row['acknowledged_by_user_id']) if pd.notna(row['acknowledged_by_user_id']) else None,
                        resolved=bool(row['resolved']),
                        resolved_at=datetime.strptime(row['resolved_at'], '%Y-%m-%d %H:%M:%S') if pd.notna(row['resolved_at']) else None,
                        resolution_notes=row['resolution_notes'] if pd.notna(row['resolution_notes']) else None
                    )
                    db.session.add(alert)
                    imported += 1
                except Exception as e:
                    continue
            
            db.session.commit()
            flash(f'Successfully imported {imported} alerts!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing alerts: {str(e)}', 'error')
    
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/residential/subscriptions', methods=['POST'])
@login_required
@admin_required
def import_residential_subscriptions():
    """Import residential subscriptions from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            
            for idx, row in df.iterrows():
                try:
                    subscription = ResidentialSubscription(
                        site_id=int(row['site_id']),
                        user_id=int(row['user_id']),
                        tier=row['tier'],
                        billing_cycle=row['billing_cycle'],
                        amount=float(row['amount']),
                        currency=row['currency'],
                        start_date=datetime.strptime(row['start_date'], '%Y-%m-%d').date(),
                        end_date=datetime.strptime(row['end_date'], '%Y-%m-%d').date(),
                        next_billing_date=datetime.strptime(row['next_billing_date'], '%Y-%m-%d').date() if pd.notna(row['next_billing_date']) else None,
                        status=row['status'],
                        auto_renew=bool(row['auto_renew']),
                        payment_method=row['payment_method'] if pd.notna(row['payment_method']) else None
                    )
                    db.session.add(subscription)
                    imported += 1
                except Exception as e:
                    continue
            
            db.session.commit()
            flash(f'Successfully imported {imported} subscriptions!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing subscriptions: {str(e)}', 'error')
    
    return redirect(url_for('admin.data_import'))

# ==================== PUBLIC IMPORT ROUTES ====================

@admin_bp.route('/import/public/sites', methods=['POST'])
@login_required
@admin_required
def import_public_sites():
    """Import public monitoring sites from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))

    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    site = Site(
                        site_name=row['site_name'],
                        site_code=row['site_code'],
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        address=row['address'] if pd.notna(row['address']) else None,
                        district=row['district'] if pd.notna(row['district']) else None,
                        state=row['state'] if pd.notna(row['state']) else None,
                        country=row['country'] if pd.notna(row['country']) else 'India',
                        postal_code=row['postal_code'] if pd.notna(row['postal_code']) else None,
                        environment_type=row['environment_type'] if pd.notna(row['environment_type']) else None,
                        is_coastal=bool(row['is_coastal']) if pd.notna(row['is_coastal']) else False,
                        population_density=row['population_density'] if pd.notna(row['population_density']) else None,
                        industrial_nearby=bool(row['industrial_nearby']) if pd.notna(row['industrial_nearby']) else False,
                        agricultural_nearby=bool(row['agricultural_nearby']) if pd.notna(row['agricultural_nearby']) else False,
                        description=row['description'] if pd.notna(row['description']) else None,
                        is_active=bool(row['is_active']) if pd.notna(row['is_active']) else True
                    )
                    db.session.add(site)
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
                    continue

            db.session.commit()

            if errors:
                flash(f'Imported {imported} sites with {len(errors)} errors. First error: {errors[0]}', 'warning')
            else:
                flash(f'Successfully imported {imported} public monitoring sites!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing sites: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')

    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/public/samples', methods=['POST'])
@login_required
@admin_required
def import_public_samples():
    """Import water samples from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))

    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    sample = WaterSample(
                        sample_id=row['sample_id'],
                        site_id=int(row['site_id']),
                        sub_site_details=row['sub_site_details'] if pd.notna(row['sub_site_details']) else None,
                        exact_latitude=float(row['exact_latitude']) if pd.notna(row['exact_latitude']) else None,
                        exact_longitude=float(row['exact_longitude']) if pd.notna(row['exact_longitude']) else None,
                        collection_date=datetime.strptime(row['collection_date'], '%Y-%m-%d').date(),
                        collection_time=datetime.strptime(row['collection_time'], '%H:%M:%S').time(),
                        collected_by_id=int(row['collected_by_id']) if pd.notna(row['collected_by_id']) else None,
                        source_type=row['source_type'] if pd.notna(row['source_type']) else None,
                        source_depth_meters=float(row['source_depth_meters']) if pd.notna(row['source_depth_meters']) else None,
                        storage_type=row['storage_type'] if pd.notna(row['storage_type']) else None,
                        storage_material=row['storage_material'] if pd.notna(row['storage_material']) else None,
                        discharge_type=row['discharge_type'] if pd.notna(row['discharge_type']) else None,
                        discharge_material=row['discharge_material'] if pd.notna(row['discharge_material']) else None,
                        water_source_root=row['water_source_root'] if pd.notna(row['water_source_root']) else None,
                        is_recycled=bool(row['is_recycled']) if pd.notna(row['is_recycled']) else False,
                        source_age_years=int(row['source_age_years']) if pd.notna(row['source_age_years']) else None,
                        pipe_material=row['pipe_material'] if pd.notna(row['pipe_material']) else None,
                        pipe_age_years=int(row['pipe_age_years']) if pd.notna(row['pipe_age_years']) else None,
                        status=row['status'] if pd.notna(row['status']) else 'collected',
                        priority=row['priority'] if pd.notna(row['priority']) else 'normal',
                        collection_notes=row['collection_notes'] if pd.notna(row['collection_notes']) else None
                    )
                    db.session.add(sample)
                    imported += 1

                    # Batch commit every 100 records
                    if (idx + 1) % 100 == 0:
                        db.session.commit()

                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
                    continue

            db.session.commit()

            if errors:
                flash(f'Imported {imported} samples with {len(errors)} errors. First error: {errors[0]}', 'warning')
            else:
                flash(f'Successfully imported {imported} water samples!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing samples: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')

    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/public/test-results', methods=['POST'])
@login_required
@admin_required
def import_public_test_results():
    """Import test results from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))

    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    test_result = TestResult(
                        sample_id=int(row['sample_id']),
                        test_date=datetime.strptime(row['test_date'], '%Y-%m-%d').date(),
                        test_time=datetime.strptime(row['test_time'], '%H:%M:%S').time(),
                        tested_by=row['tested_by'] if pd.notna(row['tested_by']) else None,
                        test_batch_id=row['test_batch_id'] if pd.notna(row['test_batch_id']) else None,
                        # Physical Parameters
                        turbidity_ntu=float(row['turbidity_ntu']) if pd.notna(row['turbidity_ntu']) else None,
                        temperature_celsius=float(row['temperature_celsius']) if pd.notna(row['temperature_celsius']) else None,
                        # Chemical Parameters
                        ph_value=float(row['ph_value']) if pd.notna(row['ph_value']) else None,
                        tds_ppm=float(row['tds_ppm']) if pd.notna(row['tds_ppm']) else None,
                        salinity_ppm=float(row['salinity_ppm']) if pd.notna(row['salinity_ppm']) else None,
                        conductivity_us_cm=float(row['conductivity_us_cm']) if pd.notna(row['conductivity_us_cm']) else None,
                        # Chlorine
                        free_chlorine_mg_l=float(row['free_chlorine_mg_l']) if pd.notna(row['free_chlorine_mg_l']) else None,
                        total_chlorine_mg_l=float(row['total_chlorine_mg_l']) if pd.notna(row['total_chlorine_mg_l']) else None,
                        chloride_mg_l=float(row['chloride_mg_l']) if pd.notna(row['chloride_mg_l']) else None,
                        # Metals
                        iron_mg_l=float(row['iron_mg_l']) if pd.notna(row['iron_mg_l']) else None,
                        manganese_mg_l=float(row['manganese_mg_l']) if pd.notna(row['manganese_mg_l']) else None,
                        lead_mg_l=float(row['lead_mg_l']) if pd.notna(row['lead_mg_l']) else None,
                        arsenic_mg_l=float(row['arsenic_mg_l']) if pd.notna(row['arsenic_mg_l']) else None,
                        # Hardness
                        total_hardness_mg_l=float(row['total_hardness_mg_l']) if pd.notna(row['total_hardness_mg_l']) else None,
                        # Nutrients
                        nitrate_mg_l=float(row['nitrate_mg_l']) if pd.notna(row['nitrate_mg_l']) else None,
                        ammonia_mg_l=float(row['ammonia_mg_l']) if pd.notna(row['ammonia_mg_l']) else None,
                        phosphate_mg_l=float(row['phosphate_mg_l']) if pd.notna(row['phosphate_mg_l']) else None,
                        # Biological
                        coliform_status=row['coliform_status'] if pd.notna(row['coliform_status']) else None,
                        e_coli_status=row['e_coli_status'] if pd.notna(row['e_coli_status']) else None,
                        coliform_count_cfu_100ml=float(row['coliform_count_cfu_100ml']) if pd.notna(row['coliform_count_cfu_100ml']) else None,
                        # Dissolved Oxygen
                        dissolved_oxygen_mg_l=float(row['dissolved_oxygen_mg_l']) if pd.notna(row['dissolved_oxygen_mg_l']) else None,
                        bod_mg_l=float(row['bod_mg_l']) if pd.notna(row['bod_mg_l']) else None,
                        cod_mg_l=float(row['cod_mg_l']) if pd.notna(row['cod_mg_l']) else None,
                        # Other Parameters
                        alkalinity_mg_l=float(row['alkalinity_mg_l']) if pd.notna(row['alkalinity_mg_l']) else None,
                        sulfate_mg_l=float(row['sulfate_mg_l']) if pd.notna(row['sulfate_mg_l']) else None,
                        fluoride_mg_l=float(row['fluoride_mg_l']) if pd.notna(row['fluoride_mg_l']) else None,
                        # Quality Control
                        qc_status=row['qc_status'] if pd.notna(row['qc_status']) else 'pending',
                        qc_notes=row['qc_notes'] if pd.notna(row['qc_notes']) else None,
                        test_method=row['test_method'] if pd.notna(row['test_method']) else None,
                        test_notes=row['test_notes'] if pd.notna(row['test_notes']) else None
                    )
                    db.session.add(test_result)
                    imported += 1

                    # Batch commit every 100 records
                    if (idx + 1) % 100 == 0:
                        db.session.commit()

                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
                    continue

            db.session.commit()

            if errors:
                flash(f'Imported {imported} test results with {len(errors)} errors. First error: {errors[0]}', 'warning')
            else:
                flash(f'Successfully imported {imported} test results!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing test results: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')

    return redirect(url_for('admin.data_import'))

@admin_bp.route('/import/public/analyses', methods=['POST'])
@login_required
@admin_required
def import_public_analyses():
    """Import contamination analyses from CSV"""
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.data_import'))

    file = request.files['file']
    if file and allowed_file(file.filename):
        try:
            df = pd.read_csv(file)
            imported = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    analysis = Analysis(
                        sample_id=int(row['sample_id']),
                        test_result_id=int(row['test_result_id']) if pd.notna(row['test_result_id']) else None,
                        analysis_date=datetime.strptime(row['analysis_date'], '%Y-%m-%d %H:%M:%S') if pd.notna(row['analysis_date']) else datetime.utcnow(),
                        analyzed_by_id=int(row['analyzed_by_id']) if pd.notna(row['analyzed_by_id']) else None,
                        analysis_type=row['analysis_type'] if pd.notna(row['analysis_type']) else 'automated',
                        # Primary Classification
                        contamination_detected=bool(row['contamination_detected']) if pd.notna(row['contamination_detected']) else False,
                        primary_cause=row['primary_cause'] if pd.notna(row['primary_cause']) else None,
                        confidence_level=float(row['confidence_level']) if pd.notna(row['confidence_level']) else None,
                        severity=row['severity'] if pd.notna(row['severity']) else None,
                        # Rule-Based Scores
                        runoff_sediment_score=float(row['runoff_sediment_score']) if pd.notna(row['runoff_sediment_score']) else None,
                        runoff_sediment_indicators=row['runoff_sediment_indicators'] if pd.notna(row['runoff_sediment_indicators']) else None,
                        sewage_ingress_score=float(row['sewage_ingress_score']) if pd.notna(row['sewage_ingress_score']) else None,
                        sewage_ingress_indicators=row['sewage_ingress_indicators'] if pd.notna(row['sewage_ingress_indicators']) else None,
                        salt_intrusion_score=float(row['salt_intrusion_score']) if pd.notna(row['salt_intrusion_score']) else None,
                        salt_intrusion_indicators=row['salt_intrusion_indicators'] if pd.notna(row['salt_intrusion_indicators']) else None,
                        pipe_corrosion_score=float(row['pipe_corrosion_score']) if pd.notna(row['pipe_corrosion_score']) else None,
                        pipe_corrosion_indicators=row['pipe_corrosion_indicators'] if pd.notna(row['pipe_corrosion_indicators']) else None,
                        disinfectant_decay_score=float(row['disinfectant_decay_score']) if pd.notna(row['disinfectant_decay_score']) else None,
                        disinfectant_decay_indicators=row['disinfectant_decay_indicators'] if pd.notna(row['disinfectant_decay_indicators']) else None,
                        # Compliance
                        who_compliant=bool(row['who_compliant']) if pd.notna(row['who_compliant']) else None,
                        bis_compliant=bool(row['bis_compliant']) if pd.notna(row['bis_compliant']) else None,
                        non_compliant_parameters=row['non_compliant_parameters'] if pd.notna(row['non_compliant_parameters']) else None,
                        # Recommendations
                        immediate_actions=row['immediate_actions'] if pd.notna(row['immediate_actions']) else None,
                        short_term_solutions=row['short_term_solutions'] if pd.notna(row['short_term_solutions']) else None,
                        long_term_solutions=row['long_term_solutions'] if pd.notna(row['long_term_solutions']) else None,
                        estimated_cost=row['estimated_cost'] if pd.notna(row['estimated_cost']) else None,
                        implementation_priority=row['implementation_priority'] if pd.notna(row['implementation_priority']) else None,
                        # Follow-up
                        follow_up_required=bool(row['follow_up_required']) if pd.notna(row['follow_up_required']) else False,
                        follow_up_date=datetime.strptime(row['follow_up_date'], '%Y-%m-%d').date() if pd.notna(row['follow_up_date']) else None,
                        # Status
                        status=row['status'] if pd.notna(row['status']) else 'pending',
                        notes=row['notes'] if pd.notna(row['notes']) else None
                    )
                    db.session.add(analysis)
                    imported += 1

                    # Batch commit every 100 records
                    if (idx + 1) % 100 == 0:
                        db.session.commit()

                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
                    continue

            db.session.commit()

            if errors:
                flash(f'Imported {imported} analyses with {len(errors)} errors. First error: {errors[0]}', 'warning')
            else:
                flash(f'Successfully imported {imported} contamination analyses!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing analyses: {str(e)}', 'error')
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')

    return redirect(url_for('admin.data_import'))

# ==================== TEMPLATE DOWNLOAD ROUTES ====================

@admin_bp.route('/download/residential/template/<template_type>')
@login_required
@admin_required
def download_residential_template(template_type):
    """Download CSV template for residential data"""
    template_files = {
        'sites': 'residential_sites_template.csv',
        'measurements': 'residential_measurements_template.csv',
        'alerts': 'residential_alerts_template.csv',
        'subscriptions': 'residential_subscriptions_template.csv'
    }

    filename = template_files.get(template_type)
    if filename:
        filepath = TEMPLATES_DIR / filename
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True, download_name=filename)

    flash('Template not found', 'error')
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/download/residential/sample/<sample_type>')
@login_required
@admin_required
def download_residential_sample(sample_type):
    """Download sample CSV data for residential monitoring"""
    sample_files = {
        'sites': 'residential/chennai_residential_sites.csv',
        'measurements': 'residential/chennai_residential_measurements.csv',
        'alerts': 'residential/chennai_residential_alerts.csv',
        'subscriptions': 'residential/chennai_residential_subscriptions.csv'
    }

    relative_path = sample_files.get(sample_type)
    if relative_path:
        filepath = SAMPLES_DIR / relative_path
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True, download_name=f'sample_{filepath.name}')

    flash('Sample data not found', 'error')
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/download/public/template/<template_type>')
@login_required
@admin_required
def download_public_template(template_type):
    """Download CSV template for public data"""
    template_files = {
        'sites': 'public_sites_template.csv',
        'samples': 'public_samples_template.csv',
        'test_results': 'public_test_results_template.csv',
        'analyses': 'public_analyses_template.csv'
    }

    filename = template_files.get(template_type)
    if filename:
        filepath = TEMPLATES_DIR / filename
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True, download_name=filename)

    flash('Template not found', 'error')
    return redirect(url_for('admin.data_import'))

@admin_bp.route('/download/public/sample/<sample_type>')
@login_required
@admin_required
def download_public_sample(sample_type):
    """Download sample CSV data for public monitoring"""
    sample_files = {
        'sites': 'public/chennai_public_sites.csv',
        'samples': 'public/chennai_public_samples.csv',
        'test_results': 'public/chennai_public_test_results.csv',
        'analyses': 'public/chennai_public_analyses.csv'
    }

    relative_path = sample_files.get(sample_type)
    if relative_path:
        filepath = SAMPLES_DIR / relative_path
        if filepath.exists():
            return send_file(str(filepath), as_attachment=True, download_name=f'sample_{filepath.name}')

    flash('Public sample data not found', 'error')
    return redirect(url_for('admin.data_import'))
