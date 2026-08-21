"""create priority and workflow tables and issue columns

Revision ID: 20260821_create_priority_and_workflow_tables
Revises: 20260821_create_image_classifications_table
Create Date: 2026-08-21 21:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260821_create_priority_and_workflow_tables'
down_revision: Union[str, None] = '20260821_create_image_classifications_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums if postgres
    authoritydepartment_enum = sa.Enum(
        'ROAD_DEPARTMENT',
        'ELECTRICAL_DEPARTMENT',
        'SANITATION_DEPARTMENT',
        'TRAFFIC_DEPARTMENT',
        'DRAINAGE_DEPARTMENT',
        'GENERAL_WORKS',
        name='authoritydepartment'
    )
    prioritylevel_enum = sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', name='prioritylevel')
    locationzone_enum = sa.Enum('HOSPITAL', 'SCHOOL', 'MAIN_ROAD', 'JUNCTION', 'RESIDENTIAL', 'OTHER', name='locationzone')
    trafficdensity_enum = sa.Enum('HEAVY', 'MEDIUM', 'LOW', name='trafficdensity')

    # Add columns to issues table
    op.add_column('issues', sa.Column('priority_level', prioritylevel_enum, nullable=False, server_default='LOW'))
    op.add_column('issues', sa.Column('traffic_density', trafficdensity_enum, nullable=False, server_default='MEDIUM'))
    op.add_column('issues', sa.Column('location_zone', locationzone_enum, nullable=False, server_default='RESIDENTIAL'))
    op.add_column('issues', sa.Column('assigned_department', authoritydepartment_enum, nullable=True))

    # 2. Create issue_assignments table
    op.create_table(
        'issue_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('department', authoritydepartment_enum, nullable=False),
        sa.Column('assigned_to_user_id', sa.UUID(), nullable=True),
        sa.Column('assigned_by_user_id', sa.UUID(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_issue_assignments_id'), 'issue_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_issue_assignments_issue_id'), 'issue_assignments', ['issue_id'], unique=False)

    # 3. Create issue_status_history table
    op.create_table(
        'issue_status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column(
            'previous_status',
            sa.Enum(
                'REPORTED', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'FIXED', 'CLOSED', 'REJECTED',
                name='reportstatus',
                create_type=False
            ),
            nullable=True
        ),
        sa.Column(
            'new_status',
            sa.Enum(
                'REPORTED', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'FIXED', 'CLOSED', 'REJECTED',
                name='reportstatus',
                create_type=False
            ),
            nullable=False
        ),
        sa.Column('changed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_issue_status_history_id'), 'issue_status_history', ['id'], unique=False)
    op.create_index(op.f('ix_issue_status_history_issue_id'), 'issue_status_history', ['issue_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_issue_status_history_issue_id'), table_name='issue_status_history')
    op.drop_index(op.f('ix_issue_status_history_id'), table_name='issue_status_history')
    op.drop_table('issue_status_history')

    op.drop_index(op.f('ix_issue_assignments_issue_id'), table_name='issue_assignments')
    op.drop_index(op.f('ix_issue_assignments_id'), table_name='issue_assignments')
    op.drop_table('issue_assignments')

    op.drop_column('issues', 'assigned_department')
    op.drop_column('issues', 'location_zone')
    op.drop_column('issues', 'traffic_density')
    op.drop_column('issues', 'priority_level')
