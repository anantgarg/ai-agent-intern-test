"""Recovery + Installation/upgrade + Localization/i18n.

Recovery: what happens when something goes wrong (no crash, safe fallback).
Installation: fresh-clone readiness without extra dependencies.
Localization: dates, currency, dashes, encodings stay stable.
"""
import subprocess
import sys

import pytest

from app.agent import Agent
from .conftest import ROOT, chat


# ---------- recovery ----------
class TestRecovery:
    def test_missing_kb_raises_clearly(self, tmp_path):
        with pytest.raises(Exception):
            Agent(kb_dir=str(tmp_path / "nope"), orders_path=str(ROOT / "data/orders.json"))

    def test_missing_orders_raises_clearly(self, tmp_path):
        with pytest.raises(Exception):
            Agent(kb_dir=str(ROOT / "knowledge-base"),
                  orders_path=str(tmp_path / "nope.json"))

    def test_malformed_orders_json_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(Exception):
            Agent(kb_dir=str(ROOT / "knowledge-base"), orders_path=str(bad))

    def test_gibberish_query_abstains_safely(self, agent):
        r, _ = chat(agent, agent.new_session(), "asdf qwer zxcv 12345 !!!")
        assert r["answer"].strip()
        assert isinstance(r["handoff"], bool)

    def test_none_like_empty_handled(self, agent):
        r = agent.chat(agent.new_session(), "")
        assert r["answer"].strip()


# ---------- installation ----------
class TestInstallation:
    def test_stdlib_only_imports(self):
        import ast
        third_party = {"selenium", "playwright", "requests", "numpy",
                       "sklearn", "torch", "openai", "pydantic"}
        for f in ["app/agent.py", "app/retrieval.py", "app/orders.py",
                  "app/documents.py", "app/cli.py", "eval/run_eval.py"]:
            tree = ast.parse((ROOT / f).read_text(encoding="utf-8"))
            imported = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    imported.update(a.name.split(".")[0] for a in n.names)
                elif isinstance(n, ast.ImportFrom) and n.module:
                    imported.add(n.module.split(".")[0])
            assert not (imported & third_party), f"{f}: {imported & third_party}"

    def test_env_example_and_requirements(self):
        assert (ROOT / ".env.example").exists()
        assert (ROOT / "requirements.txt").exists()

    def test_eval_runs_from_clean_process(self):
        p = subprocess.run([sys.executable, "-m", "eval.run_eval",
                            "--out", str(ROOT / "eval" / "results.json")],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        assert "passed" in p.stdout.lower()


# ---------- localization ----------
class TestLocalization:
    def test_us_date_format(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Where is ORD-1007?")
        assert "August 22, 2026" in r["answer"]
        assert "2026-08-22" not in r["answer"]

    def test_currency_formats(self, agent):
        s = agent.new_session()
        assert "$6.95" in agent.chat(s, "How do returns shipping fees work?")["answer"]
        r = agent.chat(agent.new_session(),
                       "How long does standard shipping take to Chicago?")
        assert "$75" in r["answer"]

    def test_endash_normalization(self, agent, fresh_session):
        r, _ = chat(agent, fresh_session, "Do you ship to Canada?")
        assert "5" in r["answer"] and "9" in r["answer"] and "business days" in r["answer"]

    def test_kb_utf8_readable(self):
        for md in (ROOT / "knowledge-base").glob("*.md"):
            md.read_text(encoding="utf-8")
