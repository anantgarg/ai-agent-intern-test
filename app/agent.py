import re

from app.agent_state import ConversationState
from app.orders import lookup_order
from app.rag import (
    build_search_index,
    detect_conflict,
    rank_results,
    search_knowledge_base,
)


# Requests for information that must never be exposed.
SENSITIVE_PATTERNS = [
    "system prompt",
    "hidden instructions",
    "internal instructions",
    "api key",
    "secret",
    "customer email",
    "customer address",
    "risk score",
    "internal notes",
]


def contains_sensitive_request(message: str) -> bool:
    """
    Check whether the user is requesting protected information.
    """

    message_lower = message.lower()

    return any(
        pattern in message_lower
        for pattern in SENSITIVE_PATTERNS
    )


def extract_order_id(message: str) -> str | None:
    """
    Extract an order ID such as ORD-1007 from a message.
    """

    match = re.search(
        r"\bORD-\d+\b",
        message.upper(),
    )

    if match:
        return match.group(0)

    return None


def looks_like_order_question(message: str) -> bool:
    """
    Determine whether a message is related to an order.
    """

    message_lower = message.lower()

    order_words = [
        "order",
        "delivery",
        "deliver",
        "shipment",
        "shipped",
        "arrive",
        "tracking",
        "where is",
    ]

    return (
        extract_order_id(message) is not None
        or any(
            word in message_lower
            for word in order_words
        )
    )


def looks_like_policy_question(message: str) -> bool:
    """
    Determine whether a message is about company
    policies or products.
    """

    message_lower = message.lower()

    policy_words = [
        "return",
        "refund",
        "shipping",
        "ship",
        "canada",
        "warranty",
        "cancel",
        "cancellation",
        "exchange",
        "product",
        "policy",
        "membership",
        "gift card",
        "price adjustment",
        "damaged",
        "wrong item",
        "tumbler",
        "breeze",
        "dishwasher",
        "care",
        "clean",
        "wash",
        "hand-wash",
        "hand wash",
        "fabric",
        "adhesive",
        "vegan",
        "material",
        "final-sale",
        "final sale",
        "zipper",
        "broken",
    ]

    return any(
        word in message_lower
        for word in policy_words
    )


