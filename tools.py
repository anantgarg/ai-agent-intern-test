import json
import os

ORDERS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'orders.json')

def load_orders():
    with open(ORDERS_FILE, 'r') as f:
        return json.load(f)

orders_db = load_orders().get('orders', [])

def lookup_order(order_id: str) -> dict:
    """
    Look up an order by its ID and return sanitized, customer-safe details.
    """
    # Normalize input
    if not order_id:
        return {"error": "Missing order ID. Please provide an order ID."}
    
    normalized_id = order_id.strip().upper()
    
    # Find order
    order_data = next((o for o in orders_db if o.get('order_id') == normalized_id), None)
    
    if not order_data:
        return {"error": f"Order {normalized_id} was not found. Please check the order ID or contact support."}
    
    # Sanitize and extract only customer-safe fields
    safe_order = {
        "order_id": order_data.get("order_id"),
        "membership_tier": order_data.get("membership_tier"),
        "placed_at": order_data.get("placed_at"),
        "status": order_data.get("status"),
        "status_updated_at": order_data.get("status_updated_at"),
        "shipped_at": order_data.get("shipped_at"),
        "delivered_at": order_data.get("delivered_at"),
        "carrier": order_data.get("carrier"),
        "tracking_number": order_data.get("tracking_number"),
        "estimated_delivery": order_data.get("estimated_delivery"),
        "customer_safe_message": order_data.get("customer_safe_message"),
    }
    
    # Extract items safely
    safe_items = []
    for item in order_data.get("items", []):
        safe_items.append({
            "name": item.get("name"),
            "quantity": item.get("quantity"),
            "final_sale": item.get("final_sale")
        })
    safe_order["items"] = safe_items
    
    # Apply status precedence logic
    status = safe_order.get("status")
    if status in ["cancelled", "returned"]:
        safe_order["estimated_delivery"] = None
        safe_order["tracking_number"] = None
        safe_order["carrier"] = None
        
    # Remove None values for cleaner output
    safe_order = {k: v for k, v in safe_order.items() if v is not None}
        
    return safe_order

def get_tool_definition():
    return {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up the status and details of an order using its order ID. Call this when a customer asks about their order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to look up (e.g., ORD-1007)."
                    }
                },
                "required": ["order_id"]
            }
        }
    }
