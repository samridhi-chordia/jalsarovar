"""Role Permission model for granular access control"""
from app import db


class RolePermission(db.Model):
    """Defines permissions for each user role"""
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(30), nullable=False, unique=True, index=True)

    # View Permissions
    can_view_sites = db.Column(db.Boolean, default=True)
    can_view_samples = db.Column(db.Boolean, default=True)
    can_view_test_results = db.Column(db.Boolean, default=False)
    can_view_analysis = db.Column(db.Boolean, default=False)
    can_export_data = db.Column(db.Boolean, default=False)

    # Create/Edit Permissions
    can_create_sites = db.Column(db.Boolean, default=False)
    can_edit_sites = db.Column(db.Boolean, default=False)
    can_delete_sites = db.Column(db.Boolean, default=False)

    can_create_samples = db.Column(db.Boolean, default=False)
    can_edit_samples = db.Column(db.Boolean, default=False)
    can_delete_samples = db.Column(db.Boolean, default=False)

    can_submit_test_results = db.Column(db.Boolean, default=False)
    can_edit_test_results = db.Column(db.Boolean, default=False)
    can_delete_test_results = db.Column(db.Boolean, default=False)

    # Visual Observations
    can_submit_visual_observations = db.Column(db.Boolean, default=False)
    can_edit_visual_observations = db.Column(db.Boolean, default=False)

    # ML & Analysis
    can_run_ml_models = db.Column(db.Boolean, default=False)
    can_create_analysis = db.Column(db.Boolean, default=False)
    can_view_ml_predictions = db.Column(db.Boolean, default=False)

    # Admin Functions
    can_manage_users = db.Column(db.Boolean, default=False)
    can_approve_roles = db.Column(db.Boolean, default=False)
    can_approve_submissions = db.Column(db.Boolean, default=False)
    can_bulk_import = db.Column(db.Boolean, default=False)
    can_manage_system = db.Column(db.Boolean, default=False)

    # Data Scope
    data_scope = db.Column(db.String(20), default='public', nullable=False)
    # Options: 'all', 'assigned', 'own', 'public'

    def __repr__(self):
        return f'<RolePermission {self.role}>'

    @staticmethod
    def seed_permissions():
        """Seed default permissions for all 10 roles"""
        permissions = [
            # Viewer - Read-only access to public data
            {
                'role': 'viewer',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': False,
                'can_view_analysis': False,
                'can_export_data': False,
                'data_scope': 'public'
            },

            # Citizen Contributor - Submit visual observations
            {
                'role': 'citizen_contributor',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_submit_visual_observations': True,
                'can_edit_visual_observations': True,
                'data_scope': 'public'
            },

            # Researcher - Access all data for research
            {
                'role': 'researcher',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_view_analysis': True,
                'can_view_ml_predictions': True,
                'can_export_data': True,
                'data_scope': 'all'
            },

            # Field Collector - Collect samples and observations
            {
                'role': 'field_collector',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_create_sites': True,
                'can_create_samples': True,
                'can_edit_samples': True,
                'can_submit_visual_observations': True,
                'data_scope': 'all'
            },

            # Analyst - Data analysis and ML models
            {
                'role': 'analyst',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_view_analysis': True,
                'can_view_ml_predictions': True,
                'can_run_ml_models': True,
                'can_create_analysis': True,
                'can_export_data': True,
                'data_scope': 'all'
            },

            # Lab Partner - Submit and manage test results
            {
                'role': 'lab_partner',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_submit_test_results': True,
                'can_edit_test_results': True,
                'can_delete_test_results': True,
                'data_scope': 'assigned'
            },

            # Industry Partner - Monitor compliance for assigned sites
            {
                'role': 'industry_partner',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_create_samples': True,
                'can_submit_visual_observations': True,
                'data_scope': 'assigned'
            },

            # Government Official - Official monitoring and reporting
            {
                'role': 'government_official',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_view_analysis': True,
                'can_view_ml_predictions': True,
                'can_run_ml_models': True,
                'can_export_data': True,
                'can_approve_submissions': True,
                'data_scope': 'all'
            },

            # Site Manager - Manage assigned water body sites
            {
                'role': 'site_manager',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_edit_sites': True,
                'can_create_samples': True,
                'can_edit_samples': True,
                'can_submit_visual_observations': True,
                'data_scope': 'assigned'
            },

            # Admin - Full system access
            {
                'role': 'admin',
                'can_view_sites': True,
                'can_view_samples': True,
                'can_view_test_results': True,
                'can_view_analysis': True,
                'can_view_ml_predictions': True,
                'can_export_data': True,
                'can_create_sites': True,
                'can_edit_sites': True,
                'can_delete_sites': True,
                'can_create_samples': True,
                'can_edit_samples': True,
                'can_delete_samples': True,
                'can_submit_test_results': True,
                'can_edit_test_results': True,
                'can_delete_test_results': True,
                'can_submit_visual_observations': True,
                'can_edit_visual_observations': True,
                'can_run_ml_models': True,
                'can_create_analysis': True,
                'can_manage_users': True,
                'can_approve_roles': True,
                'can_approve_submissions': True,
                'can_bulk_import': True,
                'can_manage_system': True,
                'data_scope': 'all'
            }
        ]

        for perm_data in permissions:
            # Check if permission already exists
            existing = RolePermission.query.filter_by(role=perm_data['role']).first()
            if not existing:
                perm = RolePermission(**perm_data)
                db.session.add(perm)

        db.session.commit()
        print(f"Seeded permissions for {len(permissions)} roles")
