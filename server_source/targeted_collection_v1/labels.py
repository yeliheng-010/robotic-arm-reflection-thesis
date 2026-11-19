"""保留多解和失败，隔离旧开发输入；不自动导出单标签SFT。"""
import json
from collections import defaultdict
from curation import input_digest
from loopstudy.selection import messages
from pilot_common import ROOT, read, sha
from policy import outcome_set


def prompt_for(trace, offset):
    d = trace['decisions'][offset]
    return messages(d['feedback'], d['before'], rows=d['candidates'], history=trace['decisions'][:offset])


def held_inputs():
    held, train = set(), set()
    old = ROOT.parent/'data_review_v1/output_v1/provenance.jsonl'
    for line in old.read_text().splitlines():
        row = json.loads(line)
        (train if row['split'] == 'train' else held).add(row['input_hash'])
    for folder in ('noisy_loop_v1', 'scene_expansion_v1', 'hard_cases_v1'):
        root = ROOT.parent/folder
        for item in read(root/'protocol.json')['items']:
            if folder != 'noisy_loop_v1' and item['split'] == 'train_candidate':
                continue
            trace = read(root/'tasks'/item['id']/'result.json')
            held.update(input_digest(prompt_for(trace, i)) for i in range(len(trace['decisions'])))
    source = ROOT.parent/'candidate_closed_loop_v2'
    for entry in read(source/'manifest.json')['entries']:
        trace = read(source/'tasks'/entry['uid']/'result.json')
        held.update(input_digest(prompt_for(trace, i)) for i in range(len(trace['decisions'])))
    return held, train


def records(value):
    result = []
    for node in value['nodes']:
        offset = node['after_attempt']-1
        traces = [read(p) for p in node['trajectories']]
        prompt = prompt_for(traces[0], offset)
        assert all(prompt_for(t, offset) == prompt for t in traces)
        outcomes = []
        for path, trace in zip(node['trajectories'], traces):
            d = trace['decisions'][offset]
            outcomes.append(dict(action_id=d['selected']['id'], kind=d['selected']['kind'],
                profile=d['selected']['state']['profile'], terminal_success=trace['success'],
                immediate_success=trace['attempts'][offset+1]['success'],
                following_attempts=len(trace['attempts'])-offset-1,
                trajectory_path=path, trajectory_sha256=sha(path)))
        result.append(dict(scene_id=value['scene']['id'], seed=value['scene']['seed'],
            after_attempt=offset+1, messages=prompt, input_hash=input_digest(prompt),
            candidate_count=len(traces[0]['decisions'][offset]['candidates']),
            tested_outcomes=outcomes, successful_actions=outcome_set(outcomes),
            source='expert_counterfactual_rule_continuation', model=None,
            label_semantics='terminal_success_within_original_three_attempt_budget',
            training_approved=False, split='train_candidate', test_used=False))
    return result


def summarize(rows):
    held, train = held_inputs()
    groups = defaultdict(list)
    for row in rows:
        row['heldout_input_overlap'] = row['input_hash'] in held
        row['old_train_input_overlap'] = row['input_hash'] in train
        groups[row['input_hash']].append(row)
    counts = dict(raw_nodes=len(rows), unique_inputs=len(groups), eval_overlap=0,
                  single_success=0, multiple_success=0, no_success=0,
                  contradictory_observations=0, old_train_overlap=0)
    for key, group in groups.items():
        successes, failures = set(), set()
        for row in group:
            for outcome in row['tested_outcomes']:
                (successes if outcome['terminal_success'] else failures).add(outcome['action_id'])
        counts['eval_overlap'] += key in held
        counts['old_train_overlap'] += key in train
        conflict = bool(successes & failures)
        counts['contradictory_observations'] += conflict
        if key not in held and not conflict:
            counts['single_success' if len(successes) == 1 else
                   'multiple_success' if successes else 'no_success'] += 1
    return counts
