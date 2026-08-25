from app.retrieval.loader import load_documents
from app.retrieval.retriever import authority
from app.config import KNOWLEDGE_BASE

def test_all_kb_files_are_indexable():
    docs=load_documents(KNOWLEDGE_BASE)
    assert len(docs)>=14
    assert all(d.filename and d.heading and d.text for d in docs)

def test_front_matter_is_preserved():
    docs=load_documents(KNOWLEDGE_BASE)
    current=next(d for d in docs if d.filename=='01-returns-policy-current.md')
    assert current.metadata['status']=='active'
    assert current.metadata['policy_authority']=='official'

def test_current_official_customer_source_outranks_internal_draft():
    active={'status':'active','audience':'customer','policy_authority':'official'}
    internal={'status':'draft','audience':'internal','policy_authority':'none','customer_answering':'false'}
    assert authority(active)>authority(internal)
