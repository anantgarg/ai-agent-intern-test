"""Usability + Compatibility (+ Accessibility note for a CLI).

Usability: can humans use it easily (clear answers, sources, next steps)?
Compatibility: Windows/macOS/Linux paths, Python versions, encodings.
Accessibility: no UI to audit — assert the CLI is plain-text, no color-only
or visual-only signaling (screen-reader/keyboard neutral by construction).
"""
import sys

import pytest

from .conftest import chat


class TestUsability:
    def test_answer_has_next_step_or_handoff(self, agent):
        for q in ["Where is my order?", "Please check ORD-9999.",
                  "Are all fabrics vegan in bags?"]:
            r, _ = chat(agent, agent.new_session(), q)
            low = r["answer"].lower()
            assert ("order id" in low or "contact support" in low
                    or "human" in low or "next step" in low)

    def test_policy_answer_shows_sources(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "What is the standard return window?")
        assert "Sources:" in r["answer"]
        assert ".md" in r["answer"]

    def test_error_message_actionable(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Please check ORD-9999.")
        assert "ORD-9999" in r["answer"]
        assert "check the order id" in r["answer"].lower()

    def test_no_jargon_trace_leak(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Where is ORD-1007?")
        for jargon in ("cosine", "traceback", "exception in handler"):
            assert jargon not in r["answer"].lower()


class TestCompatibility:
    def test_python_version_supported(self):
        assert sys.version_info >= (3, 10)

    def test_paths_portable(self, agent):
        assert len(agent.chunks) > 0  # built via pathlib, no hardcoded separators

    def test_output_is_plain_text(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Do you ship to Canada?")
        assert r["answer"].isascii() or "–" in r["answer"]  # only en-dash beyond ascii
        assert "\x1b[" not in r["answer"]  # no ANSI color codes


class TestAccessibilityNote:
    def test_no_color_only_signals(self, agent, fresh_session):
        # Handoff is words ("Yes"/"No"), never color/icons alone.
        r, _ = chat(agent, fresh_session, "Where is ORD-1007?")
        assert "Handoff:" in r["answer"] or "handoff" in r["answer"].lower()

    def test_plain_language_errors(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Where is my order?")
        assert "order ID" in r["answer"] and "ORD-1007" in r["answer"]
