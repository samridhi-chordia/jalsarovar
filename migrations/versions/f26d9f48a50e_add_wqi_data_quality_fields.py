"""add_wqi_data_quality_fields

Revision ID: f26d9f48a50e
Revises: increase_sample_id_length
Create Date: 2025-12-22 16:17:23.942839

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f26d9f48a50e'
down_revision = 'increase_sample_id_length'
branch_labels = None
depends_on = None


def upgrade():
    # Add data quality fields to analyses table
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_coverage_pct', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('parameters_measured', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('key_parameters_measured', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('has_sufficient_data', sa.Boolean(),
                                      nullable=False, server_default='true'))
        batch_op.add_column(sa.Column('data_quality_tier', sa.String(20),
                                      nullable=True, server_default='full'))


def downgrade():
    # Remove data quality fields from analyses table
    with op.batch_alter_table('analyses', schema=None) as batch_op:
        batch_op.drop_column('data_quality_tier')
        batch_op.drop_column('has_sufficient_data')
        batch_op.drop_column('key_parameters_measured')
        batch_op.drop_column('parameters_measured')
        batch_op.drop_column('data_coverage_pct')
