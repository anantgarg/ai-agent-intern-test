from app.rag import (
    load_documents,
    split_into_chunks,
    build_search_index,
    search_knowledge_base,
    authority_score,
    rank_results,
    detect_conflict,
)



def test_load_documents():
    documents = load_documents()

    assert len(documents) == 14


def test_document_has_required_structure():
    documents = load_documents()

    document = documents[0]

    assert "filename" in document
    assert "metadata" in document
    assert "content" in document


def test_metadata_is_preserved():
    documents = load_documents()

    current_returns = next(
        document
        for document in documents
        if document["filename"] == "01-returns-policy-current.md"
    )

    assert current_returns["metadata"]["status"] == "active"
    assert current_returns["metadata"]["audience"] == "customer"
    assert current_returns["metadata"]["policy_authority"] == "official"


def test_document_is_split_into_chunks():
    documents = load_documents()

    current_returns = next(
        document
        for document in documents
        if document["filename"] == "01-returns-policy-current.md"
    )

    chunks = split_into_chunks(current_returns)

    assert len(chunks) > 1


def test_chunks_preserve_source_metadata():
    documents = load_documents()

    current_returns = next(
        document
        for document in documents
        if document["filename"] == "01-returns-policy-current.md"
    )

    chunks = split_into_chunks(current_returns)

    first_chunk = chunks[0]

    assert first_chunk["filename"] == "01-returns-policy-current.md"
    assert "heading" in first_chunk
    assert "metadata" in first_chunk
    assert "text" in first_chunk


def test_search_finds_returns_policy():
    vectorizer, chunks, matrix = build_search_index()

    results = search_knowledge_base(
        "How long do I have to return a regular purchase?",
        vectorizer,
        chunks,
        matrix,
        top_k=10,
    )

    assert len(results) > 0

    filenames = [result["filename"] for result in results]

    assert "01-returns-policy-current.md" in filenames


def test_search_returns_scores():
    vectorizer, chunks, matrix = build_search_index()

    results = search_knowledge_base(
        "What is the return policy?",
        vectorizer,
        chunks,
        matrix,
        top_k=3,
    )

    assert len(results) > 0

    for result in results:
        assert "score" in result
        assert isinstance(result["score"], float)

def test_active_official_content_beats_superseded_content():
    active_chunk = {
        "metadata": {
            "status": "active",
            "policy_authority": "official",
            "audience": "customer",
        }
    }

    legacy_chunk = {
        "metadata": {
            "status": "superseded",
            "policy_authority": "official",
            "audience": "customer",
        }
    }

    assert authority_score(active_chunk) > authority_score(legacy_chunk)


def test_rank_results_prefers_authoritative_content():
    results = [
        {
            "filename": "02-returns-policy-legacy.md",
            "heading": "Legacy return window",
            "metadata": {
                "status": "superseded",
                "policy_authority": "official",
                "audience": "customer",
            },
            "text": "Old return policy",
            "score": 0.95,
        },
        {
            "filename": "01-returns-policy-current.md",
            "heading": "Standard return window",
            "metadata": {
                "status": "active",
                "policy_authority": "official",
                "audience": "customer",
            },
            "text": "Current return policy",
            "score": 0.85,
        },
    ]

    ranked = rank_results(results)

    assert ranked[0]["filename"] == "01-returns-policy-current.md"

def test_detect_conflict_with_multiple_active_official_sources():
    results = [
        {
            "filename": "policy-a.md",
            "metadata": {
                "status": "active",
                "policy_authority": "official",
            },
            "text": "Return window is 30 days.",
        },
        {
            "filename": "policy-b.md",
            "metadata": {
                "status": "active",
                "policy_authority": "official",
            },
            "text": "Return window is 45 days.",
        },
    ]

    assert detect_conflict(results) is True


def test_no_conflict_with_single_authoritative_source():
    results = [
        {
            "filename": "policy-a.md",
            "metadata": {
                "status": "active",
                "policy_authority": "official",
            },
            "text": "Return window is 30 days.",
        }
    ]

    assert detect_conflict(results) is False