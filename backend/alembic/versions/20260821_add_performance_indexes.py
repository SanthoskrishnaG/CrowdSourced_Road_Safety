"""add_performance_indexes

Revision ID: 20260821_add_performance_indexes
Revises: 20260821_create_priority_and_workflow_tables
Create Date: 2026-08-21 22:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260821_add_performance_indexes'
down_revision: Union[str, None] = '20260821_create_priority_and_workflow_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indexes on issues table
    op.create_index('idx_issues_lat_long', 'issues', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_issues_status_priority', 'issues', ['status', 'priority_level'], unique=False)
    op.create_index('ix_issues_category', 'issues', ['category'], unique=False)
    op.create_index('ix_issues_severity', 'issues', ['severity'], unique=False)
    op.create_index('ix_issues_status', 'issues', ['status'], unique=False)
    op.create_index('ix_issues_priority_score', 'issues', ['priority_score'], unique=False)
    op.create_index('ix_issues_priority_level', 'issues', ['priority_level'], unique=False)
    op.create_index('ix_issues_assigned_department', 'issues', ['assigned_department'], unique=False)
    op.create_index('ix_issues_created_at', 'issues', ['created_at'], unique=False)

    # Indexes on reports table
    op.create_index('idx_reports_lat_long', 'reports', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_reports_status_created', 'reports', ['status', 'created_at'], unique=False)
    op.create_index('ix_reports_category', 'reports', ['category'], unique=False)
    op.create_index('ix_reports_severity', 'reports', ['severity'], unique=False)
    op.create_index('ix_reports_status', 'reports', ['status'], unique=False)
    op.create_index('ix_reports_created_at', 'reports', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes on reports
    op.drop_index('ix_reports_created_at', table_name='reports')
    op.drop_index('ix_reports_status', table_name='reports')
    op.drop_index('ix_reports_severity', table_name='reports')
    op.drop_index('ix_reports_category', table_name='reports')
    op.drop_index('idx_reports_status_created', table_name='reports')
    op.drop_index('idx_reports_lat_long', table_name='reports')

    # Drop indexes on issues
    op.drop_index('ix_issues_created_at', table_name='issues')
    op.drop_index('ix_issues_assigned_department', table_name='issues')
    op.drop_index('ix_issues_priority_level', table_name='issues')
    op.drop_index('ix_issues_priority_score', table_name='issues')
    op.drop_index('ix_issues_status', table_name='issues')
    op.drop_index('ix_issues_severity', table_name='issues')
    op.drop_index('ix_issues_category', table_name='issues')
    op.drop_index('idx_issues_status_priority', table_name='issues')
    op.drop_index('idx_issues_lat_long', table_name='issues')
