"""Billing calculation engine: taxes, discounts and line pricing.

Ensures no float math, strict Decimal precision, and correct inclusive/exclusive tax handling.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import (
    Discount,
    DiscountTarget,
    DiscountType,
    Product,
    ProductVariant,
    Tax,
)
from app.models.subscriptions import Subscription, SubscriptionLine

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def quantize_money(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP."""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class CalculatedLine:
    description: str
    quantity: int
    unit_price: Decimal
    product_id: int | None
    variant_id: int | None
    tax_id: int | None
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    amount: Decimal
    line_type: str = "STANDARD"


@dataclass
class CalculationResult:
    lines: list[CalculatedLine] = field(default_factory=list)
    amount_subtotal: Decimal = ZERO
    amount_tax: Decimal = ZERO
    amount_discount: Decimal = ZERO
    amount_total: Decimal = ZERO
    applied_discounts: list[tuple[Discount, Decimal]] = field(default_factory=list)


def compute_tax(
    amount: Decimal,
    percentage: Decimal,
    inclusive: bool,
) -> tuple[Decimal, Decimal]:
    """Compute (pre_tax_base, tax_amount) given an amount and a tax percentage.

    If exclusive:
        base = amount
        tax = quantize(amount * (percentage / 100))
    If inclusive:
        rate = 1 + (percentage / 100)
        base = quantize(amount / rate)
        tax = amount - base
    """
    if percentage <= ZERO:
        return amount, ZERO

    pct_factor = percentage / Decimal("100")
    if inclusive:
        base = quantize_money(amount / (Decimal("1") + pct_factor))
        tax = quantize_money(amount - base)
        return base, tax
    else:
        tax = quantize_money(amount * pct_factor)
        return amount, tax


def find_applicable_discounts(
    db: Session,
    as_of_date: date,
    subtotal: Decimal,
    total_qty: int,
) -> list[Discount]:
    """Return all active, valid discount rules that qualify based on date, purchase, and usage."""
    query = (
        select(Discount)
        .where(
            Discount.start_date <= as_of_date,
            Discount.end_date >= as_of_date,
            Discount.min_purchase_amount <= subtotal,
            Discount.min_quantity <= total_qty,
        )
        .order_by(Discount.id)
    )
    discounts = list(db.scalars(query).all())
    # Filter out rules whose usage limit has been reached
    valid = []
    for d in discounts:
        if d.usage_limit > 0 and d.usage_count >= d.usage_limit:
            continue
        valid.append(d)
    return valid


def calculate_subscription_invoice(
    db: Session,
    subscription: Subscription,
    as_of_date: date,
) -> CalculationResult:
    """Calculate line items, taxes, discounts, and totals for a subscription."""
    calculated_lines: list[CalculatedLine] = []
    subtotal_sum = ZERO
    tax_sum = ZERO
    discount_sum = ZERO

    # 1. Calculate raw lines with products and variants
    total_qty = sum(line.quantity for line in subscription.lines)
    preliminary_subtotal = ZERO

    for line in subscription.lines:
        product = db.get(Product, line.product_id) if line.product_id else None
        variant = db.get(ProductVariant, line.variant_id) if line.variant_id else None
        tax = db.get(Tax, line.tax_id) if line.tax_id else None

        prod_name = product.name if product else "Subscription Line"
        var_name = f" ({variant.value})" if variant else ""
        desc = f"{prod_name}{var_name}"

        unit_price = line.unit_price
        line_base = quantize_money(unit_price * line.quantity)
        preliminary_subtotal += line_base

    # 2. Check applicable discounts
    discounts = find_applicable_discounts(db, as_of_date, preliminary_subtotal, total_qty)

    applied_discounts: list[tuple[Discount, Decimal]] = []
    product_discounts: dict[int, Decimal] = {}  # product_id -> discount_amount
    subscription_discounts: list[Discount] = []

    for d in discounts:
        if d.target == DiscountTarget.PRODUCT:
            for p in d.products:
                if d.type == DiscountType.PERCENTAGE:
                    product_discounts[p.id] = d.value
                else:
                    product_discounts[p.id] = d.value
            applied_discounts.append((d, ZERO))
        else:
            subscription_discounts.append(d)

    # 3. Process lines with taxes and product-level discounts
    for line in subscription.lines:
        product = db.get(Product, line.product_id) if line.product_id else None
        variant = db.get(ProductVariant, line.variant_id) if line.variant_id else None
        tax = db.get(Tax, line.tax_id) if line.tax_id else None

        prod_name = product.name if product else "Subscription Item"
        var_name = f" ({variant.value})" if variant else ""
        desc = f"{prod_name}{var_name}"

        unit_price = line.unit_price
        raw_amount = quantize_money(unit_price * line.quantity)

        # Apply product discount if any
        line_discount = ZERO
        if product and product.id in product_discounts:
            disc_val = product_discounts[product.id]
            # If percentage
            disc_pct = disc_val / Decimal("100")
            line_discount = quantize_money(raw_amount * disc_pct)
            if line_discount > raw_amount:
                line_discount = raw_amount

        net_line = raw_amount - line_discount

        # Compute tax on net line
        tax_rate = tax.percentage if tax else ZERO
        tax_amount = ZERO
        if tax and tax_rate > ZERO:
            _, tax_amount = compute_tax(net_line, tax_rate, tax.inclusive)

        final_line_amount = (net_line + tax_amount) if (tax and not tax.inclusive) else net_line

        subtotal_sum += raw_amount
        discount_sum += line_discount
        tax_sum += tax_amount

        calculated_lines.append(
            CalculatedLine(
                description=desc,
                quantity=line.quantity,
                unit_price=unit_price,
                product_id=line.product_id,
                variant_id=line.variant_id,
                tax_id=line.tax_id,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                discount_amount=line_discount,
                amount=final_line_amount,
                line_type="STANDARD",
            )
        )

    # 4. Apply subscription-level discounts
    for d in subscription_discounts:
        order_net = subtotal_sum - discount_sum
        if order_net <= ZERO:
            break

        if d.type == DiscountType.PERCENTAGE:
            d_amount = quantize_money(order_net * (d.value / Decimal("100")))
        else:
            d_amount = min(quantize_money(d.value), order_net)

        if d_amount > ZERO:
            discount_sum += d_amount
            applied_discounts.append((d, d_amount))
            # Append a discount summary line
            calculated_lines.append(
                CalculatedLine(
                    description=f"Discount: {d.name}",
                    quantity=1,
                    unit_price=-d_amount,
                    product_id=None,
                    variant_id=None,
                    tax_id=None,
                    tax_rate=ZERO,
                    tax_amount=ZERO,
                    discount_amount=d_amount,
                    amount=-d_amount,
                    line_type="DISCOUNT",
                )
            )

    grand_total = max(ZERO, subtotal_sum + tax_sum - discount_sum)

    return CalculationResult(
        lines=calculated_lines,
        amount_subtotal=subtotal_sum,
        amount_tax=tax_sum,
        amount_discount=discount_sum,
        amount_total=grand_total,
        applied_discounts=applied_discounts,
    )

