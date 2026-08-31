from app.tools.orders import lookup_order


def test_valid_order():
    result = lookup_order("ORD-1007")

    assert result["found"] is True
    assert result["status"] == "shipped"
    assert result["carrier"] == "UPS"
    assert result["estimated_delivery"] == "2026-08-22"


def test_normalizes_order_id():
    result = lookup_order(" ord-1007 ")

    assert result["found"] is True
    assert result["order_id"] == "ORD-1007"


def test_unknown_order():
    result = lookup_order("ORD-9999")

    assert result["found"] is False
    assert result["error"] == "order_not_found"


def test_cancelled_order_hides_stale_shipping_data():
    result = lookup_order("ORD-1004")

    assert result["found"] is True
    assert result["status"] == "cancelled"
    assert "estimated_delivery" not in result
    assert "tracking_number" not in result


def test_internal_data_is_not_exposed():
    result = lookup_order("ORD-1007")

    assert "email" not in result
    assert "shipping_address" not in result
    assert "risk_score" not in result
    assert "warehouse_note" not in result