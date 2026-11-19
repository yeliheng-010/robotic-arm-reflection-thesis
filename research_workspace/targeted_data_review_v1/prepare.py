"""保留已观察成功集合，不伪造唯一标签或未测候选结果。"""
import hashlib
import json
from copy import deepcopy

SOURCE = 'expert_counterfactual_rule_continuation'
SEMANTICS = 'terminal_success_within_original_three_attempt_budget'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_input(messages):
    canonical = []
    for message in messages:
        content = message['content']
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            pass
        canonical.append(dict(role=message['role'], content=content))
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(encoded.encode()).hexdigest()


def validate_outcomes(raw, candidates):
    seen, successes = set(), []
    remaining = 3-raw['after_attempt']
    for outcome in raw['tested_outcomes']:
        key = outcome['action_id']
        require(key in candidates and key not in seen, 'Unknown or duplicated tested candidate')
        seen.add(key)
        candidate = candidates[key]
        require(candidate['kind'] == outcome['kind'], 'Candidate kind changed')
        require(candidate['state']['profile'] == outcome['profile'], 'Profile changed')
        terminal, immediate = outcome['terminal_success'], outcome['immediate_success']
        require(type(terminal) is bool and type(immediate) is bool, 'Outcome must be boolean')
        count = outcome['following_attempts']
        require(type(count) is int and 1 <= count <= remaining, 'Budget exceeded')
        require(not immediate or (terminal and count == 1), 'Inconsistent immediate success')
        require(not terminal or immediate or count > 1, 'Delayed success lacks continuation')
        if terminal:
            successes.append(key)
    require(sorted(successes) == raw['successful_actions'], 'Declared success set changed')
    return sorted(successes), sorted(seen)


def pack(raw):
    require(raw['input_hash'] == digest_input(raw['messages']), 'Input hash changed')
    require([m['role'] for m in raw['messages']] == ['system', 'user'], 'Invalid prompt roles')
    require(raw['source'] == SOURCE and raw['model'] is None, 'Incorrect supervision source')
    require(raw['label_semantics'] == SEMANTICS, 'Incorrect outcome horizon')
    require(raw['split'] == 'train_candidate' and not raw['test_used'], 'Nontraining source')
    require(raw['training_approved'] is False, 'Unexpected training approval')
    require(raw['after_attempt'] in (1, 2), 'Invalid decision position')
    body = json.loads(raw['messages'][1]['content'])
    candidates = {c['id']: c for c in body['candidates']}
    require(len(candidates) == len(body['candidates']) == raw['candidate_count'], 'Candidate count changed')
    successes, seen = validate_outcomes(raw, candidates)
    timing = {o['immediate_success'] for o in raw['tested_outcomes'] if o['terminal_success']}
    label = 'mixed' if len(timing) > 1 else 'immediate' if True in timing else 'delayed' if timing else 'none'
    return dict(id=raw['input_hash'], messages=deepcopy(raw['messages']),
        accepted_action_ids=successes, observed_unsuccessful_action_ids=sorted(set(seen)-set(successes)),
        untested_action_ids=sorted(set(candidates)-set(seen)), tested_outcomes=deepcopy(raw['tested_outcomes']),
        success_timing=label, remaining_attempts=3-raw['after_attempt'],
        group=f"targeted_collection_v1:{raw['seed']}", scene_id=raw['scene_id'],
        after_attempt=raw['after_attempt'], source=SOURCE, model=None, label_semantics=SEMANTICS,
        training_approved=False, split='train_candidate', test_used=False)


def partition(rows, *, held, old_train):
    result = {k: [] for k in ('positive_sets', 'single_success', 'multi_success', 'unresolved', 'quarantine')}
    seen = set()
    for raw in rows:
        row = pack(raw)
        require(row['id'] not in seen, 'Duplicate input requires explicit merge review')
        seen.add(row['id'])
        reason = 'evaluation_overlap' if row['id'] in held else 'old_train_overlap' if row['id'] in old_train else None
        if reason:
            result['quarantine'].append(dict(record=row, reason=reason))
            continue
        count = len(row['accepted_action_ids'])
        result['single_success' if count == 1 else 'multi_success' if count else 'unresolved'].append(row)
        if count:
            result['positive_sets'].append(row)
    return result


def sft_row(row):
    require(len(row['accepted_action_ids']) == 1, 'SFT view requires one observed successful action')
    assistant = dict(role='assistant', content=json.dumps({'action_id': row['accepted_action_ids'][0]}))
    return dict(messages=deepcopy(row['messages'])+[assistant])
