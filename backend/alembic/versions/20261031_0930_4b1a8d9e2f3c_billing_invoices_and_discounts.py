"""billing: invoices, invoice lines and discount usages

Revision ID: 4b1a8d9e2f3c
Revises: 1ee7f86311f8
Create Date: 2026-10-31 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b1a8d9e2f3c'
down_revision: Union[str, Sequence[str], None] = '1ee7f86311f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('number', sa.String(length=30), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'CONFIRMED', 'PAID', 'CANCELLED', name='invoice_status', native_enum=False, create_constraint=True, length=20),
            nullable=False,
        ),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='INR', nullable=False),
        sa.Column('amount_subtotal', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('amount_tax', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('amount_discount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('amount_total', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount_subtotal >= 0', name=op.f('ck_invoices_subtotal_non_negative')),
        sa.CheckConstraint('amount_tax >= 0', name=op.f('ck_invoices_tax_non_negative')),
        sa.CheckConstraint('amount_discount >= 0', name=op.f('ck_invoices_discount_non_negative')),
        sa.CheckConstraint('amount_total >= 0', name=op.f('ck_invoices_total_non_negative')),
        sa.CheckConstraint('amount_paid >= 0', name=op.f('ck_invoices_paid_non_negative')),
        sa.CheckConstraint('due_date >= issue_date', name=op.f('ck_invoices_dates_valid')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_invoices_customer_id_customers'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], name=op.f('fk_invoices_subscription_id_subscriptions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_invoices')),
        sa.UniqueConstraint('subscription_id', 'period_start', 'period_end', name=op.f('uq_invoices_subscription_period')),
    )
    op.create_index(op.f('ix_invoices_customer_id'), 'invoices', ['customer_id'], unique=False)
    op.create_index(op.f('ix_invoices_number'), 'invoices', ['number'], unique=True)
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)
    op.create_index('ix_invoices_status_due_date', 'invoices', ['status', 'due_date'], unique=False)

    op.create_table(
        'invoice_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('variant_id', sa.Integer(), nullable=True),
        sa.Column('tax_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=6, scale=3), server_default='0.000', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('line_type', sa.String(length=20), server_default='STANDARD', nullable=False),
        sa.CheckConstraint('quantity > 0', name=op.f('ck_invoice_lines_quantity_positive')),
        sa.CheckConstraint('unit_price >= 0', name=op.f('ck_invoice_lines_unit_price_non_negative')),
        sa.CheckConstraint('tax_rate >= 0', name=op.f('ck_invoice_lines_tax_rate_non_negative')),
        sa.CheckConstraint('tax_amount >= 0', name=op.f('ck_invoice_lines_tax_amount_non_negative')),
        sa.CheckConstraint('discount_amount >= 0', name=op.f('ck_invoice_lines_discount_amount_non_negative')),
        sa.CheckConstraint('amount >= 0', name=op.f('ck_invoice_lines_amount_non_negative')),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name=op.f('fk_invoice_lines_invoice_id_invoices'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_invoice_lines_product_id_products'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tax_id'], ['taxes.id'], name=op.f('fk_invoice_lines_tax_id_taxes'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], name=op.f('fk_invoice_lines_variant_id_product_variants'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_invoice_lines')),
    )
    op.create_index(op.f('ix_invoice_lines_invoice_id'), 'invoice_lines', ['invoice_id'], unique=False)

    op.create_table(
        'discount_usages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('discount_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('amount_applied', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount_applied >= 0', name=op.f('ck_discount_usages_amount_applied_non_negative')),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_discount_usages_customer_id_customers'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['discount_id'], ['discounts.id'], name=op.f('fk_discount_usages_discount_id_discounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name=op.f('fk_discount_usages_invoice_id_invoices'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_discount_usages')),
    )
    op.create_index(op.f('ix_discount_usages_customer_id'), 'discount_usages', ['customer_id'], unique=False)
    op.create_index(op.f('ix_discount_usages_discount_id'), 'discount_usages', ['discount_id'], unique=False)
    op.create_index(op.f('ix_discount_usages_invoice_id'), 'discount_usages', ['invoice_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_discount_usages_invoice_id'), table_name='discount_usages')
    op.drop_index(op.f('ix_discount_usages_discount_id'), table_name='discount_usages')
    op.drop_index(op.f('ix_discount_usages_customer_id'), table_name='discount_usages')
    op.drop_table('discount_usages')

    op.drop_index(op.f('ix_invoice_lines_invoice_id'), table_name='invoice_lines')
    op.drop_table('invoice_lines')

    op.drop_index('ix_invoices_status_due_date', table_name='invoices')
    op.drop_index(op.f('ix_invoices_subscription_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_customer_id'), table_name='invoices')
    op.drop_table('invoices')

