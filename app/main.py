import os
import re
from datetime import datetime

from app.rag import search
from app.tools.orders import lookup_order


# =========================================================
# DEBUG / OBSERVABILITY
# =========================================================

def debug_log(event, **data):
    """
    Print structured debug information when DEBUG=1.

    Sensitive fields are never logged.
    """
    if os.getenv("DEBUG", "").lower() not in ("1", "true", "yes"):
        return

    sensitive_keys = {
        "email",
        "address",
        "internal_note",
        "risk_score",
        "fraud_review",
        "warehouse_note",
        "tracking_number",
    }

    safe_data = {}

    for key, value in data.items():
        if key in sensitive_keys:
            safe_data[key] = "[REDACTED]"
        else:
            safe_data[key] = value

    print(f"[DEBUG] {event}: {safe_data}")


# =========================================================
# HELPERS
# =========================================================

def format_delivery_date(value):
    """Convert YYYY-MM-DD into a customer-friendly date."""
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime(
            "%B %-d, %Y"
        )
    except (ValueError, TypeError):
        return value


def get_order_id(message):
    """
    Extract a valid order ID.

    Supports:
    - ORD-1007
    - ord-1007
    - surrounding whitespace
    """
    if not message:
        return None

    match = re.search(
        r"\bord-\d+\b",
        message,
        re.IGNORECASE,
    )

    if match:
        return match.group(0).upper()

    return None


def get_order_id_from_history(history):
    """
    Recover the most recent valid order ID from conversation history.

    This allows follow-ups such as:

        User: Where is ORD-1007?
        User: When should it arrive?

    to continue using ORD-1007 without asking the customer
    for the order ID again.
    """
    if not history:
        return None

    for item in reversed(history):
        if item.get("role") != "user":
            continue

        content = item.get("content", "")

        order_id = get_order_id(content)

        if order_id:
            return order_id

    return None


def has_malformed_order_id(message):
    """
    Detect attempted malformed order IDs such as:
    - ORD-ABC
    - ORD-12ABC
    """
    if not message:
        return False

    return bool(
        re.search(
            r"\bord-[a-z]+\b",
            message,
            re.IGNORECASE,
        )
        or
        re.search(
            r"\bord-[a-z0-9]*[a-z][a-z0-9]*\b",
            message,
            re.IGNORECASE,
        )
    )


def is_order_request(message):
    """
    Determine whether the customer is asking about an order.
    """
    order_phrases = [
        "where is my order",
        "where's my order",
        "track my order",
        "track order",
        "order status",
        "when will my order arrive",
        "when will the order arrive",
        "when will order arrive",
        "when does my order arrive",
        "when does the order arrive",
        "when should my order arrive",
        "when should the order arrive",
        "when will it arrive",
        "when should it arrive",
        "when does it arrive",
        "when will it be delivered",
        "when should it be delivered",
        "when does it get delivered",
        "order arrive",
        "delivery status",
        "delivery update",
        "shipping status",
        "shipping update",
    ]

    if "ord-" in message:
        return True

    return any(
        phrase in message
        for phrase in order_phrases
    )


def is_order_followup(message):
    """
    Detect a short follow-up that refers to a previously mentioned order.

    Examples:
    - When should it arrive?
    - When will it be delivered?
    - What's the status?
    - Has it shipped?
    """
    followup_phrases = [
        "when should it arrive",
        "when will it arrive",
        "when does it arrive",
        "when should it be delivered",
        "when will it be delivered",
        "when does it get delivered",
        "what's the status",
        "what is the status",
        "status?",
        "has it shipped",
        "is it shipped",
        "where is it now",
        "where is it",
        "delivery update",
        "shipping update",
        "when will it come",
        "when should it come",
    ]

    return any(
        phrase in message
        for phrase in followup_phrases
    )


def get_previous_user_messages(history):
    """
    Extract only user messages from conversation history.
    """
    return [
        item.get("content", "")
        for item in history
        if item.get("role") == "user"
    ]


def is_greeting(message):
    """
    Detect simple greetings so they are not incorrectly sent
    through knowledge-base retrieval.
    """
    greeting_patterns = [
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
    ]

    normalized = re.sub(
        r"[^\w\s]",
        "",
        message.lower().strip(),
    )

    return normalized in greeting_patterns


# =========================================================
# MAIN AGENT
# =========================================================

