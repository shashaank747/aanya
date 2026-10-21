"""create_finance_transactions

Revision ID: 0002_finance_transactions
Revises: 0001_initial_baseline
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_finance_transactions'
down_revision: Union[str, None] = '0001_initial_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create finance_transactions table with NUMERIC(12, 2) precision
    op.create_table(
        'finance_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.Enum('INCOME', 'EXPENSE', 'income', 'expense', name='transaction_type_enum'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False, server_default='UPI'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('amount > 0', name='check_positive_amount'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_finance_transactions_id', 'finance_transactions', ['id'])
    op.create_index('ix_finance_transactions_type', 'finance_transactions', ['type'])
    op.create_index('ix_finance_transactions_category', 'finance_transactions', ['category'])
    op.create_index('ix_finance_transactions_date', 'finance_transactions', ['transaction_date'])
    op.create_index('ix_finance_tx_date_type', 'finance_transactions', ['transaction_date', 'type'])


def downgrade() -> None:
    op.drop_index('ix_finance_tx_date_type', table_name='finance_transactions')
    op.drop_index('ix_finance_transactions_date', table_name='finance_transactions')
    op.drop_index('ix_finance_transactions_category', table_name='finance_transactions')
    op.drop_index('ix_finance_transactions_type', table_name='finance_transactions')
    op.drop_index('ix_finance_transactions_id', table_name='finance_transactions')
    op.drop_table('finance_transactions')
    
    # Drop enum if on postgres
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='transaction_type_enum').drop(bind, checkfirst=True)