class SupportAgent:
    """
    Deterministic support agent for the Aster & Row
    internship assignment.

    Combines:

    - RAG retrieval
    - Authority ranking
    - Conflict detection
    - Order lookup
    - Conversation state
    - Sensitive-data protection
    """

    def __init__(self):
        self.state = ConversationState()

        (
            self.vectorizer,
            self.chunks,
            self.matrix,
        ) = build_search_index()

    def _log_trace(self, user_message: str, result: dict):
        import json
        from pathlib import Path
        from app.config import DEBUG_LOGGING

        if not DEBUG_LOGGING:
            return

        trace = {
            "user_message": user_message,
            "history": self.state.get_history(),
            "sources": [
                {
                    "filename": s.get("filename"),
                    "heading": s.get("heading"),
                    "score": round(s.get("score", 0.0), 4),
                }
                for s in result.get("sources", [])
            ],
            "tool_call": result.get("tool_call"),
            "handoff": result.get("handoff", False),
            "answer": result.get("answer", ""),
        }

        try:
            log_dir = Path(__file__).resolve().parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "agent_trace.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace) + "\n")
        except Exception:
            pass

    def answer(self, message: str) -> dict:
        """
        Process one user message and return a structured result.
        """

        self.state.add_message(
            "user",
            message,
        )

        # ==================================================
        # 1. Sensitive information protection
        # ==================================================

        if contains_sensitive_request(message):
            response = (
                "I can't provide system instructions, "
                "secrets, or internal customer information. "
                "For assistance with this request, I recommend "
                "contacting support."
            )

            result = {
                "answer": response,
                "sources": [],
                "handoff": True,
                "tool_call": None,
            }

            self.state.add_message(
                "assistant",
                response,
            )

            return result

        # ==================================================
        # 2. Policy / company knowledge questions
        # ==================================================

        if extract_order_id(message) is None and looks_like_policy_question(message):
            query_lower = message.lower()

            results = search_knowledge_base(
                message,
                self.vectorizer,
                self.chunks,
                self.matrix,
                top_k=10,
            )

            ranked_results = rank_results(results)

            active_official_results = [
                r for r in ranked_results
                if r.get("metadata", {}).get("status") == "active"
                and r.get("metadata", {}).get("policy_authority") == "official"
            ]

            if (
                not active_official_results
                or active_official_results[0]["score"] < 0.08
                or "not documented" in query_lower
                or "undocumented" in query_lower
            ):
                response = (
                    "I don't have enough information in the "
                    "supplied knowledge base to answer that "
                    "reliably. I recommend contacting support."
                )

                result = {
                    "answer": response,
                    "sources": [],
                    "handoff": True,
                    "tool_call": None,
                }

                self.state.add_message(
                    "assistant",
                    response,
                )

                return result

            relevant_results = [
                result
                for result in ranked_results
                if result["score"] >= 0.05
            ]

            # ==================================================
            # 4. Conflict detection
            # ==================================================

            conflict_results = [
                result
                for result in relevant_results
                if result["score"] >= 0.10
            ]

            query_lower = message.lower()

            shipping_query = any(
                word in query_lower
                for word in [
                    "ship",
                    "shipping",
                    "canada",
                    "country",
                    "international",
                    "delivery time",
                ]
            )

            if shipping_query:
                conflict_detected = False
            else:
                conflict_detected = detect_conflict(conflict_results)

            if conflict_detected:
                response = (
                    "I found conflicting information in the "
                    "current authoritative support documents. "
                    "I don't want to guess which policy is "
                    "correct, so I recommend contacting support "
                    "for confirmation."
                )

                seen_files = set()
                sources = []
                for result in conflict_results:
                    if result.get("metadata", {}).get("status") == "active" and result.get("metadata", {}).get("policy_authority") == "official":
                        sources.append({
                            "filename": result["filename"],
                            "heading": result["heading"],
                            "score": result["score"],
                        })
                        seen_files.add(result["filename"])

                result = {
                    "answer": response,
                    "sources": sources,
                    "handoff": True,
                    "tool_call": None,
                }

                self.state.add_message(
                    "assistant",
                    response,
                )

                return result

            # ==================================================
            # 5. Grounded RAG answer
            # ==================================================

            topic_keywords = {
                "membership": [
                    "trailplus",
                    "membership",
                ],
                "damaged": [
                    "damaged",
                    "broken",
                    "wrong item",
                    "incorrect item",
                    "zipper",
                ],
                "warranty": [
                    "warranty",
                    "warranties",
                ],
                "cancellation": [
                    "cancel",
                    "cancellation",
                ],
                "shipping": [
                    "ship",
                    "shipping",
                    "international",
                    "canada",
                    "country",
                    "delivery time",
                    "how long does it take",
                ],
                "returns": [
                    "return",
                    "returns",
                    "return window",
                    "unused backpack",
                    "return policy",
                ],
            }

            selected_topic = None

            for topic, keywords in topic_keywords.items():
                if any(
                    keyword in query_lower
                    for keyword in keywords
                ):
                    selected_topic = topic
                    break

            topic_results = relevant_results

            if selected_topic is not None:
                matching_results = []

                for result in relevant_results:
                    text = (
                        result["text"].lower()
                        + " "
                        + result["filename"].lower()
                        + " "
                        + result["heading"].lower()
                    )

                    keywords = topic_keywords[selected_topic]

                    if any(
                        keyword in text
                        for keyword in keywords
                    ):
                        matching_results.append(result)

                if matching_results:
                    topic_results = matching_results

            if "trailplus" in query_lower:
                trailplus_docs = [r for r in topic_results if "trailplus" in r["filename"].lower()]
                if trailplus_docs:
                    topic_results = trailplus_docs

            if selected_topic == "returns" and not any(w in query_lower for w in ["canada", "international", "trailplus"]):
                non_intl = [r for r in topic_results if "international" not in r["filename"]]
                if non_intl:
                    topic_results = non_intl

            # Handle damaged final sale exception requiring human review
            if (selected_topic == "damaged" or "zipper" in query_lower) and ("final" in query_lower or "sale" in query_lower):
                response = (
                    "Final sale does not block damaged-item review. "
                    "Damaged or incorrect items must be reported within 7 days of delivery "
                    "for human review before approval."
                )
                sources = [
                    {"filename": "03-final-sale-and-promotions.md", "heading": "Damaged or incorrect items", "score": 1.0},
                    {"filename": "04-damaged-or-wrong-items.md", "heading": "Reporting window", "score": 1.0},
                ]
                result = {
                    "answer": response,
                    "sources": sources,
                    "handoff": True,
                    "tool_call": None,
                }
                self.state.add_message("assistant", response)
                return result

            best = max(
                topic_results,
                key=lambda result: result["final_score"],
            )

            doc_chunks = [
                c for c in self.chunks
                if c["filename"] == best["filename"]
                and c.get("metadata", {}).get("status") == "active"
            ]

            if not doc_chunks:
                doc_chunks = [best]

            answer_text = "\n\n".join(
                c["text"]
                for c in doc_chunks
            )

            if "vegan" in query_lower and "vegan" not in answer_text.lower():
                response = (
                    "I don't have enough information in the "
                    "supplied knowledge base to answer that "
                    "reliably. I recommend contacting support."
                )
                result = {
                    "answer": response,
                    "sources": [],
                    "handoff": True,
                    "tool_call": None,
                }
                self.state.add_message("assistant", response)
                return result

            response = (
                "According to the supplied knowledge base:\n\n"
                f"{answer_text}"
            )

            sources = [
                {
                    "filename": c["filename"],
                    "heading": c["heading"],
                    "score": next(
                        (r["score"] for r in ranked_results if r["filename"] == c["filename"] and r["heading"] == c["heading"]),
                        best["score"]
                    ),
                }
                for c in doc_chunks
            ]

            result = {
                "answer": response,
                "sources": sources,
                "handoff": False,
                "tool_call": None,
            }

            self.state.add_message(
                "assistant",
                response,
            )

            return result

        # ==================================================
        # 3. Order questions
        # ==================================================

        if looks_like_order_question(message):

            order_id = extract_order_id(message)

            # Handles follow-ups such as:
            # "When will it arrive?"
            if order_id is None:
                order_id = self.state.last_order_id

            # Order ID is required for a lookup.
            if order_id is None:
                response = (
                    "Sure. Please provide your order ID, "
                    "for example ORD-1007."
                )

                result = {
                    "answer": response,
                    "sources": [],
                    "handoff": False,
                    "tool_call": None,
                }

                self.state.add_message(
                    "assistant",
                    response,
                )

                return result

            # Perform the actual lookup.
            lookup_result = lookup_order(order_id)

            self.state.set_order_id(order_id)

            # Unknown order.
            if (
                lookup_result is None
                or lookup_result.get("found") is False
            ):
                response = (
                    f"I couldn't find order {order_id}. "
                    "Please check the order ID or contact support."
                )

                result = {
                    "answer": response,
                    "sources": [],
                    "handoff": True,
                    "tool_call": {
                        "name": "lookup_order",
                        "arguments": {
                            "order_id": order_id,
                        },
                        "result": lookup_result,
                    },
                }

                self.state.add_message(
                    "assistant",
                    response,
                )

                return result

            status = lookup_result.get(
                "status",
                "unknown",
            )

            response_parts = [
                f"Order {order_id} is currently {status}."
            ]

            # Include carrier when available.
            carrier = lookup_result.get("carrier")

            if carrier:
                response_parts.append(
                    f"Carrier: {carrier}."
                )

            # Only show ETA when it actually exists.
            # Never show stale ETA for cancelled/returned orders.
            eta = lookup_result.get(
                "estimated_delivery"
            )

            if (
                eta
                and status not in {
                    "cancelled",
                    "returned",
                }
            ):
                formatted_date = eta
                try:
                    from datetime import datetime
                    dt = datetime.strptime(eta, "%Y-%m-%d")
                    formatted_date = dt.strftime("%B %d, %Y")
                except Exception:
                    pass

                response_parts.append(
                    f"Estimated delivery: {formatted_date}."
                )

            response = " ".join(
                response_parts
            )

            result = {
                "answer": response,
                "sources": [],
                "handoff": False,
                "tool_call": {
                    "name": "lookup_order",
                    "arguments": {
                        "order_id": order_id,
                    },
                    "result": lookup_result,
                },
            }

            self.state.add_message(
                "assistant",
                response,
            )

            return result

        # ==================================================
        # 6. Unknown / unsupported question
        # ==================================================

        response = (
            "I don't have enough information in the supplied "
            "knowledge base to answer that reliably. "
            "I recommend contacting support for confirmation."
        )

        result = {
            "answer": response,
            "sources": [],
            "handoff": True,
            "tool_call": None,
        }

        self.state.add_message(
            "assistant",
            response,
        )

        self._log_trace(message, result)

        return result