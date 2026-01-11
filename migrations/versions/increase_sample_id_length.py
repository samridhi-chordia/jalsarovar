"""Increase sample_id length from 50 to 100 characters

Revision ID: increase_sample_id_length
Revises: add_country_to_sites
Create Date: 2025-12-20 12:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'increase_sample_id_length'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Increase sample_id length to accommodate longer USGS ActivityIdentifiers"""
    with op.batch_alter_table('water_samples', schema=None) as batch_op:
        batch_op.alter_column('sample_id',
                              existing_type=sa.String(50),
                              type_=sa.String(100),
                              existing_nullable=False)


def downgrade():
    """Revert sample_id length back to 50 characters"""
    with op.batch_alter_table('water_samples', schema=None) as batch_op:
        batch_op.alter_column('sample_id',
                              existing_type=sa.String(100),
                              type_=sa.String(50),
                              existing_nullable=False)
