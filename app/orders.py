import json
import re
from pathlib import Path


ORDERS_FILE = Path(__file__).resolve().parent.parent / "data" / "orders.json"


def load_orders():
    """Load the mock order data from orders.json."""
    with ORDERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data["orders"]


def normalize_order_id(order_id: str) -> str:
    """Normalize harmless differences in an order ID."""
    if not isinstance(order_id, str):
        return ""

    # Remove surrounding whitespace and common punctuation.
    normalized = order_id.strip().upper()
    normalized = re.sub(r"[^A-Z0-9-]", "", normalized)

    return normalized


def lookup_order(order_id: str) -> dict:
    """
    Look up an order and return only customer-safe information.

    Internal fields such as email, address, risk score,
    warehouse notes, and support tags are never returned.
    """
    normalized_id = normalize_order_id(order_id)

    if not normalized_id:
        return {
            "found": False,
            "reason": "missing_or_invalid_order_id",
        }

    orders = load_orders()

    for order in orders:
        if order["order_id"] == normalized_id:
            safe_result = {
                "found": True,
                "order_id": order["order_id"],
                "membership_tier": order["membership_tier"],
                "items": [
                    {
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "final_sale": item["final_sale"],
                    }
                    for item in order["items"]
                ],
                "placed_at": order["placed_at"],
                "status": order["status"],
                "status_updated_at": order["status_updated_at"],
                "shipped_at": order["shipped_at"],
                "delivered_at": order["delivered_at"],
                "carrier": order["carrier"],
                "tracking_number": order["tracking_number"],
                "estimated_delivery": order["estimated_delivery"],
                "customer_safe_message": order["customer_safe_message"],
            }

            # Cancelled/returned orders may contain stale delivery data.
            if order["status"] in {"cancelled", "returned"}:
                safe_result["carrier"] = None
                safe_result["tracking_number"] = None
                safe_result["estimated_delivery"] = None

            return safe_result

    return {
        "found": False,
        "reason": "order_not_found",
    }