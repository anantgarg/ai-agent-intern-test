from app.orders import lookup_order


def test_valid_order():
    result = lookup_order("ORD-1007")

    assert result["found"] is True
    assert result["order_id"] == "ORD-1007"
    assert result["status"] == "shipped"
    assert result["carrier"] == "UPS"
    assert result["estimated_delivery"] == "2026-08-22"


def test_lowercase_and_whitespace():
    result = lookup_order("  ord-1007 ")

    assert result["found"] is True
    assert result["order_id"] == "ORD-1007"


def test_unknown_order():
    result = lookup_order("ORD-9999")

    assert result["found"] is False
    assert result["reason"] == "order_not_found"


def test_missing_order_id():
    result = lookup_order("")

    assert result["found"] is False
    assert result["reason"] == "missing_or_invalid_order_id"


def test_cancelled_order_does_not_expose_stale_eta():
    result = lookup_order("ORD-1004")

    assert result["found"] is True
    assert result["status"] == "cancelled"
    assert result["estimated_delivery"] is None
    assert result["carrier"] is None
    assert result["tracking_number"] is None


def test_private_fields_are_not_returned():
    result = lookup_order("ORD-1007")

    assert "customer" not in result
    assert "email" not in result
    assert "shipping_address" not in result
    assert "internal" not in result
    assert "risk_score" not in result
    assert "warehouse_note" not in result