"""create_health_tables

Revision ID: 0003_health_tables
Revises: 0002_finance_transactions
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_health_tables'
down_revision: Union[str, None] = '0002_finance_transactions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create health_profiles table
    op.create_table(
        'health_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('daily_calorie_target', sa.Integer(), nullable=False, server_default='2000'),
        sa.Column('target_is_provisional', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('height_cm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('activity_level', sa.String(length=50), nullable=True),
        sa.Column('dietary_preferences', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('daily_calorie_target > 0', name='check_positive_calorie_target'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create health_meals table
    op.create_table(
        'health_meals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'meal_type',
            sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', 'breakfast', 'lunch', 'dinner', 'snack', name='meal_type_enum'),
            nullable=False
        ),
        sa.Column('food_items', sa.Text(), nullable=False),
        sa.Column('portion_notes', sa.Text(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=False),
        sa.Column('protein_g', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('carbs_g', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('fat_g', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('meal_date', sa.Date(), nullable=False),
        sa.Column('meal_time', sa.String(length=8), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_estimated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('estimation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('calories >= 0', name='check_non_negative_calories'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_health_meals_id', 'health_meals', ['id'])
    op.create_index('ix_health_meals_type', 'health_meals', ['meal_type'])
    op.create_index('ix_health_meals_date', 'health_meals', ['meal_date'])
    op.create_index('ix_health_meals_date_type', 'health_meals', ['meal_date', 'meal_type'])


def downgrade() -> None:
    op.drop_index('ix_health_meals_date_type', table_name='health_meals')
    op.drop_index('ix_health_meals_date', table_name='health_meals')
    op.drop_index('ix_health_meals_type', table_name='health_meals')
    op.drop_index('ix_health_meals_id', table_name='health_meals')
    op.drop_table('health_meals')
    op.drop_table('health_profiles')

    # Drop enum if on postgres
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='meal_type_enum').drop(bind, checkfirst=True)
