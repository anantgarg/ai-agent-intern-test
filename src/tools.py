import json
from pathlib import Path
from typing import Any, Dict, Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.json"

def _load_orders() -> Dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def lookup_order_status(order_id: Optional[str]) -> Dict[str, Any]:
    if not order_id or not isinstance(order_id, str) or not order_id.strip():
        return {"error": "Order ID is missing or empty."}

    normalized_id = order_id.strip().upper()
    if not DATA_PATH.exists():
        return {"error": "Orders database not found."}

    orders_root = _load_orders()
    orders_list = orders_root.get("orders", [])
    
    order = next((o for o in orders_list if o.get("order_id") == normalized_id), None)
    if not order:
        return {"error": f"Order '{normalized_id}' not found."}

    sanitized_result = {
        "order_id": normalized_id,
        "status": order.get("status"),
        "items": order.get("items", []),
    }

    if order.get("customer_safe_message"):
        sanitized_result["customer_safe_message"] = order.get("customer_safe_message")
    if order.get("estimated_delivery"):
        sanitized_result["estimated_delivery"] = order["estimated_delivery"]
    if order.get("carrier"):
        sanitized_result["carrier"] = order["carrier"]

    return sanitized_result