"""全分母审计、跨方法初态配对、决策复算和转移来源清单。"""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path('/home/yeliheng/grasp_server/route_loop_v1')
sys.path.insert(0,str(ROOT))
from loopstudy.protocol import verify
from loopstudy.audit import audit
from loopstudy.actions import candidates
from loopstudy.design import ARMS,ANCHOR_SEED
from semanticfix2.protocol import sha
from stability.collection_status import atomic


def read_item(item):
    directory = ROOT/'tasks'/item['id']
    result = json.loads((directory/'result.json').read_text())
    row = json.loads((directory/'summary.json').read_text())
    assert row['audit']==audit(result,item) and row['success']==result['success']
    assert row['attempts']==len(result['attempts']) and row['id']==item['id']
    assert row['arm']==item['arm'] and row['seed']==item['seed'] and row['factor']==item['factor']
    return result,dict(**row,result_sha256=sha(directory/'result.json'))


def paired_initials(results):
    references,checks = {},0
    for value in results:
        key = value['item']['scene_id']
        raw = json.loads(Path(value['attempts'][0]['result_path']).read_text())['records'][0]
        reference = references.setdefault(key,raw)
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(reference['candidate_trace'][field],raw['candidate_trace'][field],atol=1e-8,rtol=0)
        checks += 1
    return checks


def transition_rows(results):
    rows = []
    for value in results:
        for offset,decision in enumerate(value['decisions']):
            if decision['selected'] is None or offset+1>=len(value['attempts']):
                continue
            after = value['attempts'][offset+1]
            if not after['success']:
                continue
            rows.append(dict(task_id=value['item']['id'],arm=value['item']['arm'],
                source=decision.get('source','retry'),before_attempt=offset+1,after_attempt=offset+2,
                feedback=decision['feedback'],selected=decision['selected'],
                before_sha256=value['attempts'][offset]['result_sha256'],after_sha256=after['result_sha256'],
                training_approved=False,explanation_source='deterministic_action_template'))
    return rows


def candidate_checks(results):
    checks = 0
    for value in results:
        if value['item']['arm'] not in ('new_rule','hybrid'):
            continue
        for index,decision in enumerate(value['decisions']):
            expected = candidates(decision['feedback'],decision['before'],value['decisions'][:index])
            assert expected==decision['candidates']
            checks += 1
    return checks


def metrics(rows):
    result = []
    for group in ('all','anchor','extension'):
        for arm in ARMS:
            subset = [r for r in rows if r['arm']==arm and (group=='all' or (r['seed']==ANCHOR_SEED)==(group=='anchor'))]
            result.append(dict(group=group,arm=arm,n=len(subset),successes=sum(r['success'] for r in subset),
                attempts=sum(r['attempts'] for r in subset),calls=sum(r['calls'] for r in subset),
                invalid=sum(r['invalid'] for r in subset),service_errors=sum(r['service_errors'] for r in subset)))
    return result


def main():
    protocol = verify()
    loaded = [read_item(i) for i in protocol['items'] if (ROOT/'tasks'/i['id']/'summary.json').exists()]
    results,rows = [x[0] for x in loaded],[x[1] for x in loaded]
    transitions = transition_rows(results)
    summary = dict(expected=len(protocol['items']),completed=len(rows),metrics=metrics(rows),rows=rows,
        paired_initials=paired_initials(results),common_generator_checks=candidate_checks(results),
        successful_transitions=len(transitions),training_approved=0,test_used=False,
        protocol_sha256=sha(ROOT/'protocol.json'))
    atomic(ROOT/'verification.json',summary)
    atomic(ROOT/'transitions.json',dict(rows=transitions,training_approved=0))
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))


if __name__=='__main__':
    main()
