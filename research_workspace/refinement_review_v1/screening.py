"""仅生成待审候选；物理成功不自动等于解释正确或训练准入。"""
import copy
import hashlib
import json
import math
from collections import defaultdict


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def residual_check(residual, current, proposed):
    if residual is None:
        return {'measurement': 'missing'}
    delta = [proposed[i]-current[i] for i in range(2)]
    norm = lambda v: math.sqrt(sum(x*x for x in v))
    return dict(measurement='present', residual=list(residual), delta=delta,
                dot=sum(a*b for a, b in zip(delta, residual)), before_norm=norm(residual),
                proxy_after_norm=norm([residual[i]+delta[i] for i in range(2)]),
                interpretation='Linear diagnostic only, not a physical success predictor')


def visible_state(run, index):
    event = run['feedback'][index]
    return copy.deepcopy(dict(instruction=run['instruction'], error=event['projected'],
                              parameters=run['records'][index]['parameters'], history=event['history']))


def normalize_state(state):
    value = copy.deepcopy(state)
    value['history'] = [dict(error=h['error'], reflection={'changes': h['reflection']['changes']})
                        for h in value.get('history', [])]
    return value


def sample_key(state, changes, *, source):
    return fingerprint(dict(state=normalize_state(state), changes=changes, source=source))


def candidate_indices(records):
    return [i for i, (before, after) in enumerate(zip(records, records[1:]))
            if not before['accepted'] and after['accepted'] and after.get('physical_success')
            and (before.get('reflection') or {}).get('changes')]


def transition(run, index):
    before, after = run['records'][index:index+2]
    answer = before['reflection']
    state = visible_state(run, index)
    source = 'llm' if run['arm'].startswith('flash') else 'rule_expert'
    checks = {}
    for field, measurement in (('grasp_offset', 'grasp_residual_xy'), ('place_offset', 'placement_residual_xy')):
        if field in answer['changes']:
            checks[field] = residual_check(state['error']['evidence'].get(measurement),
                                           before['parameters'][field], answer['changes'][field])
    event = run['events'][index] if source == 'llm' else None
    return dict(id=f"{run['id']}/a{index+1}", run_id=run['id'], case=run['case'], arm=run['arm'],
                repeat=run['repeat'], attempt=index+1, source=source, model=event['request']['model'] if event else None,
                visible_state_sha256=fingerprint(normalize_state(state)),
                sample_sha256=sample_key(state, answer['changes'], source=source),
                request_sha256=fingerprint(event['request']) if event else None,
                answer=answer, residual_checks=checks, next_accepted=after['accepted'],
                next_error=(after.get('error') or {}).get('error_type'),
                evidence_refs={p: sha for p, sha in run['source_files'].items()},
                deployment_role='development_only', training_approved=False)


def catalogue(data):
    candidates, all_transitions, groups = [], [], defaultdict(list)
    for run in data['runs']:
        positives = candidate_indices(run['records'])
        for index, record in enumerate(run['records'][:-1]):
            if not record.get('reflection'):
                continue
            row = transition(run, index)
            all_transitions.append(row)
            groups[row['sample_sha256']].append(row)
            if index not in positives:
                continue
            control = data['controls'][str(run['case'])]
            row['same_budget_retry_success'] = control['summary']['success']
            row['family'] = {k: run['summary']['task'][k] for k in ('source', 'destination', 'seed')}
            row['candidate_status'] = 'awaiting_semantic_review'
            candidates.append(row)
    conflicts = {key for key, rows in groups.items() if len({r['next_accepted'] for r in rows}) > 1}
    for row in candidates:
        row['same_observation_action_conflict'] = row['sample_sha256'] in conflicts
    return candidates, all_transitions, groups
