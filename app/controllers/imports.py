"""
Imports Controller
Handles data import workflows, data source management, and import history
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from app import db
from app.models.data_source import DataSource
from app.models.import_batch import ImportBatch
from app.services.csv_importer import CSVImporter


# Create blueprint
imports_bp = Blueprint('imports', __name__, url_prefix='/imports')


# ============================================================================
# DATA SOURCES MANAGEMENT
# ============================================================================

@imports_bp.route('/sources')
@login_required
def list_sources():
    """List all data sources"""
    sources = DataSource.query.order_by(DataSource.name).all()
    return render_template('imports/sources_list.html', sources=sources)


@imports_bp.route('/sources/new', methods=['GET', 'POST'])
@login_required
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

@imports_bp.route('/new')
@login_required
def new_import():
    """Start new import wizard"""
    # Clear any previous import session data
    session.pop('import_wizard', None)

    sources = DataSource.query.filter_by(is_active=True).order_by(DataSource.name).all()
    return render_template('imports/wizard_upload.html', sources=sources)


@imports_bp.route('/upload', methods=['POST'])
@login_required
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
        importer = CSVImporter(current_app.config['UPLOAD_FOLDER'])
        if not importer.allowed_file(file.filename):
            flash(f'Invalid file type. Allowed types: CSV, Excel (.xlsx, .xls)', 'error')
            return redirect(url_for('imports.new_import'))

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        # Ensure upload directory exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Read file and get preview
        records, columns = importer.read_file(filepath)

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
def validate():
    """Validate uploaded data (Step 2)"""
    import json
    import hashlib

    wizard_data = session.get('import_wizard')
    if not wizard_data:
        flash('No import in progress', 'error')
        return redirect(url_for('imports.new_import'))

    try:
        importer = CSVImporter(current_app.config['UPLOAD_FOLDER'])

        # Read and validate file
        records, columns = importer.read_file(wizard_data['filepath'])
        validation_results = importer.validator.validate_batch(records)

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
            failed_imports=len(validation_results.get('errors', [])),
            warnings_count=len(validation_results.get('warnings', [])),
            validation_errors=json.dumps(validation_results.get('errors', [])),
            validation_warnings=json.dumps(validation_results.get('warnings', [])),
            data_preview=json.dumps(wizard_data['preview']),
            status='validation_failed' if validation_results.get('errors') else 'validating'
        )

        # Add validation log entry
        batch.add_log_entry(f"File validated: {len(records)} records, {len(validation_results.get('errors', []))} errors, {len(validation_results.get('warnings', []))} warnings")

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
def confirm_import():
    """Confirm and execute import (Step 3)"""
    wizard_data = session.get('import_wizard')
    if not wizard_data:
        flash('No import in progress', 'error')
        return redirect(url_for('imports.new_import'))

    try:
        # Delete the validation batch since we're proceeding with import
        # process_import will create a new batch with actual import results
        if 'batch_id' in wizard_data:
            validation_batch = ImportBatch.query.get(wizard_data['batch_id'])
            if validation_batch:
                db.session.delete(validation_batch)
                db.session.commit()

        importer = CSVImporter(current_app.config['UPLOAD_FOLDER'])

        # Execute the import
        results = importer.process_import(
            file_path=wizard_data['filepath'],
            file_name=wizard_data['filename'],
            data_source_id=wizard_data['data_source_id'],
            user_id=current_user.id
        )

        # Clear wizard session data
        session.pop('import_wizard', None)

        # Show results
        if results['success']:
            flash(f"Import completed successfully! {results['import']['successful']} records imported.", 'success')
        else:
            flash(f"Import completed with errors. Check the batch details for more information.", 'warning')

        return redirect(url_for('imports.view_batch', batch_id=results['batch_id']))

    except Exception as e:
        flash(f'Error during import: {str(e)}', 'error')
        # Don't clear session so user can retry
        return redirect(url_for('imports.validate'))


@imports_bp.route('/cancel')
@login_required
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
def download_template():
    """Download CSV template with predefined water quality fields"""
    # Define CSV headers (required + optional fields)
    headers = [
        'Sample ID',
        'Site Name',
        'Collection Date',
        'pH',
        'Temperature (°C)',
        'Turbidity (NTU)',
        'Arsenic (mg/L)',
        'Lead (mg/L)',
        'Iron (mg/L)',
        'Nitrate (mg/L)',
        'Fluoride (mg/L)',
        'Chloride (mg/L)',
        'Sulfate (mg/L)',
        'TDS (mg/L)',
        'Hardness (mg/L)',
        'Conductivity (μS/cm)',
        'Dissolved Oxygen (mg/L)',
        'Notes'
    ]

    # Add one example row
    example_row = [
        'SAMPLE-001',
        'Chennai Water Treatment Plant',
        '2025-10-26',
        '7.2',
        '28',
        '2.5',
        '0.005',
        '0.003',
        '0.15',
        '35',
        '0.8',
        '180',
        '220',
        '450',
        '280',
        '650',
        '6.5',
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

    return render_template('imports/history.html',
                         batches=batches,
                         sources=sources,
                         status_choices=status_choices,
                         selected_source=source_id,
                         selected_status=status)


@imports_bp.route('/batch/<int:batch_id>')
@login_required
def view_batch(batch_id):
    """View import batch details"""
    batch = ImportBatch.query.get_or_404(batch_id)

    return render_template('imports/batch_detail.html', batch=batch)


@imports_bp.route('/batch/<int:batch_id>/rollback', methods=['POST'])
@login_required
def rollback_batch(batch_id):
    """Rollback an import batch"""
    batch = ImportBatch.query.get_or_404(batch_id)

    try:
        # TODO: Implement actual rollback logic
        # This would need to:
        # 1. Find all records created by this batch
        # 2. Delete them in a transaction
        # 3. Mark batch as rolled back

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
def api_list_sources():
    """API: Get list of data sources"""
    sources = DataSource.query.filter_by(is_active=True).all()
    return jsonify([source.to_dict() for source in sources])


@imports_bp.route('/api/batch/<int:batch_id>/status', methods=['GET'])
@login_required
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
