"""add lightcurve status fields

Revision ID: 9d96c23f0a7b
Revises: 15b5fd757927
Create Date: 2026-10-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d96c23f0a7b'
down_revision = '15b5fd757927'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('lightcurve', sa.Column('stable_status', sa.Boolean(), nullable=True))
    op.add_column(
        'lightcurve',
        sa.Column('status_prob', sa.Float(), server_default=sa.text('0'), nullable=False),
    )
    with op.batch_alter_table('lightcurve') as batch_op:
        batch_op.create_check_constraint(
            'ck_lightcurve_status_prob_range',
            'status_prob >= 0 AND status_prob <= 100',
        )


def downgrade():
    with op.batch_alter_table('lightcurve') as batch_op:
        batch_op.drop_constraint('ck_lightcurve_status_prob_range', type_='check')
    op.drop_column('lightcurve', 'status_prob')
    op.drop_column('lightcurve', 'stable_status')