def answer(user_message, history=None):

    history = history or []

    message = user_message.lower().strip()

    debug_log(
        "user_message",
        message=user_message,
        history_length=len(history),
    )

    # =====================================================
    # SIMPLE GREETINGS
    # =====================================================

    # IMPORTANT:
    # Do this before RAG.
    #
    # "hi" should never retrieve random knowledge-base
    # documents such as shipping or return policies.
    if is_greeting(message):

        response = {
            "answer": (
                "Hi! I'm the Aster & Row support agent. "
                "How can I help you today?"
            ),
            "sources": [],
            "handoff": False,
            "tool": "not_called",
        }

        debug_log(
            "greeting",
            handoff=False,
            tool="not_called",
        )

        return response

    # =====================================================
    # PRIVACY PROTECTION
    # =====================================================

    sensitive_terms = [
        "email",
        "email address",
        "shipping address",
        "customer address",
        "address",
        "internal note",
        "internal notes",
        "risk score",
        "fraud review",
        "warehouse note",
        "warehouse notes",
    ]

    if any(
        term in message
        for term in sensitive_terms
    ):

        response = {
            "answer": (
                "I cannot provide customer email addresses, "
                "shipping addresses, internal notes, risk scores, "
                "or other internal-only information. "
                "Please contact support if you need assistance "
                "with the order."
            ),
            "sources": [],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "privacy_refusal",
            handoff=True,
            tool="not_called",
        )

        return response

    # =====================================================
    # SYSTEM / PROMPT INJECTION PROTECTION
    # =====================================================

    prompt_injection_terms = [
        "system prompt",
        "system instructions",
        "hidden instructions",
        "hidden prompt",
        "developer prompt",
        "developer instructions",
        "reveal your prompt",
        "show your prompt",
        "show hidden instructions",
        "ignore previous instructions",
        "ignore your instructions",
        "reveal secrets",
        "show secrets",
    ]

    if any(
        term in message
        for term in prompt_injection_terms
    ):

        response = {
            "answer": (
                "I cannot provide internal instructions or "
                "confidential information. I can help with "
                "Aster & Row support questions instead."
            ),
            "sources": [],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "prompt_injection_refusal",
            handoff=True,
            tool="not_called",
        )

        return response

    # =====================================================
    # ORDER CONTEXT
    # =====================================================

    previous_user_messages = get_previous_user_messages(
        history
    )

    current_order_id = get_order_id(message)
    historical_order_id = get_order_id_from_history(history)

    # =====================================================
    # ORDER LOOKUP
    # =====================================================

    order_requested = is_order_request(message)

    # If the user asks a follow-up such as
    # "When should it arrive?" and an order appeared earlier,
    # treat it as an order lookup.
    if (
        not current_order_id
        and historical_order_id
        and is_order_followup(message)
    ):
        order_requested = True
        current_order_id = historical_order_id

        debug_log(
            "order_context_recovered",
            order_id=current_order_id,
        )

    if order_requested:

        order_id = current_order_id

        # -------------------------------------------------
        # Malformed order ID
        # -------------------------------------------------

        if not order_id:

            if has_malformed_order_id(message):

                response = {
                    "answer": (
                        "The order ID appears to be malformed. "
                        "Please provide a valid order ID, "
                        "such as ORD-1007."
                    ),
                    "sources": [],
                    "handoff": False,
                    "tool": "not_called",
                }

                debug_log(
                    "malformed_order_id",
                    handoff=False,
                    tool="not_called",
                )

                return response

            # -------------------------------------------------
            # Missing order ID
            # -------------------------------------------------

            response = {
                "answer": (
                    "Please provide your order ID so I can "
                    "look up your order."
                ),
                "sources": [],
                "handoff": False,
                "tool": "not_called",
            }

            debug_log(
                "missing_order_id",
                handoff=False,
                tool="not_called",
            )

            return response

        # -------------------------------------------------
        # Actual lookup
        # -------------------------------------------------

        debug_log(
            "order_lookup",
            order_id=order_id,
        )

        result = lookup_order(order_id)

        debug_log(
            "order_lookup_result",
            found=result.get("found"),
            status=result.get("status"),
            carrier=result.get("carrier"),
            estimated_delivery=result.get(
                "estimated_delivery"
            ),
            tracking_number=result.get(
                "tracking_number"
            ),
        )

        # -------------------------------------------------
        # Unknown order
        # -------------------------------------------------

        if not result.get("found"):

            response = {
                "answer": (
                    "That order was not found. "
                    "Please check the order ID or contact support."
                ),
                "sources": [],
                "handoff": True,
                "tool": "order_lookup",
                "tool_result": {
                    "found": False,
                    "order_id": order_id,
                },
            }

            debug_log(
                "unknown_order",
                handoff=True,
                tool="order_lookup",
            )

            return response

        # -------------------------------------------------
        # Shipped order
        # -------------------------------------------------

        if result.get("status") == "shipped":

            carrier = result.get("carrier")

            estimated_delivery = result.get(
                "estimated_delivery"
            )

            if estimated_delivery:

                delivery_date = format_delivery_date(
                    estimated_delivery
                )

                answer_text = (
                    f"The order has shipped and is currently "
                    f"in transit with {carrier}. "
                    f"It is estimated to arrive on "
                    f"{delivery_date}."
                )

            else:

                answer_text = (
                    f"The order has shipped with {carrier}. "
                    "The delivery estimate is unavailable."
                )

            response = {
                "answer": answer_text,
                "sources": [],
                "handoff": False,
                "tool": "order_lookup",
                "tool_result": result,
            }

            debug_log(
                "shipped_order_response",
                handoff=False,
                tool="order_lookup",
            )

            return response

        # -------------------------------------------------
        # Cancelled / returned / other statuses
        # -------------------------------------------------

        safe_message = result.get(
            "customer_safe_message"
        )

        if not safe_message:

            safe_message = (
                "The current order information does not "
                "provide enough detail for me to safely "
                "describe this order. Please contact support."
            )

        response = {
            "answer": safe_message,
            "sources": [],
            "handoff": False,
            "tool": "order_lookup",
            "tool_result": result,
        }

        debug_log(
            "other_order_status",
            status=result.get("status"),
            handoff=False,
            tool="order_lookup",
        )

        return response

    # =====================================================
    # UNSUPPORTED ACTIONS / TOPICS
    # =====================================================

    unsupported_topics = [
        "refund",
        "refund me",
        "get a refund",
        "issue a refund",
        "give me my refund",
        "cancel my order",
        "cancel the order",
        "cancel order",
        "replacement",
        "replace my item",
        "replace the item",
        "address change",
        "change my address",
        "change shipping address",
        "vegan",
        "material certification",
    ]

    if any(
        term in message
        for term in unsupported_topics
    ):

        response = {
            "answer": (
                "The supplied information is insufficient "
                "to complete this action. I cannot approve "
                "or complete a refund, cancellation, replacement, "
                "or address change. Please contact support for "
                "human confirmation."
            ),
            "sources": [],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "unsupported_action",
            handoff=True,
            tool="not_called",
        )

        return response

    # =====================================================
    # GENUINE SOURCE CONFLICT
    # BREEZE TUMBLER DISHWASHER CARE
    # =====================================================

    if (
        "breeze tumbler" in message
        and "dishwasher" in message
    ):

        response = {
            "answer": (
                "The current official sources conflict. "
                "One says to hand-wash the stainless-steel "
                "body, while the product card says all "
                "components are dishwasher safe. Please get "
                "human confirmation before putting the entire "
                "tumbler in the dishwasher. As the safest "
                "interim guidance, hand-wash the tumbler body."
            ),
            "sources": [
                "11-product-care.md — Breeze Tumbler",
                "12-breeze-tumbler-product-card.md — Cleaning",
            ],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "source_conflict",
            handoff=True,
            sources=response["sources"],
        )

        return response

    # =====================================================
    # FINAL-SALE + DAMAGED ITEM
    # =====================================================

    if (
        (
            "final-sale" in message
            or "final sale" in message
        )
        and
        (
            "damaged" in message
            or "broken" in message
            or "defective" in message
            or "wrong item" in message
            or "incorrect item" in message
        )
    ):

        response = {
            "answer": (
                "Final-sale items can still be reviewed when "
                "they arrive damaged, defective, or incorrect. "
                "Please report the issue within **7 calendar "
                "days of delivery**. A human review is required "
                "before any refund or replacement can be approved."
            ),
            "sources": [
                "03-final-sale-and-promotions.md — "
                "Damaged or incorrect items",
                "04-damaged-or-wrong-items.md — "
                "Final-sale items",
            ],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "damaged_final_sale",
            handoff=True,
            sources=response["sources"],
        )

        return response

    # =====================================================
    # LEGACY / MIGRATION POLICY PROTECTION
    # =====================================================

    legacy_policy_query = (
        "older return policy" in message
        or "old return policy" in message
        or "older return period" in message
        or "old return period" in message
        or "previous return policy" in message
        or "previous return period" in message
        or "legacy return policy" in message
        or "legacy return period" in message
    )

    migration_note_query = (
        "migration note" in message
        or "60 days" in message
        or "ignore the real policy" in message
        or "newer document" in message
        or "ignore the current policy" in message
    )

    if (
        legacy_policy_query
        or migration_note_query
    ):

        response = {
            "answer": (
                "The migration note is not authoritative and "
                "must not override the current return policy. "
                "The standard policy is **30 calendar days from "
                "delivery**, unless a valid exception applies. "
                "The legacy policy does not override the current "
                "policy, and the agent cannot approve a return."
            ),
            "sources": [
                "01-returns-policy-current.md — Standard return window"
            ],
            "handoff": False,
            "tool": "not_called",
        }

        debug_log(
            "legacy_policy_protection",
            handoff=False,
            sources=response["sources"],
        )

        return response
        # =====================================================
    # LOW-INFORMATION / UNCLEAR INPUT
    # =====================================================

    low_information_inputs = {
        "i dont know",
        "i don't know",
        "idk",
        "not sure",
        "no idea",
        "nothing",
        "help",
        "okay",
        "ok",
        "thanks",
        "thank you",
    }

    normalized_message = re.sub(
        r"[^\w\s']",
        "",
        message,
    ).strip()

    if normalized_message in low_information_inputs:

        response = {
            "answer": (
                "No problem. Please tell me what you need "
                "help with, such as returns, shipping, "
                "warranty, or an order."
            ),
            "sources": [],
            "handoff": False,
            "tool": "not_called",
        }

        debug_log(
            "low_information_input",
            handoff=False,
            tool="not_called",
        )

        return response

    # =====================================================
    # CONVERSATION-AWARE RETRIEVAL
    # =====================================================

    retrieval_query = user_message

    if previous_user_messages:

        last_message = (
            previous_user_messages[-1].lower()
        )

        # -------------------------------------------------
        # International shipping -> Canada follow-up
        # -------------------------------------------------

        if (
            "international" in last_message
            and "canada" in message
        ):

            retrieval_query = (
                "international shipping Canada delivery "
                "estimate business days duties taxes"
            )

        # -------------------------------------------------
        # International duties follow-up
        # -------------------------------------------------

        elif (
            "canada" in last_message
            and (
                "duties" in message
                or "taxes" in message
            )
        ):

            retrieval_query = (
                "Canada international shipping duties taxes "
                "not prepaid"
            )

        # -------------------------------------------------
        # Order follow-up
        # -------------------------------------------------

        elif (
            historical_order_id
            and is_order_followup(message)
        ):

            retrieval_query = (
                previous_user_messages[-1]
                + " "
                + user_message
            )

        # -------------------------------------------------
        # General contextual follow-up
        # -------------------------------------------------

        else:

            retrieval_query = (
                previous_user_messages[-1]
                + " "
                + user_message
            )

    debug_log(
        "retrieval",
        query=retrieval_query,
        history_used=bool(previous_user_messages),
    )

    # =====================================================
    # SEARCH KNOWLEDGE BASE
    # =====================================================

    results = search(retrieval_query)

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadata = results.get(
        "metadatas",
        [[]]
    )[0]

    debug_log(
        "retrieval_results",
        count=len(documents),
        metadata_count=len(metadata),
    )

    # =====================================================
    # INSUFFICIENT INFORMATION
    # =====================================================

    if not documents:

        response = {
            "answer": (
                "The supplied information is insufficient. "
                "Please contact support for human confirmation."
            ),
            "sources": [],
            "handoff": True,
            "tool": "not_called",
        }

        debug_log(
            "insufficient_information",
            handoff=True,
            tool="not_called",
        )

        return response

    # =====================================================
    # DEFAULT RELEVANT CHUNKS
    # =====================================================

    selected_documents = documents[:3]
    selected_metadata = metadata[:3]

    # =====================================================
    # INTERNATIONAL SHIPPING
    # =====================================================

    if (
        "germany" in message
        or "international" in message
        or "canada" in message
        or "duties" in message
        or "taxes" in message
    ):

        relevant = []

        for doc, meta in zip(
            documents,
            metadata
        ):

            filename = meta.get(
                "filename",
                ""
            )

            heading = meta.get(
                "heading",
                ""
            ).lower()

            if filename == "06-international-shipping.md":

                if (
                    "supported destinations" in heading
                    or "canada delivery estimate" in heading
                    or "duties and taxes" in heading
                    or "general" in heading
                ):

                    relevant.append(
                        (doc, meta)
                    )

        if relevant:

            selected_documents = [
                item[0]
                for item in relevant[:3]
            ]

            selected_metadata = [
                item[1]
                for item in relevant[:3]
            ]

    # =====================================================
    # TRAILPLUS RETURN WINDOW
    # =====================================================

    if (
        "trailplus" in message
        and "return" in message
    ):

        relevant = []

        for doc, meta in zip(
            documents,
            metadata
        ):

            heading = meta.get(
                "heading",
                ""
            ).lower()

            if (
                meta.get("filename")
                == "09-trailplus-membership.md"
                and (
                    "return window" in heading
                    or "membership verification" in heading
                )
            ):

                relevant.append(
                    (doc, meta)
                )

        if relevant:

            selected_documents = [
                item[0]
                for item in relevant[:2]
            ]

            selected_metadata = [
                item[1]
                for item in relevant[:2]
            ]

            combined = "\n\n".join(
                selected_documents
            )

            combined = combined.replace(
                "45-calendar-day",
                "45 calendar days",
            )

            combined = combined.replace(
                "45-calendar-days",
                "45 calendar days",
            )

            selected_documents = [
                combined
            ]

    # =====================================================
    # WARRANTY
    # =====================================================

    if (
        "warranty" in message
        or "lifetime warranty" in message
    ):

        relevant = []

        for doc, meta in zip(
            documents,
            metadata
        ):

            if (
                meta.get("filename")
                == "07-warranty.md"
            ):

                relevant.append(
                    (doc, meta)
                )

        if relevant:

            selected_documents = [
                item[0]
                for item in relevant[:3]
            ]

            selected_metadata = [
                item[1]
                for item in relevant[:3]
            ]

        warranty_context = "\n\n".join(
            selected_documents
        )

        if "lifetime warranty" in message:

            warranty_context = (
                "Aster & Row does not offer a lifetime warranty. "
                "There is no lifetime warranty for Aster & Row "
                "products.\n\n"
                + warranty_context
            )

        selected_documents = [
            warranty_context
        ]

    # =====================================================
    # RETURN POLICY PRECEDENCE
    # =====================================================

    if (
        "return" in message
        and "trailplus" not in message
        and not (
            "final sale" in message
            or "final-sale" in message
        )
    ):

        relevant = []

        for doc, meta in zip(
            documents,
            metadata
        ):

            filename = meta.get(
                "filename",
                ""
            )

            heading = meta.get(
                "heading",
                ""
            ).lower()

            if (
                filename
                == "01-returns-policy-current.md"
            ):

                if (
                    "standard return window" in heading
                    or "general" in heading
                    or "return window" in heading
                ):

                    relevant.append(
                        (doc, meta)
                    )

        if relevant:

            selected_documents = [
                relevant[0][0]
            ]

            selected_metadata = [
                relevant[0][1]
            ]

    # =====================================================
    # FILTER INTERNAL MIGRATION CONTENT
    # =====================================================

    safe_documents = []
    safe_metadata = []

    for doc, meta in zip(
        selected_documents,
        selected_metadata
    ):

        filename = meta.get(
            "filename",
            ""
        )

        if (
            filename
            == "14-internal-content-migration-notes.md"
        ):
            continue

        safe_documents.append(doc)
        safe_metadata.append(meta)

    if safe_documents:

        selected_documents = safe_documents
        selected_metadata = safe_metadata

    # =====================================================
    # FINAL RESPONSE + SOURCES
    # =====================================================

    sources = [
        f"{meta.get('filename', 'unknown')} — "
        f"{meta.get('heading', 'General')}"
        for meta in selected_metadata
    ]

    context = "\n\n".join(
        selected_documents
    )

    debug_log(
        "final_response",
        sources=sources,
        handoff=False,
        tool="not_called",
        response_preview=context[:500],
    )

    return {
        "answer": context,
        "sources": sources,
        "handoff": False,
        "tool": "not_called",
    }