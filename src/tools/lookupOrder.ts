import fs from "node:fs";
import { config } from "../config.js";
import type { OrderLookupResult, SafeOrderView } from "../types.js";

interface RawOrder {
  order_id: string;
  membership_tier: string;
  items: Array<{
    name: string;
    quantity: number;
    final_sale: boolean;
  }>;
  placed_at: string;
  status: string;
  status_updated_at: string;
  shipped_at: string | null;
  delivered_at: string | null;
  carrier: string | null;
  tracking_number: string | null;
  estimated_delivery: string | null;
  customer_safe_message: string;
}

interface OrdersFile {
  snapshot_at: string;
  orders: RawOrder[];
}

let cached: OrdersFile | null = null;

function loadOrders(): OrdersFile {
  if (!cached) {
    cached = JSON.parse(fs.readFileSync(config.ordersPath, "utf8")) as OrdersFile;
  }
  return cached;
}

/** Normalize harmless differences: whitespace, case, surrounding punctuation. */
export function normalizeOrderId(input: string): string | null {
  const cleaned = input
    .trim()
    .toUpperCase()
    .replace(/^[^A-Z0-9]+|[^A-Z0-9]+$/g, "")
    .replace(/\s+/g, "");

  const match = /^(ORD-\d{4})$/.exec(cleaned);
  if (match) return match[1];

  // Accept ORD1007 → ORD-1007
  const alt = /^ORD(\d{4})$/.exec(cleaned);
  if (alt) return `ORD-${alt[1]}`;

  return null;
}

function toSafeView(order: RawOrder): SafeOrderView {
  const notes: string[] = [];
  const status = order.status.toLowerCase();

  if (status === "cancelled" || status === "returned") {
    notes.push(
      `Status "${order.status}" is authoritative. Do not report carrier tracking or estimated delivery as if the order is still arriving, even if older fields remain in storage.`,
    );
  }

  if (status === "shipped" && !order.estimated_delivery) {
    notes.push(
      "Order has shipped but estimated_delivery is null. Say an estimate is unavailable. Do not invent a date.",
    );
  }

  if (status === "exception") {
    notes.push(
      "Order is in exception status. Recommend human support handoff. Do not invent a resolution.",
    );
  }

  const estimated_delivery =
    status === "cancelled" || status === "returned"
      ? null
      : order.estimated_delivery;

  const carrier =
    status === "cancelled" || status === "returned" ? null : order.carrier;
  const tracking_number =
    status === "cancelled" || status === "returned"
      ? null
      : order.tracking_number;

  return {
    order_id: order.order_id,
    membership_tier: order.membership_tier,
    items: order.items.map((i) => ({
      name: i.name,
      quantity: i.quantity,
      final_sale: i.final_sale,
    })),
    placed_at: order.placed_at,
    status: order.status,
    status_updated_at: order.status_updated_at,
    shipped_at: order.shipped_at,
    delivered_at: order.delivered_at,
    carrier,
    tracking_number,
    estimated_delivery,
    customer_safe_message: order.customer_safe_message,
    notes,
  };
}

export function lookupOrder(orderIdInput: string): OrderLookupResult {
  const normalized = normalizeOrderId(orderIdInput);
  if (!normalized) {
    return {
      found: false,
      order_id_normalized: null,
      error:
        "Malformed order ID. Expected a value like ORD-1007. Ask the customer to re-check the ID.",
    };
  }

  const data = loadOrders();
  const order = data.orders.find((o) => o.order_id === normalized);
  if (!order) {
    return {
      found: false,
      order_id_normalized: normalized,
      error: `Order ${normalized} was not found. Ask the customer to check the ID or contact support.`,
    };
  }

  return {
    found: true,
    order_id_normalized: normalized,
    order: toSafeView(order),
  };
}

/** OpenAI / OpenRouter function-tool schema for order lookup. */
export const LOOKUP_ORDER_TOOL = {
  type: "function" as const,
  function: {
    name: "lookup_order",
    description:
      "Look up a single Aster & Row order by order ID (e.g. ORD-1007). Returns only customer-safe fields. Call this whenever the user asks about order status, shipping, tracking, or arrival and an order ID is available. Do not invent order data.",
    parameters: {
      type: "object" as const,
      properties: {
        order_id: {
          type: "string",
          description: "The order ID provided by the customer, e.g. ORD-1007",
        },
      },
      required: ["order_id"],
    },
  },
};
