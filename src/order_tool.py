"""
order_tool.py

Implements order lookup against data/orders.json as a function the LLM
can call as a tool. This module enforces two safety rules derived from
data/orders-data-dictionary.md:

  1. Only a whitelisted set of fields is ever returned. customer.* and
     everything inside internal.* (including warehouse_note, which was
     found to contain embedded instruction-like text) is stripped before
     the result leaves this function -- it never reaches the model.

  2. status is treated as authoritative. Stale carrier/tracking/ETA
     fields on cancelled or returned orders are not presented as if the
     order were still in transit.

Usage (standalone test):
    python src/order_tool.py
"""

import json
import re

ORDERS_FILE = "data/orders.json"

SAFE_FIELDS = [
    "order_id",
    "membership_tier",
    "placed_at",
    "status",
    "status_updated_at",
    "shipped_at",
    "delivered_at",
    "carrier",
    "tracking_number",
    "estimated_delivery",
    "customer_safe_message",
]


def _load_orders():
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["orders"]


def _normalize_order_id(raw_id):
    """
    Normalizes harmless input differences: strips whitespace, uppercases,
    and strips characters other than letters, digits, and hyphens.
    Does not attempt to guess or correct a substantially different ID.
    """
    if raw_id is None:
        return ""
    cleaned = raw_id.strip().upper()
    cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)
    return cleaned


def order_lookup(order_id):
    """
    Looks up an order by ID and returns a sanitized, customer-safe dict.
    """
    normalized_id = _normalize_order_id(order_id)

    if not normalized_id:
        return {"found": False, "reason": "no_order_id_provided"}

    orders = _load_orders()
    match = None
    for order in orders:
        if order.get("order_id", "").upper() == normalized_id:
            match = order
            break

    if match is None:
        return {"found": False, "reason": "order_not_found"}

    result = {"found": True}

    for field in SAFE_FIELDS:
        result[field] = match.get(field)

    result["items"] = [
        {
            "name": item.get("name"),
            "quantity": item.get("quantity"),
            "final_sale": item.get("final_sale"),
        }
        for item in match.get("items", [])
    ]

    _apply_status_rules(result)

    return result


def _apply_status_rules(result):
    """
    Applies status-precedence rules directly to the sanitized result, so
    the model never has to reason about which fields are stale.
    """
    status = result.get("status")

    if status in ("cancelled", "returned"):
        result["estimated_delivery"] = None
        result["note_for_agent"] = (
            f"Order is {status}. Do not imply it is still arriving, "
            "even if carrier/tracking fields are present."
        )

    elif status == "shipped" and result.get("estimated_delivery") is None:
        result["note_for_agent"] = (
            "Order has shipped but no delivery estimate is available. "
            "Do not calculate or invent a date."
        )

    elif status == "exception":
        result["note_for_agent"] = (
            "Order has a carrier exception. Recommend human support review."
        )

    elif status == "pending":
        result["note_for_agent"] = (
            "Order has not entered processing yet."
        )


if __name__ == "__main__":
    test_ids = ["ORD-1007", " ord-1004 ", "ORD-9999", "", "ORD-1011"]

    for tid in test_ids:
        print(f"Lookup: {tid!r}")
        print(json.dumps(order_lookup(tid), indent=2))
        print()