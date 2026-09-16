from agent.orders import OrderStore, extract_order_id


def test_extract_order_id_normalizes_harmless_variants():
    assert extract_order_id(" where is ord 1007? ") == "ORD-1007"


def test_cancelled_order_suppresses_stale_eta_and_tracking():
    result = OrderStore().lookup("ord-1004")
    assert result["status"] == "cancelled"
    assert "estimated_delivery" not in result
    assert "tracking_number" not in result


def test_lookup_never_exposes_internal_or_customer_private_fields():
    result = OrderStore().lookup("ORD-1007")
    rendered = str(result).lower()
    assert "ava.morgan" not in rendered
    assert "king street" not in rendered
    assert "risk_score" not in rendered
    assert "fraud" not in rendered

