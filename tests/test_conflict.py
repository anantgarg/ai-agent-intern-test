from app.retrieval.conflicts import detect_conflicts
from app.retrieval.loader import Document

def test_active_breeze_sources_conflict():
    meta={'status':'active','audience':'customer','policy_authority':'official'}
    hits=[
      (Document('11-product-care.md','Breeze Tumbler','body should be hand-washed',meta),.9),
      (Document('12-breeze-tumbler-product-card.md','Cleaning','all components are dishwasher safe',meta),.9)
    ]
    assert detect_conflicts(hits)
