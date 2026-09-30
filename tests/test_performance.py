"""Non-functional: Performance testing (lightweight, stdlib timing only).

Load = expected use; Stress = beyond; Spike = sudden burst; Soak = sustained.
Thresholds are generous to avoid flaky failures — they catch cliffs, not noise.
"""
import time

import pytest

from .conftest import chat


def timed(fn, *a, **k):
    t0 = time.perf_counter()
    out = fn(*a, **k)
    return out, time.perf_counter() - t0


def test_single_chat_latency(agent, fresh_session):
    _, dt = timed(agent.chat, fresh_session, "Where is ORD-1007?")
    assert dt < 2.0, f"single chat took {dt:.2f}s"


def test_retrieval_latency(agent):
    _, dt = timed(agent.retriever.retrieve, "return window backpack", top_k=4)
    assert dt < 1.0, f"retrieval took {dt:.2f}s"


def test_load_20_sequential_chats(agent):
    s = agent.new_session()
    t0 = time.perf_counter()
    for i in range(20):
        agent.chat(s, f"What is the status of ORD-{1001 + (i % 12)}?")
    dt = time.perf_counter() - t0
    assert dt < 20.0, f"20 chats took {dt:.2f}s"


def test_spike_burst_fresh_sessions(agent):
    t0 = time.perf_counter()
    for i in range(10):
        agent.chat(agent.new_session(), "Do all products have a lifetime warranty?")
    dt = time.perf_counter() - t0
    assert dt < 15.0, f"burst took {dt:.2f}s"


def test_soak_100_chats_same_session(agent):
    s = agent.new_session()
    t0 = time.perf_counter()
    for i in range(100):
        agent.chat(s, "Where is ORD-1007?" if i % 2 == 0 else "What is the return window?")
    dt = time.perf_counter() - t0
    assert dt < 60.0, f"soak took {dt:.2f}s"
    assert len(s.history) == 200  # no history truncation bug hiding growth
