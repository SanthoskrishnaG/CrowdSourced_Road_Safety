"""create issues table and issue_id column on reports

Revision ID: 20260819_create_issues_table
Revises: 20260819_create_report_images_and_accuracy
Create Date: 2026-08-19 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260819_create_issues_table'
down_revision: Union[str, None] = '20260819_create_report_images_and_accuracy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create issues table
    op.create_table(
        'issues',
        sa.Column('id', sa.UUID(), nullable=False),
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
                name='reportcategory',
                create_type=False
            ),
            nullable=False
        ),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column(
            'severity',
            sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='reportseverity', create_type=False),
            nullable=False
        ),
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
                name='reportstatus',
                create_type=False
            ),
            nullable=False
        ),
        sa.Column('priority_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('report_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_issues_id'), 'issues', ['id'], unique=False)

    # 2. Add issue_id column to reports table
    op.add_column('reports', sa.Column('issue_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_reports_issue_id'), 'reports', ['issue_id'], unique=False)
    op.create_foreign_key(
        'fk_reports_issue_id_issues',
        'reports',
        'issues',
        ['issue_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_reports_issue_id_issues', 'reports', type_='foreignkey')
    op.drop_index(op.f('ix_reports_issue_id'), table_name='reports')
    op.drop_column('reports', 'issue_id')
    op.drop_index(op.f('ix_issues_id'), table_name='issues')
    op.drop_table('issues')
