"""Data Import Models - DataSource and ImportBatch for tracking data imports"""
from datetime import datetime
import json
from app import db


class DataSource(db.Model):
    """Data source for water quality imports"""
    __tablename__ = 'data_sources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    source_type = db.Column(db.String(50), nullable=False)  # cpcb, state_board, field_team, iot_sensor, manual

    # Contact information
    contact_person = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    organization = db.Column(db.String(200))
    website = db.Column(db.String(200))

    # Data format information
    data_format_description = db.Column(db.Text)
    expected_file_format = db.Column(db.String(20))  # csv, xlsx, xls

    # Parser configuration
    has_custom_parser = db.Column(db.Boolean, default=False)
    parser_name = db.Column(db.String(100))

    # Trust level
    is_trusted = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    import_batches = db.relationship('ImportBatch', backref='data_source', lazy='dynamic')

    @property
    def total_imports(self):
        """Total number of imports from this source"""
        return self.import_batches.count()

    @property
    def total_records_imported(self):
        """Total records imported from this source"""
        return db.session.query(db.func.sum(ImportBatch.successful_imports)).filter(
            ImportBatch.data_source_id == self.id,
            ImportBatch.status == 'completed'
        ).scalar() or 0

    @staticmethod
    def get_source_types():
        """Get available source types"""
        return [
            ('cpcb', 'CPCB (Central Pollution Control Board)'),
            ('state_board', 'State Pollution Control Board'),
            ('field_team', 'Field Team Collection'),
            ('iot_sensor', 'IoT Sensor Data'),
            ('manual', 'Manual Entry'),
            ('research', 'Research Institution'),
            ('other', 'Other')
        ]

    @staticmethod
    def get_file_formats():
        """Get supported file formats"""
        return [
            ('csv', 'CSV (Comma-Separated Values)'),
            ('xlsx', 'Excel (.xlsx)'),
            ('xls', 'Excel (.xls)')
        ]

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'source_type': self.source_type,
            'organization': self.organization,
            'is_trusted': self.is_trusted,
            'is_active': self.is_active,
            'total_imports': self.total_imports,
            'total_records_imported': self.total_records_imported
        }

    def __repr__(self):
        return f'<DataSource {self.name}>'


class ImportBatch(db.Model):
    """Import batch for tracking data imports"""
    __tablename__ = 'import_batches'

    id = db.Column(db.Integer, primary_key=True)
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False)

    # File information
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_size_bytes = db.Column(db.Integer)
    file_hash = db.Column(db.String(64))  # SHA-256 hash

    # Import metadata
    imported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    import_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Processing status
    status = db.Column(db.String(20), default='pending')  # pending, validating, importing, completed, failed, rolled_back

    # Record counts
    total_records = db.Column(db.Integer, default=0)
    successful_imports = db.Column(db.Integer, default=0)
    failed_imports = db.Column(db.Integer, default=0)
    warnings_count = db.Column(db.Integer, default=0)

    # Validation results (stored as JSON)
    validation_errors = db.Column(db.Text)  # JSON array of errors
    validation_warnings = db.Column(db.Text)  # JSON array of warnings

    # Data preview (first few rows as JSON)
    data_preview = db.Column(db.Text)

    # Processing time
    processing_start = db.Column(db.DateTime)
    processing_end = db.Column(db.DateTime)

    # Processing log (JSON array of log entries)
    processing_log = db.Column(db.Text, default='[]')

    # Rollback support
    can_rollback = db.Column(db.Boolean, default=True)
    rolled_back_at = db.Column(db.DateTime)
    rolled_back_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    imported_by = db.relationship('User', foreign_keys=[imported_by_id])
    rolled_back_by = db.relationship('User', foreign_keys=[rolled_back_by_id])

    @property
    def processing_time_seconds(self):
        """Calculate processing time in seconds"""
        if self.processing_start and self.processing_end:
            return (self.processing_end - self.processing_start).total_seconds()
        return None

    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.total_records == 0:
            return 0
        return (self.successful_imports / self.total_records) * 100

    @property
    def is_in_progress(self):
        """Check if import is in progress"""
        return self.status in ('validating', 'importing')

    @property
    def is_complete(self):
        """Check if import is complete"""
        return self.status in ('completed', 'failed', 'rolled_back')

    def get_errors(self):
        """Get validation errors as list"""
        if self.validation_errors:
            try:
                return json.loads(self.validation_errors)
            except:
                return []
        return []

    def get_warnings(self):
        """Get validation warnings as list"""
        if self.validation_warnings:
            try:
                return json.loads(self.validation_warnings)
            except:
                return []
        return []

    def get_log(self):
        """Get processing log as list"""
        if self.processing_log:
            try:
                return json.loads(self.processing_log)
            except:
                return []
        return []

    def add_log_entry(self, message):
        """Add entry to processing log"""
        log = self.get_log()
        log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'message': message
        })
        self.processing_log = json.dumps(log)

    def rollback(self, user_id):
        """Mark batch as rolled back"""
        if not self.can_rollback:
            raise ValueError("This batch cannot be rolled back")
        if self.status != 'completed':
            raise ValueError("Only completed imports can be rolled back")

        self.status = 'rolled_back'
        self.rolled_back_at = datetime.utcnow()
        self.rolled_back_by_id = user_id
        self.add_log_entry(f"Import rolled back by user {user_id}")

    @staticmethod
    def get_status_choices():
        """Get available status choices"""
        return [
            ('pending', 'Pending'),
            ('validating', 'Validating'),
            ('importing', 'Importing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('validation_failed', 'Validation Failed'),
            ('rolled_back', 'Rolled Back')
        ]

    def __repr__(self):
        return f'<ImportBatch {self.id}: {self.file_name}>'
