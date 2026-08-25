from app.tools.order_lookup import OrderLookup
from app.config import ORDERS_FILE

def test_normalizes_order_id():
    assert OrderLookup(ORDERS_FILE).lookup(' ord-1007 ')['found']

def test_unknown_and_malformed_are_safe():
    tool=OrderLookup(ORDERS_FILE)
    assert tool.lookup('ORD-9999')['found'] is False
    assert tool.lookup('not-an-order')['found'] is False

def test_internal_fields_are_never_exposed():
    result=OrderLookup(ORDERS_FILE).lookup('ORD-1007')
    forbidden={'email','customer_email','shipping_address','address','internal','risk_score','warehouse_note'}
    assert not forbidden.intersection(result['order'])
    assert 'ava.morgan@example.test' not in str(result)

def test_cancelled_order_drops_stale_delivery_fields():
    result=OrderLookup(ORDERS_FILE).lookup('ORD-1004')
    assert result['order']['status']=='cancelled'
    assert 'estimated_delivery' not in result['order']
    assert 'tracking_number' not in result['order']
    assert 'UPS' not in str(result['order'])

def test_missing_eta_is_not_invented():
    result=OrderLookup(ORDERS_FILE).lookup('ORD-1011')
    assert result['order']['estimated_delivery'] is None
