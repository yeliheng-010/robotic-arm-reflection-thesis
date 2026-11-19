from collections import Counter
import sys
import numpy as np
import spatialmath as sm
from action_space_audit_v1.scene import opened
from action_space_audit_v1.common import ROOT, read, save, sha, verify
from action_space_audit_v1.cache import reused
from goal_endpoints import inspect, CONFIGS
from model_grasp_gpu_v1.planning import deadline


def cached_for(proposal, cache):
    for saved in cache:
        rows = reused(proposal,saved)
        if rows is not None:
            return rows
    return None


def measure(flow, row, *, item, configs, origin):
    pose = sm.SE3(np.asarray(row['proposal']['pose']))
    for config in configs:
        yield dict(action_id=row['id'],config=list(config),origin=origin,
                   **inspect(flow,pose,config=config,item=item))


def collect(flow, catalogue, *, manifest, cache, rows, completed):
    for row in catalogue:
        if row['proposal']['status']!='proposal':
            completed.append(row['id'])
            continue
        previous = cached_for(row['proposal'],cache)
        current = [dict(r,action_id=row['id'],origin='reused') for r in previous] if previous is not None else \
            measure(flow,row,item=manifest['case']['item'],configs=CONFIGS,origin='new')
        rows.extend(current)
        completed.append(row['id'])


def probe(manifest, catalogue):
    rows,completed = [],[]
    cache = read(ROOT/'cached_endpoints.json')
    exhausted = False
    with opened(manifest) as flow:
        try:
            with deadline(manifest['endpoint_seconds']):
                collect(flow,catalogue,manifest=manifest,cache=cache,rows=rows,completed=completed)
        except TimeoutError:
            exhausted = True
    return rows,completed,exhausted


def audit(manifest, catalogue):
    previous = read(ROOT/'probe/endpoints.json')
    selected = {r['id']:r for r in catalogue}
    rows = []
    with opened(manifest) as flow,deadline(manifest['endpoint_seconds']):
        for action_id in dict.fromkeys(r['action_id'] for r in previous):
            old = [r for r in previous if r['action_id']==action_id]
            if old[0]['origin']=='reused':
                verified = cached_for(selected[action_id]['proposal'],read(ROOT/'cached_endpoints.json'))
                rows.extend(dict(r,action_id=action_id,origin='reused') for r in verified)
            else:
                rows.extend(measure(flow,selected[action_id],item=manifest['case']['item'],
                                    configs=[r['config'] for r in old],origin='new'))
    # 归一化tuple/list，仅比较JSON中的实际审计表示。
    save(ROOT/'audit/endpoints.json',rows)
    assert read(ROOT/'audit/endpoints.json')==previous
    source = read(ROOT/'probe/result.json')
    return rows,source['completed_actions'],source['budget_exhausted']


def counts(rows, catalogue):
    return dict(actions=len(catalogue),endpoint_checks=len(rows),
         new_checks=sum(r['origin']=='new' for r in rows),reused_checks=sum(r['origin']=='reused' for r in rows),
         safe_endpoints=sum(r['ok'] for r in rows),safe_actions=len({r['action_id'] for r in rows if r['ok']}),
         reasons=dict(Counter(r.get('reason') or 'ok' for r in rows)),
         geometry_rejections=dict(Counter(r['proposal']['reason'] for r in catalogue
                                          if r['proposal']['status']!='proposal')))


def main(mode):
    manifest,catalogue = verify(),read(ROOT/'catalogue.json')
    assert mode in ('probe','audit')
    rows,completed,exhausted = probe(manifest,catalogue) if mode=='probe' else audit(manifest,catalogue)
    if mode=='probe':
        save(ROOT/mode/'endpoints.json',rows)
    result = dict(counts(rows,catalogue),passed=True,complete=len(completed)==len(catalogue),
         completed_actions=completed,budget_exhausted=exhausted,integration_identical=True,
         physical_attempts=0,model_calls=0,independent=mode=='audit',
         endpoints_sha256=sha(ROOT/mode/'endpoints.json'))
    save(ROOT/mode/'result.json',result)
    print({k:v for k,v in result.items() if k!='completed_actions'},flush=True)


if __name__=='__main__':
    main(sys.argv[1])
