from __future__ import annotations

import json
import re
from pathlib import Path


ORDER_ID_RE = re.compile(r"^ORD-\d{4}$", re.IGNORECASE)
TERMINAL = {"cancelled", "returned"}


class OrderLookup:
    """Customer-safe order lookup. Internal fields never leave this boundary."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.orders = {str(o.get("order_id", "")).upper(): o for o in data.get("orders", [])}

    @staticmethod
    def normalize(order_id: str) -> str:
        return re.sub(r"\s+", "", order_id or "").upper()

    def lookup(self, order_id: str | None) -> dict:
        if not isinstance(order_id, str) or not order_id.strip():
            return {"ok": False, "error": "missing_order_id"}
        oid = self.normalize(order_id)
        if not ORDER_ID_RE.fullmatch(oid):
            return {"ok": False, "error": "malformed_order_id", "order_id": oid}
        order = self.orders.get(oid)
        if not order:
            return {"ok": False, "error": "not_found", "order_id": oid}

        status = str(order.get("status", "")).lower()
        result = {
            "ok": True,
            "order_id": oid,
            "status": status,
            "customer_safe_message": order.get("customer_safe_message"),
        }
        if status not in TERMINAL:
            if order.get("carrier"):
                result["carrier"] = order["carrier"]
            if order.get("estimated_delivery"):
                result["estimated_delivery"] = order["estimated_delivery"]
        return result
