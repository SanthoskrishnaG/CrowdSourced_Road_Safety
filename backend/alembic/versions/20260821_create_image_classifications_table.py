"""create image_classifications table

Revision ID: 20260821_create_image_classifications_table
Revises: 20260819_create_issues_table
Create Date: 2026-08-21 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260821_create_image_classifications_table'
down_revision: Union[str, None] = '20260819_create_issues_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'image_classifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=False),
        sa.Column(
            'predicted_category',
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
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False, server_default='road-vision-v1.0'),
        sa.Column('probabilities_json', sa.Text(), nullable=True),
        sa.Column(
            'user_suggested_category',
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
            nullable=True
        ),
        sa.Column(
            'authority_verified_category',
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
            nullable=True
        ),
        sa.Column('is_corrected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('corrected_by_user_id', sa.UUID(), nullable=True),
        sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correction_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['image_id'], ['report_images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_by_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_image_classifications_id'), 'image_classifications', ['id'], unique=False)
    op.create_index(op.f('ix_image_classifications_image_id'), 'image_classifications', ['image_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_image_classifications_image_id'), table_name='image_classifications')
    op.drop_index(op.f('ix_image_classifications_id'), table_name='image_classifications')
    op.drop_table('image_classifications')
