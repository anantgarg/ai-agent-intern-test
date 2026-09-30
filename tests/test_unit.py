"""LEVEL: Unit testing — smallest pieces in isolation.

Pure functions only: documents.parse/split, retrieval.tokenize/weights,
orders.normalize/extract/sanitize/format. No Agent.chat here.
"""
import pytest

from app import documents as D
from app.documents import Chunk, load_knowledge_base
from app.orders import (
    OrderStore,
    extract_order_id,
    format_date_human,
    normalize_order_id,
    sanitize_record,
)
from app.retrieval import Retriever, authority_weight, tokenize

from .conftest import ROOT


# ---------- documents.parse_frontmatter ----------
class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        raw = "---\ntitle: T\nstatus: active\n---\nhello body"
        meta, body = D.parse_frontmatter(raw)
        assert meta == {"title": "T", "status": "active"}
        assert body == "hello body"

    def test_missing_frontmatter_returns_empty_meta(self):
        meta, body = D.parse_frontmatter("just body, no fences")
        assert meta == {}
        assert body == "just body, no fences"

    def test_lines_without_colon_ignored(self):
        raw = "---\ntitle: T\nnotakvline\n---\nbody"
        meta, _ = D.parse_frontmatter(raw)
        assert meta == {"title": "T"}

    def test_value_with_colon_kept(self):
        raw = "---\ntitle: A: B\n---\nbody"
        meta, _ = D.parse_frontmatter(raw)
        assert meta["title"] == "A: B"


# ---------- documents.split_markdown ----------
class TestSplitMarkdown:
    def test_splits_on_h2(self):
        chunks = D.split_markdown("f.md", {"title": "T"}, "# H1\n## A\ntext a\n## B\ntext b")
        headings = [c.heading for c in chunks]
        assert "A" in headings and "B" in headings

    def test_no_headings_single_chunk(self):
        chunks = D.split_markdown("f.md", {"title": "T"}, "plain text only")
        assert len(chunks) == 1
        assert chunks[0].text == "plain text only"

    def test_empty_body_no_chunks(self):
        assert D.split_markdown("f.md", {"title": "T"}, "") == []

    def test_metadata_copied_not_shared(self):
        meta = {"title": "T", "status": "active"}
        chunks = D.split_markdown("f.md", meta, "## A\nx")
        chunks[0].metadata["status"] = "MUTATED"
        assert meta["status"] == "active"

    def test_chunk_ids_unique(self):
        chunks = D.split_markdown("f.md", {"title": "T"}, "## A\nx\n## A\ny")
        assert len({c.chunk_id for c in chunks}) == len(chunks)


# ---------- documents.load_knowledge_base ----------
class TestLoadKnowledgeBase:
    def test_loads_14_source_files(self):
        chunks = load_knowledge_base(str(ROOT / "knowledge-base"))
        files = {c.filename for c in chunks}
        assert len(files) == 14
        assert "01-returns-policy-current.md" in files
        assert "14-internal-content-migration-notes.md" in files

    def test_metadata_preserved(self):
        chunks = load_knowledge_base(str(ROOT / "knowledge-base"))
        by_file = {}
        for c in chunks:
            by_file.setdefault(c.filename, c.metadata)
        assert by_file["01-returns-policy-current.md"]["status"] == "active"
        assert by_file["01-returns-policy-current.md"]["policy_authority"] == "official"
        assert by_file["02-returns-policy-legacy.md"]["status"] == "superseded"
        assert by_file["14-internal-content-migration-notes.md"]["policy_authority"] == "none"

    def test_every_chunk_has_text_and_heading(self):
        for c in load_knowledge_base(str(ROOT / "knowledge-base")):
            assert c.text.strip()
            assert c.heading.strip()
            assert c.full_text.strip()


# ---------- retrieval.tokenize / weights ----------
class TestTokenize:
    def test_lowercases_and_strips_stopwords(self):
        toks = tokenize("The QUICK Brown Fox")
        assert "quick" in toks and "brown" in toks
        assert "the" not in toks

    def test_single_chars_dropped(self):
        assert tokenize("a I x") == []

    def test_empty_string(self):
        assert tokenize("") == []


