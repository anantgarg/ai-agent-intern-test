import argparse, json, re
from pathlib import Path
from app.config import KNOWLEDGE_BASE, ORDERS_FILE, EMBEDDING_MODEL, INDEX_DIR
from app.retrieval.loader import load_documents
from app.retrieval.index import VectorIndex
from app.retrieval.retriever import Retriever
from app.tools.order_lookup import OrderLookup
from app.memory.session import SessionStore
from app.observability.logger import JsonLogger
from app.agent import SupportAgent

ROOT=Path(__file__).resolve().parents[1]
VISIBLE=json.loads((ROOT/'evaluation/visible-cases.json').read_text())['cases']
CUSTOM=json.loads((ROOT/'evaluation/custom-cases.json').read_text())

def build_agent():
    idx=VectorIndex(EMBEDDING_MODEL,INDEX_DIR)
    docs=load_documents(KNOWLEDGE_BASE)
    idx.build(docs)
    return SupportAgent(Retriever(idx,8),OrderLookup(ORDERS_FILE),SessionStore(),"gpt-4.1-mini",JsonLogger())

def text_ok(text, phrases):
    t=text.lower()
    return all(p.lower() in t for p in phrases)

def evaluate_case(agent, case):
    session='eval-'+case['id']
    responses=[]
    traces=[]
    for msg in case['messages']:
        result=agent.answer(session,msg['content'])
        responses.append(result)
        traces.append(result.get('trace',{}))
    combined='\n'.join(r['answer'] for r in responses)
    exp=case['expect']
    checks=[]
    checks += [(f'include:{p}', p.lower() in combined.lower()) for p in exp.get('must_include',[])]
    checks += [(f'include_concept:{p}', concept_match(combined,p)) for p in exp.get('must_include_concepts',[])]
    checks += [(f'not_include:{p}', p.lower() not in combined.lower()) for p in exp.get('must_not_include',[])]
    checks += [(f'not_invent:{p}', p.lower() not in combined.lower()) for p in exp.get('must_not_invent',[])]
    checks += [(f'refuse:{p}', p.lower() not in combined.lower()) for p in exp.get('must_refuse_to_disclose',[])]
    source_text=' '.join(s['filename'] for r in responses for s in r.get('sources',[]))
    for src in exp.get('required_sources',[]): checks.append((f'source:{src}',src in source_text))
    forbidden=exp.get('forbidden_sources_as_authority',[])
    for src in forbidden: checks.append((f'forbidden_source:{src}', not re.search(re.escape(src),combined,re.I)))
    tool_expect=exp.get('tool')
    called=any(t.get('tool_called') for t in traces)
    if tool_expect=='order_lookup': checks.append(('tool_called',called))
    if tool_expect=='not_called': checks.append(('tool_not_called',not called))
    if tool_expect=='not_called_without_id': checks.append(('tool_not_called_without_id',not called))
    if 'handoff' in exp: checks.append(('handoff', all(r.get('handoff')==exp['handoff'] for r in responses[-1:])))
    if exp.get('tool_arguments'):
        expected=exp['tool_arguments']['order_id']
        checks.append(('tool_argument_order_id', any(t.get('tool',{}).get('arguments',{}).get('order_id')==expected for t in traces)))
    passed=sum(ok for _,ok in checks)
    return passed==len(checks), checks

def concept_match(text, concept):
    c=concept.lower(); t=text.lower()
    mappings={
      'canada is supported':['canada','supported'],
      '5–9 business days after dispatch':['5–9 business days','dispatch'],
      'duties or taxes are not prepaid':['duties','taxes','not prepaid'],
      'shipping to germany is not currently available':['germany','not currently available'],
      'final sale does not block damaged-item review':['final-sale','damaged'],
      'report within 7 days':['7 days'],
      'human review before approval':['human review','approval'],
      'the order is cancelled':['cancelled'],
      'it will not be shipped':['not be shipped'],
      'shipped with canada post':['shipped','canada post'],
      'delivery estimate is unavailable':['delivery estimate','unavailable'],
      'no lifetime warranty':['no','lifetime warranty'],
      'bags have 2 years':['bags','2 years'],
      'drinkware and travel accessories have 1 year':['drinkware','travel accessories','1 year'],
      'migration note is not authoritative':['migration note','not authoritative'],
      'standard policy is 30 days unless a valid exception applies':['30 calendar days'],
      'the agent cannot approve a return':['cannot approve','return'],
      'the supplied information is insufficient':['insufficient'],
      'human confirmation':['human confirmation'],
      'current official sources conflict':['official sources conflict'],
      'one says hand-wash the body':['hand-wash','body'],
      'one says all components are dishwasher safe':['all components','dishwasher safe'],
      'human confirmation or safest interim guidance':['human confirmation','safest'],
    }
    needed=mappings.get(c,[c])
    return all(x in t for x in needed)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Use the configured OpenAI model')
    args=parser.parse_args()
    if args.live:
        print('Live evaluation is supported by setting OPENAI_API_KEY and running the API/evaluator with the live agent.')
    agent=build_agent()
    rows=[]
    for case in VISIBLE:
        ok,checks=evaluate_case(agent,case)
        rows.append((case['id'],case['category'],ok,checks))
    print('Aster & Row behavior evaluation')
    print('='*70)
    for cid,cat,ok,checks in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} [{cat}] {sum(x[1] for x in checks)}/{len(checks)} assertions")
        for name,result in checks:
            print(f"    {'✓' if result else '✗'} {name}")
    print('\nSummary by category')
    cats={}
    for _,cat,ok,_ in rows: cats.setdefault(cat,[0,0]); cats[cat][0]+=int(ok); cats[cat][1]+=1
    for cat,(p,n) in cats.items(): print(f"  {cat}: {p}/{n}")
    print(f"\nOverall: {sum(ok for _,_,ok,_ in rows)}/{len(rows)} visible cases passed")
    print(f"Additional original cases available: {len(CUSTOM)}")

if __name__=='__main__': main()
