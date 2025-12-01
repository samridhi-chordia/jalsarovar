"""
Import Batch Model
Tracks each data import operation with validation results and statistics
"""
from datetime import datetime
from app import db
import json


class ImportBatch(db.Model):
    """
    Represents a single data import operation.

    Tracks the import process from file upload through validation and
    final import with detailed statistics and error tracking.
    """
    __tablename__ = 'import_batches'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Source Information
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False)

    # File Information
    file_name = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000))  # Server path to uploaded file
    file_size_bytes = db.Column(db.Integer)
    file_hash = db.Column(db.String(64))  # SHA256 hash for duplicate detection

    # Import Metadata
    import_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    imported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Import Statistics
    total_records = db.Column(db.Integer, default=0)  # Total rows in file
    successful_imports = db.Column(db.Integer, default=0)  # Successfully imported
    failed_imports = db.Column(db.Integer, default=0)  # Failed validation/import
    skipped_records = db.Column(db.Integer, default=0)  # Duplicates or intentionally skipped
    warnings_count = db.Column(db.Integer, default=0)  # Non-fatal issues

    # Validation & Error Tracking
    validation_errors = db.Column(db.Text)  # JSON string of errors
    validation_warnings = db.Column(db.Text)  # JSON string of warnings
    import_log = db.Column(db.Text)  # Detailed log of import process

    # Status
    status = db.Column(
        db.String(50),
        nullable=False,
        default='pending'
    )  # pending, processing, validating, importing, completed, failed, rolled_back

    # Field Mapping (for CSV/Excel imports)
    field_mapping = db.Column(db.Text)  # JSON mapping of file columns to database fields

    # Rollback capability
    can_rollback = db.Column(db.Boolean, default=True)
    rolled_back_at = db.Column(db.DateTime)
    rolled_back_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Data Preview (first 5 rows for review)
    data_preview = db.Column(db.Text)  # JSON string

    # Performance Metrics
    processing_time_seconds = db.Column(db.Float)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    imported_by = db.relationship('User', foreign_keys=[imported_by_id], backref='imports_created')
    rolled_back_by = db.relationship('User', foreign_keys=[rolled_back_by_id])

    def __repr__(self):
        return f'<ImportBatch {self.id}: {self.file_name} ({self.status})>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'data_source': self.data_source.name if self.data_source else None,
            'file_name': self.file_name,
            'import_date': self.import_date.isoformat() if self.import_date else None,
            'imported_by': self.imported_by.full_name if self.imported_by else None,
            'status': self.status,
            'total_records': self.total_records,
            'successful_imports': self.successful_imports,
            'failed_imports': self.failed_imports,
            'skipped_records': self.skipped_records,
            'warnings_count': self.warnings_count,
            'success_rate': self.success_rate,
            'can_rollback': self.can_rollback and self.status == 'completed',
            'processing_time': self.processing_time_seconds,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.total_records == 0:
            return 0
        return round((self.successful_imports / self.total_records) * 100, 2)

    @property
    def is_in_progress(self):
        """Check if import is currently running"""
        return self.status in ['processing', 'validating', 'importing']

    @property
    def is_complete(self):
        """Check if import has finished (successfully or with errors)"""
        return self.status in ['completed', 'failed']

    @property
    def duration(self):
        """Get human-readable duration"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        duration = end_time - self.started_at
        return str(duration).split('.')[0]  # Remove microseconds

    def get_validation_errors(self):
        """Parse and return validation errors as list"""
        if not self.validation_errors:
            return []
        try:
            return json.loads(self.validation_errors)
        except:
            return []

    def set_validation_errors(self, errors_list):
        """Store validation errors as JSON"""
        self.validation_errors = json.dumps(errors_list, indent=2)

    def get_validation_warnings(self):
        """Parse and return validation warnings as list"""
        if not self.validation_warnings:
            return []
        try:
            return json.loads(self.validation_warnings)
        except:
            return []

    def set_validation_warnings(self, warnings_list):
        """Store validation warnings as JSON"""
        self.validation_warnings = json.dumps(warnings_list, indent=2)

    def get_field_mapping(self):
        """Parse and return field mapping as dict"""
        if not self.field_mapping:
            return {}
        try:
            return json.loads(self.field_mapping)
        except:
            return {}

    def set_field_mapping(self, mapping_dict):
        """Store field mapping as JSON"""
        self.field_mapping = json.dumps(mapping_dict, indent=2)

    def get_data_preview(self):
        """Parse and return data preview"""
        if not self.data_preview:
            return []
        try:
            return json.loads(self.data_preview)
        except:
            return []

    def set_data_preview(self, preview_data):
        """Store first few rows of data for preview"""
        self.data_preview = json.dumps(preview_data[:5], indent=2)  # Store first 5 rows

    def add_log_entry(self, message, level='info'):
        """Add entry to import log"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"

        if self.import_log:
            self.import_log += log_entry
        else:
            self.import_log = log_entry

    def mark_as_processing(self):
        """Update status to processing"""
        self.status = 'processing'
        self.started_at = datetime.utcnow()
        self.add_log_entry("Import processing started")

    def mark_as_validating(self):
        """Update status to validating"""
        self.status = 'validating'
        self.add_log_entry("Data validation started")

    def mark_as_importing(self):
        """Update status to importing"""
        self.status = 'importing'
        self.add_log_entry("Data import to database started")

    def mark_as_completed(self):
        """Update status to completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.processing_time_seconds = duration.total_seconds()

        self.add_log_entry(
            f"Import completed successfully. {self.successful_imports}/{self.total_records} records imported."
        )

    def mark_as_failed(self, error_message):
        """Update status to failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.processing_time_seconds = duration.total_seconds()

        self.add_log_entry(f"Import failed: {error_message}", level='error')

    def rollback(self, user_id):
        """Mark import as rolled back"""
        if not self.can_rollback:
            raise ValueError("This import cannot be rolled back")

        if self.status != 'completed':
            raise ValueError("Only completed imports can be rolled back")

        self.status = 'rolled_back'
        self.rolled_back_at = datetime.utcnow()
        self.rolled_back_by_id = user_id
        self.can_rollback = False
        self.add_log_entry("Import rolled back by user", level='warning')

    @staticmethod
    def get_status_choices():
        """Return list of valid status values"""
        return [
            ('pending', 'Pending'),
            ('processing', 'Processing File'),
            ('validating', 'Validating Data'),
            ('validation_failed', 'Validation Failed'),
            ('importing', 'Importing to Database'),
            ('completed', 'Completed Successfully'),
            ('failed', 'Failed'),
            ('rolled_back', 'Rolled Back')
        ]

    @staticmethod
    def get_status_color(status):
        """Get Bootstrap color class for status"""
        colors = {
            'pending': 'secondary',
            'processing': 'info',
            'validating': 'info',
            'validation_failed': 'warning',
            'importing': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'rolled_back': 'warning'
        }
        return colors.get(status, 'secondary')
