from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ORDER_RE = re.compile(r"\bORD-\d{4}\b", re.IGNORECASE)


@dataclass
class SafeOrderResult:
    found: bool
    order_id: str | None
    message: str
    tool_called: bool = False


class OrderLookup:
    def __init__(self, path: str | Path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.orders = {
            o["order_id"].upper().strip(): o for o in payload["orders"]
        }

    @staticmethod
    def extract_order_id(text: str) -> str | None:
        m = ORDER_RE.search(text)
        return m.group(0).upper() if m else None

    def lookup(self, raw_order_id: str) -> SafeOrderResult:
        order_id = raw_order_id.strip().upper()
        if not ORDER_RE.fullmatch(order_id):
            return SafeOrderResult(False, order_id, "That order ID format is invalid.", True)

        order = self.orders.get(order_id)
        if not order:
            return SafeOrderResult(
                False,
                order_id,
                f"The order was not found. Please check the order ID or contact support. (Requested: {order_id})",
                True,
            )

        status = order.get("status", "unknown")
        if status == "cancelled":
            message = f"Order {order_id} is cancelled and will not be shipped."
        elif status == "shipped":
            carrier = order.get("carrier")
            eta = order.get("estimated_delivery")
            if eta:
                from datetime import datetime
                parsed_date = datetime.strptime(eta, "%Y-%m-%d")
                date = f"{parsed_date.strftime('%B')} {parsed_date.day}, {parsed_date.year}"
                message = f"Order {order_id} is shipped with {carrier}. Current estimated delivery is {date}."
            else:
                message = f"Order {order_id} has shipped with {carrier}. A delivery estimate is currently unavailable."
        else:
            # customer_safe_message is authoritative and contains no internal-only fields.
            message = order.get("customer_safe_message", f"Order {order_id} status: {status}.")
        return SafeOrderResult(True, order_id, message, True)
