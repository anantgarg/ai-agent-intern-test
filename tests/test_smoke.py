"""TYPE: Smoke testing — is the build even worth testing further?

Minimal alive checks. Fast, broad, shallow. If any fail: STOP.
"""
import json
import subprocess
import sys

from .conftest import ROOT


def test_imports():
    import app.agent, app.cli, app.documents, app.orders, app.retrieval  # noqa
    import eval.run_eval  # noqa


def test_kb_loads(agent):
    assert len(agent.chunks) > 20


def test_orders_load(agent):
    assert len(agent.orders.orders) == 12


def test_agent_answers(agent, fresh_session):
    r = agent.chat(fresh_session, "Hello")
    assert r["answer"].strip()
    assert isinstance(r["handoff"], bool)


def test_cli_single_question():
    p = subprocess.run([sys.executable, "-m", "app.cli", "Where is ORD-1007?"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=60)
    assert p.returncode == 0
    assert "Answer:" in p.stdout and "Handoff:" in p.stdout


def test_visible_and_extra_cases_valid_json():
    for f in [ROOT / "evaluation" / "visible-cases.json",
              ROOT / "eval" / "extra-cases.json"]:
        data = json.loads(f.read_text(encoding="utf-8"))
        assert len(data["cases"]) >= 5
        for c in data["cases"]:
            assert c["id"] and c["messages"]
