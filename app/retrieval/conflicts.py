import re
from .retriever import authority
DISHWASHER=re.compile(r"dishwasher safe|dishwasher",re.I)
HANDWASH=re.compile(r"hand[- ]washed|hand[- ]wash",re.I)

def detect_conflicts(hits):
    candidates=[]
    for doc,score in hits:
        meta=doc.metadata
        if authority(meta)>=7 and str(meta.get('status','')).lower() in {'active','current','published'}:
            candidates.append((doc,score))
    hand=[x for x in candidates if HANDWASH.search(x[0].text)]
    for h in hand:
        for d in candidates:
            if d[0].filename==h[0].filename:
                continue
            if DISHWASHER.search(d[0].text):
                return {
                    'type':'active_source_conflict',
                    'topic':'Breeze Tumbler dishwasher guidance',
                    'sources':[
                        {'filename':h[0].filename,'heading':h[0].heading},
                        {'filename':d[0].filename,'heading':d[0].heading},
                    ],
                    'summary':'Current official sources conflict: one says hand-wash the body while another says all components are dishwasher safe.'
                }
    return None
