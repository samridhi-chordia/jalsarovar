"""
Imports Controller
Handles data import workflows, data source management, and import history
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import hashlib
import pandas as pd
from datetime import datetime

from app import db
from app.models import DataSource, ImportBatch, Site, WaterSample, TestResult
from app.services.data_processor import DataProcessor


# Create blueprint
imports_bp = Blueprint('imports', __name__, url_prefix='/imports')


def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def import_permission_required(f):
    """Decorator to require import permissions (admin, field_collector, or analyst)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Authentication required', 'error')
            return redirect(url_for('auth.login'))

        # Check if user has any import-related permissions
        can_import = (
            current_user.is_admin() or
            current_user.has_permission('can_bulk_import') or
            current_user.has_permission('can_create_sites') or
            current_user.has_permission('can_create_samples')
        )

        if not can_import:
            flash('You do not have permission to import data', 'error')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# DATA SOURCES MANAGEMENT
# ============================================================================

@imports_bp.route('/sources')
@login_required
@admin_required
def list_sources():
    """List all data sources"""
    sources = DataSource.query.order_by(DataSource.name).all()
    return render_template('imports/sources_list.html', sources=sources)


@imports_bp.route('/sources/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_source():
    """Create new data source"""
    if request.method == 'POST':
        try:
            source = DataSource(
                name=request.form['name'],
                description=request.form.get('description'),
                source_type=request.form['source_type'],
                contact_person=request.form.get('contact_person'),
                contact_email=request.form.get('contact_email'),
                contact_phone=request.form.get('contact_phone'),
                organization=request.form.get('organization'),
                website=request.form.get('website'),
                data_format_description=request.form.get('data_format_description'),
                expected_file_format=request.form.get('expected_file_format'),
                has_custom_parser=request.form.get('has_custom_parser') == 'on',
                parser_name=request.form.get('parser_name') if request.form.get('has_custom_parser') else None,
                is_trusted=request.form.get('is_trusted') == 'on',
                created_by_id=current_user.id
            )

            db.session.add(source)
            db.session.commit()

            flash(f'Data source "{source.name}" created successfully', 'success')
            return redirect(url_for('imports.list_sources'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating data source: {str(e)}', 'error')

    # GET - show form
    source_types = dict(DataSource.get_source_types())
    file_formats = dict(DataSource.get_file_formats())
    return render_template('imports/source_form.html',
                         source=None,
                         source_types=source_types,
                         file_formats=file_formats)


@imports_bp.route('/sources/<int:source_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_source(source_id):
    """Edit existing data source"""
    source = DataSource.query.get_or_404(source_id)

    if request.method == 'POST':
        try:
            source.name = request.form['name']
            source.description = request.form.get('description')
            source.source_type = request.form['source_type']
            source.contact_person = request.form.get('contact_person')
            source.contact_email = request.form.get('contact_email')
            source.contact_phone = request.form.get('contact_phone')
            source.organization = request.form.get('organization')
            source.website = request.form.get('website')
            source.data_format_description = request.form.get('data_format_description')
            source.expected_file_format = request.form.get('expected_file_format')
            source.has_custom_parser = request.form.get('has_custom_parser') == 'on'
            source.parser_name = request.form.get('parser_name') if request.form.get('has_custom_parser') else None
            source.is_trusted = request.form.get('is_trusted') == 'on'

            db.session.commit()

            flash(f'Data source "{source.name}" updated successfully', 'success')
            return redirect(url_for('imports.list_sources'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating data source: {str(e)}', 'error')

    # GET - show form
    source_types = dict(DataSource.get_source_types())
    file_formats = dict(DataSource.get_file_formats())
    return render_template('imports/source_form.html',
                         source=source,
                         source_types=source_types,
                         file_formats=file_formats)


@imports_bp.route('/sources/<int:source_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_source(source_id):
    """Delete data source"""
    source = DataSource.query.get_or_404(source_id)

    try:
        # Check if source has imports
        if source.total_imports > 0:
            flash(f'Cannot delete "{source.name}" - it has {source.total_imports} import(s). ' +
                  'Delete the imports first.', 'error')
            return redirect(url_for('imports.list_sources'))

        name = source.name
        db.session.delete(source)
        db.session.commit()

        flash(f'Data source "{name}" deleted successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting data source: {str(e)}', 'error')

    return redirect(url_for('imports.list_sources'))


# ============================================================================
# IMPORT WIZARD
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_file(filepath):
    """Read CSV or Excel file and return records and columns"""
    ext = filepath.rsplit('.', 1)[1].lower()

    try:
        if ext == 'csv':
            df = pd.read_csv(filepath)
        else:  # xlsx, xls
            df = pd.read_excel(filepath)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Convert to list of dicts
        records = df.to_dict('records')
        columns = list(df.columns)

        return records, columns
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")


def validate_records(records):
    """Validate water quality records"""
    errors = []
    warnings = []
    valid_count = 0

    required_fields = ['site_name', 'collection_date']

    for idx, record in enumerate(records, start=2):  # Start at 2 (row 1 is header)
        row_errors = []
        row_warnings = []

        # Check required fields
        for field in required_fields:
            # Try common variations of field names
            field_variations = [field, field.replace('_', ' '), field.title(), field.upper()]
            found = False
            for var in field_variations:
                if var in record and record[var]:
                    found = True
                    break

            if not found:
                row_errors.append({
                    'row': idx,
                    'field': field,
                    'error': f'Required field "{field}" is missing or empty',
                    'value': None
                })

        # Validate numeric fields if present
        numeric_fields = {
            'ph': (0, 14, 'pH must be between 0 and 14'),
            'turbidity': (0, 1000, 'Turbidity must be between 0 and 1000 NTU'),
            'tds': (0, 10000, 'TDS must be between 0 and 10000 ppm'),
            'temperature': (-10, 100, 'Temperature must be between -10 and 100 C')
        }

        for field, (min_val, max_val, msg) in numeric_fields.items():
            # Try variations
            for key in record.keys():
                if field.lower() in key.lower():
                    val = record[key]
                    if val is not None and val != '':
                        try:
                            num_val = float(val)
                            if num_val < min_val or num_val > max_val:
                                row_warnings.append({
                                    'row': idx,
                                    'field': key,
                                    'warning': msg,
                                    'value': val
                                })
                        except (ValueError, TypeError):
                            row_errors.append({
                                'row': idx,
                                'field': key,
                                'error': f'Invalid numeric value',
                                'value': val
                            })
                    break

        errors.extend(row_errors)
        warnings.extend(row_warnings)

        if not row_errors:
            valid_count += 1

    return {
        'total': len(records),
        'valid': valid_count,
        'invalid': len(records) - valid_count,
        'warnings': len(warnings),
        'errors': len(errors),
        'error_list': errors[:50],  # Limit to first 50
        'warning_list': warnings[:50]
    }


@imports_bp.route('/new')
@login_required
@import_permission_required
def new_import():
    """Start new import wizard"""
    # Clear any previous import session data
    session.pop('import_wizard', None)

    sources = DataSource.query.filter_by(is_active=True).order_by(DataSource.name).all()
    return render_template('imports/wizard_upload.html', sources=sources)


@imports_bp.route('/upload', methods=['POST'])
@login_required
@import_permission_required
def upload_file():
    """Handle file upload (Step 1)"""
    try:
        # Validate inputs
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('imports.new_import'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('imports.new_import'))

        data_source_id = request.form.get('data_source_id', type=int)
        if not data_source_id:
            flash('Please select a data source', 'error')
            return redirect(url_for('imports.new_import'))

        # Validate file extension
        if not allowed_file(file.filename):
            flash('Invalid file type. Allowed types: CSV, Excel (.xlsx, .xls)', 'error')
            return redirect(url_for('imports.new_import'))

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Read file and get preview
        records, columns = read_file(filepath)

        if not records:
            os.remove(filepath)  # Clean up
            flash('File is empty or could not be read', 'error')
            return redirect(url_for('imports.new_import'))

        # Store in session for next step
        session['import_wizard'] = {
            'filepath': filepath,
            'filename': file.filename,
            'data_source_id': data_source_id,
            'columns': columns,
            'record_count': len(records),
            'preview': records[:5]  # First 5 rows for preview
        }

        # Redirect to validation step
        return redirect(url_for('imports.validate'))

    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'error')
        return redirect(url_for('imports.new_import'))


@imports_bp.route('/validate')
@login_required
@import_permission_required
def validate():
    """Validate uploaded data (Step 2)"""
    wizard_data = session.get('import_wizard')
    if not wizard_data:
        flash('No import in progress', 'error')
        return redirect(url_for('imports.new_import'))

    try:
        # Read and validate file
        records, columns = read_file(wizard_data['filepath'])
        validation_results = validate_records(records)

        # Calculate file hash and size
        file_path = wizard_data['filepath']
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Create ImportBatch record to track this validation attempt
        batch = ImportBatch(
            data_source_id=wizard_data['data_source_id'],
            file_name=wizard_data['filename'],
            file_path=file_path,
            file_size_bytes=file_size,
            file_hash=file_hash,
            imported_by_id=current_user.id,
            total_records=len(records),
            failed_imports=validation_results.get('invalid', 0),
            warnings_count=validation_results.get('warnings', 0),
            validation_errors=json.dumps(validation_results.get('error_list', [])),
            validation_warnings=json.dumps(validation_results.get('warning_list', [])),
            data_preview=json.dumps(wizard_data['preview']),
            status='validation_failed' if validation_results.get('invalid', 0) > 0 else 'validating'
        )

        # Add validation log entry
        batch.add_log_entry(f"File validated: {len(records)} records, {validation_results.get('invalid', 0)} errors, {validation_results.get('warnings', 0)} warnings")

        db.session.add(batch)
        db.session.commit()

        # Store validation results and batch_id in session
        wizard_data['validation_results'] = validation_results
        wizard_data['batch_id'] = batch.id
        session['import_wizard'] = wizard_data

        data_source = DataSource.query.get(wizard_data['data_source_id'])

        return render_template('imports/wizard_validate.html',
                             data_source=data_source,
                             wizard_data=wizard_data,
                             validation=validation_results,
                             batch=batch)

    except Exception as e:
        flash(f'Error validating data: {str(e)}', 'error')
        return redirect(url_for('imports.new_import'))


@imports_bp.route('/confirm', methods=['POST'])
@login_required
@import_permission_required
def confirm_import():
    """Confirm and execute import (Step 3)"""
    wizard_data = session.get('import_wizard')
    if not wizard_data:
        flash('No import in progress', 'error')
        return redirect(url_for('imports.new_import'))

    try:
        # Get or create batch
        batch_id = wizard_data.get('batch_id')
        if batch_id:
            batch = ImportBatch.query.get(batch_id)
        else:
            batch = None

        # Read the file
        records, columns = read_file(wizard_data['filepath'])

        # Process import
        batch.status = 'importing'
        batch.processing_start = datetime.utcnow()
        batch.add_log_entry("Import started")
        db.session.commit()

        # Initialize ML processor once for efficiency
        processor = DataProcessor()

        successful = 0
        failed = 0

        for record in records:
            try:
                # Find or get site name
                site_name = None
                for key in record.keys():
                    if 'site' in key.lower() and 'name' in key.lower():
                        site_name = record[key]
                        break

                if not site_name:
                    failed += 1
                    continue

                # Find site by name
                site = Site.query.filter(Site.site_name.ilike(f'%{site_name}%')).first()

                if not site:
                    # Create new site with minimal info
                    site = Site(
                        site_code=f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{successful}",
                        site_name=site_name,
                        state=record.get('state', record.get('State', 'Unknown')),
                        district=record.get('district', record.get('District', 'Unknown')),
                        site_type=record.get('site_type', record.get('Site Type', 'pond'))
                    )
                    db.session.add(site)
                    db.session.flush()

                # Get collection date
                collection_date = None
                for key in record.keys():
                    if 'date' in key.lower():
                        try:
                            date_val = record[key]
                            if isinstance(date_val, str):
                                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y']:
                                    try:
                                        collection_date = datetime.strptime(date_val, fmt)
                                        break
                                    except:
                                        continue
                            elif hasattr(date_val, 'date'):
                                collection_date = date_val
                        except:
                            pass
                        break

                if not collection_date:
                    collection_date = datetime.utcnow()

                # Create water sample
                sample = WaterSample(
                    site_id=site.id,
                    sample_code=f"IMP-{batch.id}-{successful}",
                    collection_date=collection_date,
                    collected_by=f"Import Batch #{batch.id}"
                )
                db.session.add(sample)
                db.session.flush()

                # Create test result
                test_result = TestResult(sample_id=sample.id)

                # Map common field names
                field_mapping = {
                    'ph': ['ph', 'ph_value', 'pH', 'pH Value'],
                    'turbidity_ntu': ['turbidity', 'turbidity_ntu', 'Turbidity', 'Turbidity (NTU)'],
                    'tds_ppm': ['tds', 'tds_ppm', 'TDS', 'TDS (mg/L)', 'TDS (ppm)'],
                    'temperature_celsius': ['temperature', 'temp', 'Temperature', 'Temperature (C)'],
                    'iron_mg_l': ['iron', 'Iron', 'Iron (mg/L)', 'Fe'],
                    'chloride_mg_l': ['chloride', 'Chloride', 'Chloride (mg/L)', 'Cl'],
                    'total_coliform_mpn': ['coliform', 'total_coliform', 'Total Coliform', 'Coliform']
                }

                for db_field, variations in field_mapping.items():
                    for var in variations:
                        if var in record and record[var] is not None and record[var] != '':
                            try:
                                setattr(test_result, db_field, float(record[var]))
                            except (ValueError, TypeError):
                                pass
                            break

                db.session.add(test_result)
                db.session.flush()  # Ensure sample ID is available

                # Trigger ML analysis automatically
                try:
                    processor.process_new_sample(sample.id)
                except Exception as ml_error:
                    # Log ML error but don't fail the import
                    batch.add_log_entry(f"ML analysis failed for sample {sample.id}: {str(ml_error)}")

                successful += 1

            except Exception as e:
                failed += 1
                continue

        # Update batch with results
        batch.successful_imports = successful
        batch.failed_imports = failed
        batch.processing_end = datetime.utcnow()
        batch.status = 'completed' if failed == 0 else 'completed'
        batch.add_log_entry(f"Import completed: {successful} successful, {failed} failed")

        db.session.commit()

        # Clear wizard session data
        session.pop('import_wizard', None)

        # Show results
        if successful > 0:
            flash(f"Import completed! {successful} records imported successfully.", 'success')
        else:
            flash("Import completed with errors. Check the batch details.", 'warning')

        return redirect(url_for('imports.view_batch', batch_id=batch.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error during import: {str(e)}', 'error')
        return redirect(url_for('imports.validate'))


@imports_bp.route('/cancel')
@login_required
@import_permission_required
def cancel_import():
    """Cancel import wizard"""
    wizard_data = session.get('import_wizard')
    if wizard_data and 'filepath' in wizard_data:
        # Clean up uploaded file
        try:
            if os.path.exists(wizard_data['filepath']):
                os.remove(wizard_data['filepath'])
        except:
            pass

    session.pop('import_wizard', None)
    flash('Import cancelled', 'info')
    return redirect(url_for('imports.history'))


@imports_bp.route('/download_template')
@login_required
@import_permission_required
def download_template():
    """Download CSV template with predefined water quality fields"""
    # Define CSV headers (required + optional fields)
    headers = [
        'Site Name',
        'State',
        'District',
        'Collection Date',
        'pH',
        'Temperature (C)',
        'Turbidity (NTU)',
        'TDS (ppm)',
        'Iron (mg/L)',
        'Chloride (mg/L)',
        'Total Coliform (MPN)',
        'Notes'
    ]

    # Add one example row
    example_row = [
        'Sample Water Body',
        'Bihar',
        'Patna',
        '2025-01-15',
        '7.2',
        '28',
        '2.5',
        '450',
        '0.15',
        '180',
        '0',
        'Sample data - replace with your actual measurements'
    ]

    # Create CSV content
    csv_lines = [','.join(headers), ','.join(example_row)]
    csv_content = '\n'.join(csv_lines)

    # Create response with proper headers
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=water_quality_template.csv'

    return response


# ============================================================================
# IMPORT HISTORY
# ============================================================================

@imports_bp.route('/history')
@login_required
@import_permission_required
def history():
    """View import history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filter options
    source_id = request.args.get('source_id', type=int)
    status = request.args.get('status')

    query = ImportBatch.query

    if source_id:
        query = query.filter_by(data_source_id=source_id)
    if status:
        query = query.filter_by(status=status)

    batches = query.order_by(ImportBatch.import_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    sources = DataSource.query.order_by(DataSource.name).all()
    status_choices = dict(ImportBatch.get_status_choices())

    # Calculate import statistics
    stats = {
        'total_imports': ImportBatch.query.count(),
        'completed': ImportBatch.query.filter_by(status='completed').count(),
        'failed': ImportBatch.query.filter_by(status='failed').count(),
        'total_records': db.session.query(db.func.sum(ImportBatch.successful_imports)).scalar() or 0
    }

    return render_template('imports/history.html',
                         batches=batches.items,
                         pagination=batches,
                         sources=sources,
                         status_choices=status_choices,
                         selected_source=source_id,
                         selected_status=status,
                         stats=stats)


@imports_bp.route('/batch/<int:batch_id>')
@login_required
@import_permission_required
def view_batch(batch_id):
    """View import batch details"""
    batch = ImportBatch.query.get_or_404(batch_id)

    return render_template('imports/batch_detail.html', batch=batch)


@imports_bp.route('/batch/<int:batch_id>/rollback', methods=['POST'])
@login_required
@admin_required
def rollback_batch(batch_id):
    """Rollback an import batch"""
    batch = ImportBatch.query.get_or_404(batch_id)

    try:
        batch.rollback(current_user.id)
        db.session.commit()

        flash(f'Import batch {batch_id} rolled back successfully', 'success')

    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rolling back import: {str(e)}', 'error')

    return redirect(url_for('imports.view_batch', batch_id=batch_id))


# ============================================================================
# API ENDPOINTS (for AJAX calls)
# ============================================================================

@imports_bp.route('/api/sources', methods=['GET'])
@login_required
@admin_required
def api_list_sources():
    """API: Get list of data sources"""
    sources = DataSource.query.filter_by(is_active=True).all()
    return jsonify([source.to_dict() for source in sources])


@imports_bp.route('/api/batch/<int:batch_id>/status', methods=['GET'])
@login_required
@admin_required
def api_batch_status(batch_id):
    """API: Get current status of import batch (for polling)"""
    batch = ImportBatch.query.get_or_404(batch_id)

    return jsonify({
        'id': batch.id,
        'status': batch.status,
        'is_in_progress': batch.is_in_progress,
        'is_complete': batch.is_complete,
        'total_records': batch.total_records,
        'successful_imports': batch.successful_imports,
        'failed_imports': batch.failed_imports,
        'success_rate': batch.success_rate
    })
