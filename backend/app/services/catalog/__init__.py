"""Catalog services (Member 2): products, plans, taxes and discounts."""

from app.services.catalog.discounts import (
    create_discount,
    delete_discount,
    get_discount,
    list_discounts,
    update_discount,
)
from app.services.catalog.plans import (
    create_plan,
    delete_plan,
    get_plan,
    list_plans,
    selectable_plans,
    update_plan,
)
from app.services.catalog.products import (
    add_attribute,
    add_variant,
    create_product,
    delete_attribute,
    delete_product,
    delete_variant,
    get_attribute,
    get_product,
    get_variant,
    list_products,
    update_product,
    update_variant,
)
from app.services.catalog.taxes import (
    create_tax,
    delete_tax,
    get_tax,
    list_taxes,
    update_tax,
)

__all__ = [
    "create_discount",
    "delete_discount",
    "get_discount",
    "list_discounts",
    "update_discount",
    "create_plan",
    "delete_plan",
    "get_plan",
    "list_plans",
    "selectable_plans",
    "update_plan",
    "add_attribute",
    "add_variant",
    "create_product",
    "delete_attribute",
    "delete_product",
    "delete_variant",
    "get_attribute",
    "get_product",
    "get_variant",
    "list_products",
    "update_product",
    "update_variant",
    "create_tax",
    "delete_tax",
    "get_tax",
    "list_taxes",
    "update_tax",
]
