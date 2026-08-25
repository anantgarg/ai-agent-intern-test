import json
import re
from pathlib import Path

ORDER_ID_RE = re.compile(r"^ORD-\d{4,}$", re.IGNORECASE)
PUBLIC_FIELDS = (
    "order_id", "status", "carrier", "tracking_number",
    "estimated_delivery", "items", "order_date", "customer_safe_message"
)
TERMINAL_WITHOUT_SHIPMENT = {"cancelled", "canceled", "returned", "refunded"}

class OrderLookup:
    """Safe application-side order lookup. Raw customer/internal fields never leave this class."""
    def __init__(self, path: Path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        orders = payload.get("orders", payload) if isinstance(payload, dict) else payload
        self.orders = {str(o.get("order_id", "")).upper(): o for o in orders}

    def lookup(self, order_id: str) -> dict:
        if not isinstance(order_id, str):
            return {"found": False, "reason": "malformed_order_id"}
        normalized = order_id.strip().upper()
        if not ORDER_ID_RE.fullmatch(normalized):
            return {"found": False, "reason": "malformed_order_id", "order_id": normalized}
        order = self.orders.get(normalized)
        if order is None:
            return {"found": False, "reason": "unknown_order_id", "order_id": normalized}

        safe = {key: order.get(key) for key in PUBLIC_FIELDS if key in order}
        safe["order_id"] = normalized
        safe["status"] = order.get("status")
        if safe["status"] and str(safe["status"]).lower() in TERMINAL_WITHOUT_SHIPMENT:
            for key in ("carrier", "tracking_number", "estimated_delivery"):
                safe.pop(key, None)
        return {"found": True, "order": safe}
