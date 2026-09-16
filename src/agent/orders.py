from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ORDERS_FILE = ROOT / "data" / "orders.json"
ORDER_RE = re.compile(r"\bORD\s*[- ]?\s*(\d{4})\b", re.IGNORECASE)


def extract_order_id(text: str) -> str | None:
    match = ORDER_RE.search(text)
    if not match:
        return None
    return f"ORD-{match.group(1)}".upper()


def _fmt_date(value: str | None) -> str | None:
    if not value:
        return None
    if "T" in value:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%B %-d, %Y")
    return date.fromisoformat(value).strftime("%B %-d, %Y")


class OrderStore:
    def __init__(self, orders_file: Path = ORDERS_FILE):
        data = json.loads(orders_file.read_text(encoding="utf-8"))
        self.snapshot_at = data["snapshot_at"]
        self.orders = {order["order_id"]: order for order in data["orders"]}

    def lookup(self, order_id: str | None) -> dict[str, Any]:
        if not order_id:
            return {"found": False, "error": "missing_order_id"}
        normalized = extract_order_id(order_id) or order_id.strip().upper()
        if not re.fullmatch(r"ORD-\d{4}", normalized):
            return {"found": False, "order_id": normalized, "error": "malformed_order_id"}
        order = self.orders.get(normalized)
        if not order:
            return {"found": False, "order_id": normalized, "error": "not_found"}

        safe: dict[str, Any] = {
            "found": True,
            "order_id": order["order_id"],
            "membership_tier": order.get("membership_tier"),
            "items": [
                {
                    "name": item.get("name"),
                    "quantity": item.get("quantity"),
                    "final_sale": item.get("final_sale"),
                }
                for item in order.get("items", [])
            ],
            "placed_at": _fmt_date(order.get("placed_at")),
            "status": order.get("status"),
            "status_updated_at": _fmt_date(order.get("status_updated_at")),
            "customer_safe_message": order.get("customer_safe_message"),
        }
        status = order.get("status")
        if status not in {"cancelled", "returned"}:
            for field in ("shipped_at", "delivered_at", "estimated_delivery"):
                safe[field] = _fmt_date(order.get(field))
            for field in ("carrier", "tracking_number"):
                safe[field] = order.get(field)
        elif status == "returned":
            safe["delivered_at"] = _fmt_date(order.get("delivered_at"))
        return safe


def order_summary(result: dict[str, Any]) -> tuple[str, bool]:
    if result.get("error") == "missing_order_id":
        return "Please share the order ID so I can look it up.", False
    if result.get("error") == "malformed_order_id":
        return "That order ID format does not look valid. Please check the order ID or contact support.", True
    if result.get("error") == "not_found":
        return f"The order was not found. Please check the order ID or contact support.", True

    status = result["status"]
    order_id = result["order_id"]
    if status == "cancelled":
        return f"The order is cancelled. It will not be shipped.", False
    if status == "returned":
        return f"{order_id} is returned. The return was received and processed.", False
    if status == "exception":
        return f"{order_id} has a shipment exception that requires support review. I recommend human assistance.", True
    if status == "shipped":
        carrier = result.get("carrier")
        eta = result.get("estimated_delivery")
        if eta:
            return f"{order_id} has shipped with {carrier} and is estimated to arrive on {eta}.", False
        return f"{order_id} has shipped with {carrier}. The delivery estimate is unavailable.", False
    if status == "delayed":
        return f"{order_id} is delayed. {result.get('customer_safe_message')}", False
    if status == "delivered":
        return f"{order_id} was delivered on {result.get('delivered_at')}.", False
    if status == "processing":
        eta = result.get("estimated_delivery")
        suffix = f" The current estimated delivery date is {eta}." if eta else " A delivery estimate is not yet available."
        return f"{order_id} is processing.{suffix}", False
    if status == "pending":
        return f"{order_id} is pending. {result.get('customer_safe_message')}", False
    return f"{order_id} status is {status}.", False
