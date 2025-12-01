"""
Data Source Model
Tracks external sources of water quality data for import functionality
"""
from datetime import datetime
from app import db


class DataSource(db.Model):
    """
    Represents an external data source for importing water quality data.

    Examples: IIT Madras Water Lab, Local Testing Lab, WHO India Dataset,
              Government Health Department, Research Institution
    """
    __tablename__ = 'data_sources'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Basic Information
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)

    # Source Classification
    source_type = db.Column(db.String(50), nullable=False)  # lab, research_institution, government_agency, ngo, who_glaas

    # Contact Information
    contact_person = db.Column(db.String(200))
    contact_email = db.Column(db.String(200))
    contact_phone = db.Column(db.String(50))
    organization = db.Column(db.String(200))
    website = db.Column(db.String(500))

    # Data Format Information
    data_format_description = db.Column(db.Text)  # Human-readable description of format
    expected_file_format = db.Column(db.String(50))  # csv, xlsx, json, xml
    has_custom_parser = db.Column(db.Boolean, default=False)  # True if requires special parsing logic
    parser_name = db.Column(db.String(100))  # Name of parser class to use

    # Source Metadata (JSON)
    source_metadata = db.Column(db.Text)  # JSON string for flexible additional data

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_trusted = db.Column(db.Boolean, default=False)  # Pre-validated, skip some checks

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    import_batches = db.relationship('ImportBatch', backref='data_source', lazy='dynamic', cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<DataSource {self.name}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'source_type': self.source_type,
            'organization': self.organization,
            'contact_email': self.contact_email,
            'data_format': self.expected_file_format,
            'is_active': self.is_active,
            'is_trusted': self.is_trusted,
            'import_count': self.import_batches.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @property
    def total_imports(self):
        """Total number of import batches from this source"""
        return self.import_batches.count()

    @property
    def successful_imports(self):
        """Number of successful import batches"""
        return self.import_batches.filter_by(status='completed').count()

    @property
    def total_records_imported(self):
        """Total number of records imported from this source"""
        from app.models.import_batch import ImportBatch
        result = db.session.query(db.func.sum(ImportBatch.successful_imports))\
            .filter(ImportBatch.data_source_id == self.id)\
            .scalar()
        return result or 0

    @staticmethod
    def get_source_types():
        """Return list of valid source types"""
        return [
            ('lab', 'Testing Laboratory'),
            ('research_institution', 'Research Institution (e.g., IIT)'),
            ('government_agency', 'Government Agency'),
            ('ngo', 'NGO / Non-Profit'),
            ('who_glaas', 'WHO GLAAS Dataset'),
            ('other', 'Other Source')
        ]

    @staticmethod
    def get_file_formats():
        """Return list of supported file formats"""
        return [
            ('csv', 'CSV (Comma-Separated Values)'),
            ('xlsx', 'Excel (.xlsx)'),
            ('xls', 'Excel Legacy (.xls)'),
            ('json', 'JSON'),
            ('xml', 'XML')
        ]
