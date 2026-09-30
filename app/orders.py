"""Order lookup tool. Sanitized, deterministic, no PII leakage."""
from __future__ import annotations

import json
import re
from pathlib import Path

ORDER_ID_RE = re.compile(r"\bORD[\s\-_]*0*(\d{1,5})\b", re.IGNORECASE)
STRICT_ORDER_RE = re.compile(r"\bORD-(\d{4})\b", re.IGNORECASE)

CUSTOMER_SAFE_FIELDS = {
    "order_id", "membership_tier", "items", "placed_at", "status",
    "status_updated_at", "shipped_at", "delivered_at", "carrier",
    "tracking_number", "estimated_delivery", "customer_safe_message",
}

# Fields that must never be exposed
FORBIDDEN_FIELDS = {"customer", "internal", "risk_score", "warehouse_note",
                    "support_tags", "email", "shipping_address"}


def normalize_order_id(raw: str) -> str | None:
    """Normalize harmless differences: case, surrounding whitespace/punct.

    Returns canonical ORD-XXXX or None if no plausible ID found.
    """
    if raw is None:
        return None
    s = raw.strip().strip(".,!?;:'\"()[]{}")
    m = STRICT_ORDER_RE.search(s)
    if m:
        return f"ORD-{m.group(1)}"
    # looser: ORD 1007, ord_1007, ord1007
    m2 = ORDER_ID_RE.search(s)
    if m2:
        num = m2.group(1).zfill(4)[-4:]
        # Only accept 4-digit canonical range; still return canonical form
        # so caller can report "not found" rather than inventing.
        try:
            n = int(num)
        except ValueError:
            return None
        return f"ORD-{n:04d}"
    return None


def extract_order_id(text: str) -> str | None:
    if not text:
        return None
    return normalize_order_id(text)


def looks_like_order_query(text: str) -> bool:
    tl = text.lower()
    return bool(ORDER_ID_RE.search(text) or any(k in tl for k in (
        "where is my order", "where's my order", "order status", "track",
        "when will", "when should", "arrive", "delivery estimate",
        "my order", "order id", "ord-",
    )))


class OrderStore:
    def __init__(self, orders_path: str | Path):
        p = Path(orders_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        self.snapshot_at: str = data.get("snapshot_at", "")
        self.orders: dict[str, dict] = {}
        for o in data.get("orders", []):
            self.orders[o["order_id"].upper()] = o

    def lookup(self, order_id_raw: str) -> dict:
        """Return dict with keys: found, normalized_id, record_safe / reason.

        Never includes customer PII or internal fields.
        """
        nid = normalize_order_id(order_id_raw or "")
        if not nid:
            return {"found": False, "normalized_id": None,
                    "reason": "malformed",
                    "message": "That order ID was not recognized. Order IDs look like ORD-1007."}
        rec = self.orders.get(nid.upper())
        if not rec:
            return {"found": False, "normalized_id": nid,
                    "reason": "not_found",
                    "message": f"Order {nid} was not found."}
        safe = sanitize_record(rec)
        return {"found": True, "normalized_id": nid, "record_safe": safe}


def sanitize_record(rec: dict) -> dict:
    items_safe = [{"name": i.get("name"), "quantity": i.get("quantity"),
                   "final_sale": i.get("final_sale")} for i in rec.get("items", [])]
    return {
        "order_id": rec.get("order_id"),
        "membership_tier": rec.get("membership_tier"),
        "items": items_safe,
        "placed_at": rec.get("placed_at"),
        "status": rec.get("status"),
        "status_updated_at": rec.get("status_updated_at"),
        "shipped_at": rec.get("shipped_at"),
        "delivered_at": rec.get("delivered_at"),
        "carrier": rec.get("carrier"),
        "tracking_number": rec.get("tracking_number"),
        "estimated_delivery": rec.get("estimated_delivery"),
        "customer_safe_message": rec.get("customer_safe_message"),
    }


def format_date_human(iso_or_date: str | None) -> str | None:
    if not iso_or_date:
        return None
    s = iso_or_date[:10]
    try:
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
    except Exception:
        return iso_or_date
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    if 1 <= m <= 12:
        return f"{months[m-1]} {d}, {y}"
    return iso_or_date
