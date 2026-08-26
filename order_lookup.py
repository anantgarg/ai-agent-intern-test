import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

DATA_PATH = Path(__file__).parent / "data" / "orders.json"


def _load_orders() -> Dict[str, Dict[str, Any]]:
    """Loads and indexes mock order data by order_id."""
    if not DATA_PATH.exists():
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                order["order_id"].upper(): order
                for order in data.get("orders", [])
            }
    except Exception:
        return {}


ORDERS_DB = _load_orders()


def extract_order_id(text: str) -> Optional[str]:
    """Extracts an order ID matching pattern ORD-XXXX from input text."""
    if not text or not isinstance(text, str):
        return None
    match = re.search(r"\bORD-\d{4}\b", text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def order_lookup(order_id: str) -> Dict[str, Any]:
    """Retrieves order details for a given order ID.

    Args:
        order_id: The order identifier (e.g., 'ORD-1004').

    Returns:
        Dict containing 'found' boolean status and order details or error details.
    """
    if not order_id or not isinstance(order_id, str):
        return {"found": False, "error": "Invalid order ID provided."}

    normalized_id = order_id.strip().upper()
    order = ORDERS_DB.get(normalized_id)

    if not order:
        return {
            "found": False,
            "error": f"Order {order_id} was not found in our system.",
        }

    return {"found": True, **order}