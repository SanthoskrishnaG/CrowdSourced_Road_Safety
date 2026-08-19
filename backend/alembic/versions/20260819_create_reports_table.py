"""create reports table

Revision ID: 20260819_create_reports_table
Revises: 20260819_create_users_table
Create Date: 2026-08-19 21:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260819_create_reports_table'
down_revision: Union[str, None] = '20260819_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column(
            'category',
            sa.Enum(
                'POTHOLE',
                'ROAD_DAMAGE',
                'BROKEN_STREETLIGHT',
                'BLOCKED_ROAD',
                'GARBAGE',
                'FLOODING',
                'DAMAGED_SIGN',
                'OBSTRUCTION',
                'OTHER',
                name='reportcategory'
            ),
            nullable=False
        ),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'severity',
            sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='reportseverity'),
            nullable=False
        ),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'REPORTED',
                'VERIFIED',
                'ASSIGNED',
                'IN_PROGRESS',
                'FIXED',
                'CLOSED',
                'REJECTED',
                name='reportstatus'
            ),
            nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')
