import json
from pathlib import Path


ORDERS_FILE = Path(__file__).resolve().parents[2] / "data" / "orders.json"


def lookup_order(order_id: str) -> dict:
    """Look up an order and return only customer-safe information."""

    if not isinstance(order_id, str):
        return {
            "found": False,
            "error": "invalid_order_id"
        }

    normalized_id = order_id.strip().upper()

    if not normalized_id.startswith("ORD-"):
        return {
            "found": False,
            "error": "invalid_order_id"
        }

    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    order = next(
        (order for order in data["orders"]
         if order["order_id"] == normalized_id),
        None
    )

    if order is None:
        return {
            "found": False,
            "error": "order_not_found",
            "order_id": normalized_id
        }

    result = {
        "found": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "customer_safe_message": order["customer_safe_message"],
    }

    # Only provide shipping details when they are relevant.
    if order["status"] not in {"cancelled", "returned"}:
        if order.get("carrier"):
            result["carrier"] = order["carrier"]

        if order.get("tracking_number"):
            result["tracking_number"] = order["tracking_number"]

        if order.get("estimated_delivery"):
            result["estimated_delivery"] = order["estimated_delivery"]

    return result