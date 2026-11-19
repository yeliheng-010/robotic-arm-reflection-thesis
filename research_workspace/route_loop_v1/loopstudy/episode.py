"""物理尝试独立重置；决定和实际执行分开留档。"""
import json
from pathlib import Path
from stability.collection_status import atomic
from recovery.references import collision_context
from semanticfix2.context import enrich,project
from semanticfix2.protocol import sha
from loopstudy.actions import initial,candidates,canonical
from loopstudy.selection import select
from loopstudy.design import configuration,MAX_ATTEMPTS


def attempt(item,state,*,directory,index):
    from loopstudy.runtime import engine_class
    config = configuration(item)
    engine = engine_class(state)(scenario_config=config,max_attempts=1,headless=True,task_parser='rule')
    trace = dict(steps=0,source_path=[],divider_contacts={})
    try:
        with collision_context(dict(item,enabled=True),trace):
            engine.run(source=item['source'],destination=item['destination'],seed=item['seed'],
                fault='none',output=directory,method='retry',context='route_loop_v1')
    finally:
        engine.close()
    result = json.loads((directory/'result.json').read_text())
    record = result['records'][0]
    feedback = project(enrich(record['error'],attempt=index),config,attempt=index) if record['error'] else None
    return dict(index=index,state=canonical(state),success=result['success'],feedback=feedback,
                result_sha256=sha(directory/'result.json'),result_path=str(directory/'result.json'))


def decide(item,step,history):
    state,report = step['state'],step['feedback']
    decision = dict(after_attempt=step['index'],before=state,feedback=report)
    if item['arm']=='retry':
        decision.update(candidates=[],selected=dict(id='retry',state=state,changes={},kind='retry'),model=None)
        return decision
    rows = candidates(report,state,history,legacy=item['arm']=='old_rule')
    decision['candidates']=rows
    if not rows:
        return dict(decision,selected=None,invalid='Candidate set exhausted')
    return dict(decision,**select(item['arm'],decision,history))


def run(item,directory):
    directory.mkdir(parents=True,exist_ok=False)
    status = dict(item=item,status='running',success=False,attempts=[],decisions=[],
                  test_used=False,training_approved=False,scenario=configuration(item))
    state = initial()
    atomic(directory/'progress.json',status)
    for index in range(1,MAX_ATTEMPTS+1):
        step = attempt(item,state,directory=directory/f'attempt_{index}',index=index)
        status['attempts'].append(step)
        status['success']=step['success']
        atomic(directory/'progress.json',status)
        if step['success'] or index==MAX_ATTEMPTS:
            break
        decision = decide(item,step,status['decisions'])
        status['decisions'].append(decision)
        atomic(directory/'progress.json',status)
        if decision['selected'] is None:
            status['status']='service_error' if decision.get('event',{}).get('service_error') else 'invalid'
            break
        state = decision['selected']['state']
    if status['status']=='running':
        status['status']='completed'
    atomic(directory/'result.json',status)
    atomic(directory/'progress.json',status)
    return status
