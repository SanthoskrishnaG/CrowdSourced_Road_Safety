"""create report_images and location_accuracy

Revision ID: 20260819_create_report_images_and_accuracy
Revises: 20260819_create_reports_table
Create Date: 2026-08-19 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260819_create_report_images_and_accuracy'
down_revision: Union[str, None] = '20260819_create_reports_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add location_accuracy column to reports
    op.add_column('reports', sa.Column('location_accuracy', sa.Float(), nullable=True))

    # Create report_images table
    op.create_table(
        'report_images',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('report_id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_images_id'), 'report_images', ['id'], unique=False)
    op.create_index(op.f('ix_report_images_report_id'), 'report_images', ['report_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_images_report_id'), table_name='report_images')
    op.drop_index(op.f('ix_report_images_id'), table_name='report_images')
    op.drop_table('report_images')
    op.drop_column('reports', 'location_accuracy')