class TestAuthorityWeight:
    def _chunk(self, filename, **meta):
        return Chunk("id", filename, "t", "h", "text", dict(meta))

    def test_active_official_customer_is_1(self):
        c = self._chunk("01-returns-policy-current.md", status="active",
                        policy_authority="official", audience="customer")
        assert authority_weight(c) == 1.0

    def test_superseded_downranked(self):
        c = self._chunk("02-returns-policy-legacy.md", status="superseded",
                        policy_authority="official", audience="customer")
        assert authority_weight(c) < 1.0

    def test_draft_and_none_minimal(self):
        d = self._chunk("14-internal-content-migration-notes.md", status="draft",
                        policy_authority="none", audience="internal")
        assert authority_weight(d) <= 0.15

    def test_internal_official_between(self):
        c = self._chunk("13-support-escalation.md", status="active",
                        policy_authority="official", audience="internal")
        w = authority_weight(c)
        assert 0.15 < w < 1.0

    def test_migration_notes_always_lowest(self):
        mig = self._chunk("14-internal-content-migration-notes.md", status="active",
                          policy_authority="official", audience="customer")
        off = self._chunk("01-returns-policy-current.md", status="active",
                          policy_authority="official", audience="customer")
        assert authority_weight(mig) < authority_weight(off)


class TestRetrieverScoring:
    @pytest.fixture(scope="class")
    def retriever(self):
        return Retriever(load_knowledge_base(str(ROOT / "knowledge-base")))

    def test_returns_top_k(self, retriever):
        assert len(retriever.retrieve("return window", top_k=4)) == 4

    def test_deterministic(self, retriever):
        a = [s.chunk.chunk_id for s in retriever.retrieve("warranty bags")]
        b = [s.chunk.chunk_id for s in retriever.retrieve("warranty bags")]
        assert a == b

    def test_scores_sorted_desc(self, retriever):
        scores = [s.score for s in retriever.retrieve("shipping canada")]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query_no_crash(self, retriever):
        assert isinstance(retriever.retrieve("", top_k=2), list)

    def test_conflict_recall_adds_both_sources(self, retriever):
        top = retriever.retrieve("Can I put the Breeze Tumbler in the dishwasher?", top_k=4)
        files = {s.chunk.filename for s in top}
        assert "11-product-care.md" in files
        assert "12-breeze-tumbler-product-card.md" in files


# ---------- orders pure functions ----------
class TestNormalizeOrderId:
    @pytest.mark.parametrize("raw,expected", [
        ("ORD-1007", "ORD-1007"),
        ("ord-1007", "ORD-1007"),
        ("  ord-1007 ", "ORD-1007"),
        ("ORD 1007", "ORD-1007"),
        ("ord_1007", "ORD-1007"),
        ("ord1007", "ORD-1007"),
        ("Where is ORD-1007?", "ORD-1007"),
        ("ord-1007.", "ORD-1007"),
    ])
    def test_variants(self, raw, expected):
        assert normalize_order_id(raw) == expected

    @pytest.mark.parametrize("raw", ["", "hello", "ORD-ABC", "ABC-123", None])
    def test_malformed_returns_none(self, raw):
        assert normalize_order_id(raw) is None

    def test_extract_delegates(self):
        assert extract_order_id("please check ord-1010!") == "ORD-1010"
        assert extract_order_id("") is None


class TestSanitizeAndFormat:
    @pytest.fixture(scope="class")
    def store(self):
        return OrderStore(str(ROOT / "data" / "orders.json"))

    def test_lookup_found_has_only_safe_fields(self, store):
        res = store.lookup("ORD-1007")
        assert res["found"] is True
        safe = res["record_safe"]
        assert "customer" not in safe and "internal" not in safe
        for bad in ("email", "shipping_address", "risk_score", "warehouse_note", "support_tags"):
            assert bad not in json_blob(safe)

    def test_lookup_unknown(self, store):
        res = store.lookup("ORD-9999")
        assert res == {"found": False, "normalized_id": "ORD-9999",
                       "reason": "not_found", "message": "Order ORD-9999 was not found."}

    def test_lookup_malformed(self, store):
        res = store.lookup("nonsense")
        assert res["found"] is False and res["reason"] == "malformed"

    def test_sanitize_items_shape(self):
        rec = {"order_id": "X", "items": [{"name": "N", "quantity": 2, "final_sale": True,
                                          "sku": "S", "extra": 1}],
               "customer": {"email": "e"}, "internal": {"risk_score": 9}}
        safe = sanitize_record(rec)
        assert safe["items"] == [{"name": "N", "quantity": 2, "final_sale": True}]

    @pytest.mark.parametrize("inp,expected", [
        ("2026-08-22", "August 22, 2026"),
        ("2026-08-22T00:00:00Z", "August 22, 2026"),
        (None, None),
        ("not-a-date", "not-a-date"),
    ])
    def test_format_date(self, inp, expected):
        assert format_date_human(inp) == expected


def json_blob(obj):
    import json
    return json.dumps(obj).lower()
