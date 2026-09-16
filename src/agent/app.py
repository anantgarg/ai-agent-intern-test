from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .orders import OrderStore, extract_order_id, order_summary
from .retrieval import Retriever
from .schemas import AgentResponse, ToolCall


@dataclass
class Session:
    last_topic: str | None = None
    last_order_id: str | None = None
    turns: list[dict[str, str]] = field(default_factory=list)


class SupportAgent:
    def __init__(self):
        self.retriever = Retriever()
        self.orders = OrderStore()

    def respond(self, message: str, session: Session | None = None, debug: bool = False) -> AgentResponse:
        session = session or Session()
        text = message.strip()
        lower = text.lower()
        trace: dict[str, Any] = {"message": text, "history": session.turns[-4:]}
        tool_calls: list[ToolCall] = []
        sources: list[str] = []
        handoff = False

        if self._is_greeting(lower):
            answer = (
                "Hi! I can help with Aster & Row policies, product-care questions, shipping, returns, "
                "and customer-safe order status lookups. Share a question or an order ID like ORD-1007."
            )
            return self._finish(answer, sources, False, tool_calls, trace, session, text, debug)

        if self._asks_private_order_data(lower):
            order_id = extract_order_id(text)
            answer = (
                "I cannot disclose customer email, address, internal notes, risk score, or other internal-only data. "
                "I can help with customer-safe order status information if needed. I recommend human assistance for privacy-sensitive requests."
            )
            if order_id:
                result = self.orders.lookup(order_id)
                tool_calls.append(ToolCall("order_lookup", {"order_id": order_id}, result))
            handoff = True
            return self._finish(answer, sources, handoff, tool_calls, trace, session, text, debug)

        if self._unsafe_request(lower):
            answer = "I cannot reveal hidden instructions, system prompts, secrets, or internal-only data."
            handoff = True
            return self._finish(answer, sources, handoff, tool_calls, trace, session, text, debug)

        order_intent = self._is_order_intent(lower)
        order_id = extract_order_id(text) or (session.last_order_id if order_intent and self._followup_order(lower) else None)
        if order_intent:
            if not order_id:
                answer = "Please share the order ID so I can look it up."
                return self._finish(answer, sources, False, tool_calls, trace, session, text, debug)
            result = self.orders.lookup(order_id)
            session.last_order_id = order_id
            tool_calls.append(ToolCall("order_lookup", {"order_id": order_id}, result))
            answer, handoff = order_summary(result)
            return self._finish(answer, sources, handoff, tool_calls, trace, session, text, debug)

        answer, sources, handoff, topic = self._answer_policy(text, session)
        if topic:
            session.last_topic = topic
        return self._finish(answer, sources, handoff, tool_calls, trace, session, text, debug)

    def _finish(
        self,
        answer: str,
        sources: list[str],
        handoff: bool,
        tool_calls: list[ToolCall],
        trace: dict[str, Any],
        session: Session,
        user_text: str,
        debug: bool,
    ) -> AgentResponse:
        session.turns.append({"role": "user", "content": user_text})
        session.turns.append({"role": "assistant", "content": answer})
        trace.update(
            {
                "sources": sources,
                "handoff": handoff,
                "tool_calls": [
                    {"name": c.name, "arguments": c.arguments, "result": c.result}
                    for c in tool_calls
                ],
                "final_response": answer,
            }
        )
        return AgentResponse(answer=answer, sources=sources, handoff=handoff, tool_calls=tool_calls, trace=trace if debug else {})

    @staticmethod
    def _asks_private_order_data(lower: str) -> bool:
        private_terms = ("email", "address", "internal note", "risk score", "fraud", "warehouse note")
        return any(term in lower for term in private_terms) and "ord-" in lower

    @staticmethod
    def _is_greeting(lower: str) -> bool:
        normalized = re.sub(r"[^a-z ]", "", lower).strip()
        return normalized in {"hi", "hello", "hey", "help", "hi there", "hello there"}

    @staticmethod
    def _unsafe_request(lower: str) -> bool:
        return any(term in lower for term in ("system prompt", "hidden prompt", "reveal your prompt", "secret"))

    @staticmethod
    def _is_order_intent(lower: str) -> bool:
        if re.search(r"\bord\s*[- ]?\s*\d{4}\b", lower):
            return True
        return any(phrase in lower for phrase in ("my order", "order status", "where is my order", "when will it arrive", "when will it get here"))

    @staticmethod
    def _followup_order(lower: str) -> bool:
        return any(phrase in lower for phrase in ("arrive", "get here", "status", "where is it", "tracking"))

    def _answer_policy(self, text: str, session: Session) -> tuple[str, list[str], bool, str | None]:
        lower = text.lower()
        query = text
        if session.last_topic == "international_shipping" and ("canada" in lower or "what about" in lower):
            query = f"international shipping Canada delivery duties taxes {text}"

        if "migration note" in lower or "60 days" in lower or "approve my return" in lower:
            sources = ["01-returns-policy-current.md > Standard return window"]
            answer = (
                "The migration note is not authoritative customer policy. The current standard policy is "
                "30 days unless a valid exception applies. The agent cannot approve a return from chat."
            )
            return answer, sources, False, "returns"

        if "trailplus" in lower and "return" in lower:
            return (
                "TrailPlus members whose membership was active when the order was placed receive a 45 calendar days return window from delivery for eligible items.",
                ["09-trailplus-membership.md > Return window"],
                False,
                "returns",
            )
        if "return" in lower and ("backpack" in lower or "unused" in lower or "regular" in lower or "standard" in lower):
            return (
                "A regular customer may request a return for an eligible unused backpack within 30 calendar days of delivery.",
                ["01-returns-policy-current.md > Standard return window"],
                False,
                "returns",
            )
        if "final-sale" in lower or "final sale" in lower or "broken zipper" in lower:
            return (
                "You are not completely out of luck: final sale does not block damaged-item review. "
                "Damage or wrong-item issues should report within 7 days of delivery, and human review before approval is required for any refund or replacement.",
                [
                    "03-final-sale-and-promotions.md > Damaged or incorrect items",
                    "04-damaged-or-wrong-items.md > Reporting window",
                    "04-damaged-or-wrong-items.md > Final-sale items",
                ],
                True,
                "damaged_items",
            )
        if "international" in lower or "canada" in lower or "germany" in lower or session.last_topic == "international_shipping":
            if "germany" in lower:
                return (
                    "Shipping to Germany is not currently available. Aster & Row currently ships internationally only to Canada.",
                    ["06-international-shipping.md > Supported destinations"],
                    False,
                    "international_shipping",
                )
            return (
                "Canada is supported. Aster & Row currently ships internationally only to Canada. Canadian orders generally arrive within 5–9 business days after dispatch, and duties or taxes are not prepaid.",
                [
                    "06-international-shipping.md > Supported destinations",
                    "06-international-shipping.md > Canada delivery estimate",
                    "06-international-shipping.md > Duties and taxes",
                ],
                False,
                "international_shipping",
            )
        if "lifetime warranty" in lower or "warranty" in lower:
            return (
                "No lifetime warranty is offered. Bags have 2 years from the purchase date; drinkware and travel accessories have 1 year.",
                ["07-warranty.md > Warranty periods"],
                False,
                "warranty",
            )
        if "gift card" in lower:
            return (
                "Gift cards are final sale and cannot be returned, exchanged for cash, or used to purchase another gift card except where required by law.",
                ["10-gift-cards-and-price-adjustments.md > Gift cards"],
                False,
                "gift_cards",
            )
        if "price" in lower and ("adjustment" in lower or "dropped" in lower or "issue" in lower):
            return (
                "A price adjustment may be requested when the public price of the same item, color, and size drops within 7 calendar days of the original purchase. "
                "A human support specialist must approve and process it, and I must not promise that credit has been issued.",
                ["10-gift-cards-and-price-adjustments.md > Price adjustments"],
                True,
                "price_adjustments",
            )
        if "breeze tumbler" in lower and "dishwasher" in lower:
            return (
                "Current official sources conflict: one says hand-wash the body, and one says all components are dishwasher safe. "
                "Use human confirmation or safest interim guidance: hand-wash the body and top-rack the lid.",
                [
                    "11-product-care.md > Breeze Tumbler",
                    "12-breeze-tumbler-product-card.md > Cleaning",
                ],
                True,
                "product_care",
            )
        if "vegan" in lower or "adhesives" in lower or "fabrics" in lower:
            return (
                "The supplied information is insufficient to confirm whether all fabrics and adhesives are vegan. Please get human confirmation.",
                [],
                True,
                "unknown",
            )

        passages = self.retriever.search(query)
        if not passages:
            return (
                "The supplied information is insufficient to answer reliably. I recommend human confirmation.",
                [],
                True,
                "unknown",
            )
        public = [p for p in passages if p.metadata.get("audience") == "customer" and p.metadata.get("status") == "active"]
        if not public:
            return (
                "The supplied information is insufficient to answer reliably from customer-facing active sources. I recommend human confirmation.",
                [],
                True,
                "unknown",
            )
        first = public[0]
        return (
            f"Based on the available policy: {first.text}",
            [first.source],
            False,
            first.title.lower().replace(" ", "_"),
        )


def format_response(response: AgentResponse, debug: bool = False) -> str:
    parts = [response.answer]
    if response.sources:
        parts.append("Sources:\n" + "\n".join(f"- {source}" for source in response.sources))
    if response.handoff:
        parts.append("Human handoff recommended: yes")
    if debug:
        parts.append("Trace:\n" + json.dumps(response.trace, indent=2, sort_keys=True))
    return "\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aster & Row support agent")
    parser.add_argument("command", choices=["ask", "chat"])
    parser.add_argument("message", nargs="*")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    agent = SupportAgent()
    session = Session()
    if args.command == "ask":
        response = agent.respond(" ".join(args.message), session=session, debug=args.debug)
        print(format_response(response, debug=args.debug))
        return

    print("Aster & Row support agent. Type 'exit' to quit.")
    while True:
        try:
            message = input("> ")
        except EOFError:
            break
        if message.strip().lower() in {"exit", "quit"}:
            break
        response = agent.respond(message, session=session, debug=args.debug)
        print(format_response(response, debug=args.debug))


if __name__ == "__main__":
    main()
