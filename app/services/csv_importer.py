"""
CSV/Excel Importer Service
Handles importing water quality data from CSV and Excel files
"""
import csv
import hashlib
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd

from app import db
from app.models import WaterSample, TestResult, Site
from app.models.import_batch import ImportBatch
from app.models.data_source import DataSource
from app.services.data_validator import DataValidator


class CSVImporter:
    """
    Generic CSV/Excel import service for water quality data.

    Supports:
    - CSV files (.csv)
    - Excel files (.xlsx, .xls)
    - Custom field mapping
    - Validation before import
    - Batch tracking with rollback capability
    """

    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

    # Default field mapping (CSV column name -> database field name)
    DEFAULT_FIELD_MAPPING = {
        'Sample ID': 'sample_id',
        'Site Name': 'site_name',
        'Location': 'location',
        'Collection Date': 'collection_date',
        'Analysis Date': 'analysis_date',
        'pH': 'ph_value',
        'Temperature (°C)': 'temperature_c',
        'Turbidity (NTU)': 'turbidity_ntu',
        'Arsenic (mg/L)': 'arsenic_mg_l',
        'Lead (mg/L)': 'lead_mg_l',
        'Iron (mg/L)': 'iron_mg_l',
        'Nitrate (mg/L)': 'nitrate_mg_l',
        'Fluoride (mg/L)': 'fluoride_mg_l',
        'Chloride (mg/L)': 'chloride_mg_l',
        'Sulfate (mg/L)': 'sulfate_mg_l',
        'TDS (mg/L)': 'total_dissolved_solids_mg_l',
        'Hardness (mg/L)': 'hardness_mg_l',
        'Conductivity (μS/cm)': 'conductivity_us_cm',
        'Dissolved Oxygen (mg/L)': 'dissolved_oxygen_mg_l',
        'Notes': 'notes'
    }

    def __init__(self, upload_folder):
        """
        Initialize CSV importer.

        Args:
            upload_folder (str): Path to folder for storing uploaded files
        """
        self.upload_folder = upload_folder
        self.validator = DataValidator()
        self.import_batch = None

    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def compute_file_hash(self, file_path):
        """
        Compute SHA256 hash of file for duplicate detection.

        Args:
            file_path (str): Path to file

        Returns:
            str: SHA256 hash of file
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_duplicate(self, file_hash, data_source_id):
        """
        Check if file has been imported before.

        Args:
            file_hash (str): SHA256 hash of file
            data_source_id (int): ID of data source

        Returns:
            ImportBatch or None: Previous import batch if duplicate found
        """
        return ImportBatch.query.filter_by(
            file_hash=file_hash,
            data_source_id=data_source_id
        ).first()

    def read_file(self, file_path, field_mapping=None):
        """
        Read data from CSV or Excel file.

        Args:
            file_path (str): Path to file
            field_mapping (dict): Optional custom field mapping

        Returns:
            tuple: (list of records as dicts, list of column names)
        """
        file_ext = file_path.rsplit('.', 1)[1].lower()

        if field_mapping is None:
            field_mapping = self.DEFAULT_FIELD_MAPPING

        if file_ext == 'csv':
            return self._read_csv(file_path, field_mapping)
        elif file_ext in ['xlsx', 'xls']:
            return self._read_excel(file_path, field_mapping)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    def _read_csv(self, file_path, field_mapping):
        """Read CSV file"""
        records = []
        original_columns = []

        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(csvfile, delimiter=delimiter)
            original_columns = reader.fieldnames

            for row in reader:
                # Map CSV columns to database fields
                mapped_row = self._map_fields(row, field_mapping)
                if mapped_row:  # Skip empty rows
                    records.append(mapped_row)

        return records, original_columns

    def _read_excel(self, file_path, field_mapping):
        """Read Excel file"""
        df = pd.read_excel(file_path)
        original_columns = df.columns.tolist()

        records = []
        for _, row in df.iterrows():
            # Convert row to dict
            row_dict = row.to_dict()
            # Map Excel columns to database fields
            mapped_row = self._map_fields(row_dict, field_mapping)
            if mapped_row:  # Skip empty rows
                records.append(mapped_row)

        return records, original_columns

    def _map_fields(self, row, field_mapping):
        """
        Map file columns to database fields.

        Args:
            row (dict): Row data with file column names as keys
            field_mapping (dict): Mapping of file columns to database fields

        Returns:
            dict: Mapped row data
        """
        mapped_row = {}

        for file_col, db_field in field_mapping.items():
            if file_col in row:
                value = row[file_col]
                # Convert pandas NA/NaN to None
                if pd.isna(value):
                    value = None
                elif isinstance(value, str):
                    value = value.strip()
                    if value == '':
                        value = None
                mapped_row[db_field] = value

        # Only return row if it has at least one non-None value
        if any(v is not None for v in mapped_row.values()):
            return mapped_row
        return None

    def create_import_batch(self, file_path, file_name, data_source_id, user_id, field_mapping=None):
        """
        Create import batch record.

        Args:
            file_path (str): Path to uploaded file
            file_name (str): Original filename
            data_source_id (int): ID of data source
            user_id (int): ID of user performing import
            field_mapping (dict): Optional custom field mapping

        Returns:
            ImportBatch: Created import batch
        """
        file_size = os.path.getsize(file_path)
        file_hash = self.compute_file_hash(file_path)

        # Check for duplicate
        duplicate = self.check_duplicate(file_hash, data_source_id)
        if duplicate:
            raise ValueError(
                f"This file has already been imported (Batch ID: {duplicate.id}, "
                f"Date: {duplicate.import_date.strftime('%Y-%m-%d %H:%M')})"
            )

        self.import_batch = ImportBatch(
            data_source_id=data_source_id,
            file_name=file_name,
            file_path=file_path,
            file_size_bytes=file_size,
            file_hash=file_hash,
            imported_by_id=user_id,
            status='pending'
        )

        if field_mapping:
            self.import_batch.set_field_mapping(field_mapping)

        db.session.add(self.import_batch)
        db.session.commit()

        return self.import_batch

    def validate_data(self, records):
        """
        Validate imported data.

        Args:
            records (list): List of record dicts

        Returns:
            dict: Validation results
        """
        if not self.import_batch:
            raise ValueError("Import batch not created. Call create_import_batch() first.")

        self.import_batch.mark_as_validating()
        db.session.commit()

        # Validate all records
        validation_results = self.validator.validate_batch(records)

        # Store validation results
        self.import_batch.set_validation_errors(validation_results['errors'])
        self.import_batch.set_validation_warnings(validation_results['warnings'])
        self.import_batch.warnings_count = validation_results['warning_count']

        db.session.commit()

        return validation_results

    def import_data(self, records, validation_results):
        """
        Import validated data into database.

        Args:
            records (list): List of record dicts
            validation_results (dict): Results from validation

        Returns:
            dict: Import summary
        """
        if not self.import_batch:
            raise ValueError("Import batch not created. Call create_import_batch() first.")

        self.import_batch.mark_as_importing()
        self.import_batch.total_records = len(records)
        db.session.commit()

        successful = 0
        failed = 0
        skipped = 0

        # Track which records are valid (no errors)
        error_rows = {err['row'] for err in validation_results['errors']}

        for idx, record in enumerate(records, start=1):
            if idx in error_rows:
                # Skip records with errors
                failed += 1
                continue

            try:
                # Import the record
                self._import_record(record)
                successful += 1

            except Exception as e:
                failed += 1
                self.import_batch.add_log_entry(
                    f"Row {idx} import failed: {str(e)}",
                    level='error'
                )

        # Update batch statistics
        self.import_batch.successful_imports = successful
        self.import_batch.failed_imports = failed
        self.import_batch.skipped_records = skipped

        if failed == 0:
            self.import_batch.mark_as_completed()
        else:
            error_msg = f"{failed} record(s) failed to import"
            self.import_batch.mark_as_failed(error_msg)

        db.session.commit()

        return {
            'batch_id': self.import_batch.id,
            'total': len(records),
            'successful': successful,
            'failed': failed,
            'skipped': skipped
        }

    def _import_record(self, record):
        """
        Import a single record into database.

        Args:
            record (dict): Record data
        """
        # Get or create site
        site_name = record.get('site_name')
        site = None
        if site_name:
            site = Site.query.filter_by(name=site_name).first()
            if not site:
                # Create new site
                site = Site(
                    name=site_name,
                    location=record.get('location', 'Unknown')
                )
                db.session.add(site)
                db.session.flush()  # Get site.id

        # Create water sample
        sample = WaterSample(
            sample_id=record.get('sample_id'),
            site_id=site.id if site else None,
            collection_date=self._parse_date(record.get('collection_date')),
            analysis_date=self._parse_date(record.get('analysis_date')),
            notes=record.get('notes')
        )
        db.session.add(sample)
        db.session.flush()  # Get sample.id

        # Create test result
        test_result = TestResult(
            sample_id=sample.id,
            ph_value=self._to_float(record.get('ph_value')),
            temperature_c=self._to_float(record.get('temperature_c')),
            turbidity_ntu=self._to_float(record.get('turbidity_ntu')),
            arsenic_mg_l=self._to_float(record.get('arsenic_mg_l')),
            lead_mg_l=self._to_float(record.get('lead_mg_l')),
            iron_mg_l=self._to_float(record.get('iron_mg_l')),
            nitrate_mg_l=self._to_float(record.get('nitrate_mg_l')),
            fluoride_mg_l=self._to_float(record.get('fluoride_mg_l')),
            chloride_mg_l=self._to_float(record.get('chloride_mg_l')),
            sulfate_mg_l=self._to_float(record.get('sulfate_mg_l')),
            total_dissolved_solids_mg_l=self._to_float(record.get('total_dissolved_solids_mg_l')),
            hardness_mg_l=self._to_float(record.get('hardness_mg_l')),
            conductivity_us_cm=self._to_float(record.get('conductivity_us_cm')),
            dissolved_oxygen_mg_l=self._to_float(record.get('dissolved_oxygen_mg_l'))
        )
        db.session.add(test_result)

    def _parse_date(self, date_value):
        """Parse date from various formats"""
        if date_value is None or date_value == '':
            return None

        if isinstance(date_value, datetime):
            return date_value

        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%Y-%m-%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S'
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_value).strip(), fmt)
            except ValueError:
                continue

        return None

    def _to_float(self, value):
        """Convert value to float, return None if not possible"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def process_import(self, file_path, file_name, data_source_id, user_id, field_mapping=None):
        """
        Complete end-to-end import process.

        Args:
            file_path (str): Path to uploaded file
            file_name (str): Original filename
            data_source_id (int): ID of data source
            user_id (int): ID of user performing import
            field_mapping (dict): Optional custom field mapping

        Returns:
            dict: Complete import results
        """
        try:
            # Step 1: Create import batch
            self.create_import_batch(file_path, file_name, data_source_id, user_id, field_mapping)
            self.import_batch.mark_as_processing()
            db.session.commit()

            # Step 2: Read file
            records, columns = self.read_file(file_path, field_mapping)
            self.import_batch.set_data_preview(records)
            self.import_batch.add_log_entry(f"Read {len(records)} records from file")
            db.session.commit()

            # Step 3: Validate data
            validation_results = self.validate_data(records)
            self.import_batch.add_log_entry(
                f"Validation complete: {validation_results['valid']} valid, "
                f"{validation_results['invalid']} invalid, "
                f"{validation_results['warning_count']} warnings"
            )
            db.session.commit()

            # Step 4: Import data if validation passed
            if validation_results['invalid'] == 0:
                import_results = self.import_data(records, validation_results)
                return {
                    'success': True,
                    'batch_id': self.import_batch.id,
                    'validation': validation_results,
                    'import': import_results
                }
            else:
                # Validation failed
                self.import_batch.mark_as_failed("Validation errors detected")
                db.session.commit()
                return {
                    'success': False,
                    'batch_id': self.import_batch.id,
                    'validation': validation_results,
                    'message': 'Import failed due to validation errors'
                }

        except Exception as e:
            if self.import_batch:
                self.import_batch.mark_as_failed(str(e))
                db.session.commit()
            raise
