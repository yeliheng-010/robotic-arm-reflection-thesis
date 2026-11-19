"""只读复核240任务，定位新旧模型分歧、末次反馈和训练情境缺口。"""
import importlib.util
import json
from collections import Counter
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from common import ROOT as SOURCE, METHODS, read, save, sha, verify
from report import load, helper
from loopstudy.actions import candidates

ROOT = SOURCE.parent/'failure_analysis_v2'
TRAIN = SOURCE.parent/'set_sft_v1/train.json'
PACK = SOURCE.parent/'targeted_data_review_v1/output_v1'
EARLY_PHASES = ('grasp_approach', 'grasp_pose', 'carry_lift')
EXPECTED_TASKS = 240
EXPECTED_CONDITIONS = 60


def previous_helpers():
    path = SOURCE.parent/'failure_analysis_v1/analyze.py'
    spec = importlib.util.spec_from_file_location('prior_readonly_analysis', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context(row):
    prompt = json.loads(row['messages'][1]['content'])
    error = prompt['error']
    evidence = error.get('evidence', {})
    visible = [k for k in ('grasp_residual_xy','placement_residual_xy') if k in evidence]
    return dict(error=error.get('error_type'),
                phase=evidence.get('motion_context', {}).get('phase', 'unknown'),
                visible_residual_fields=visible)


def kind(candidate):
    name = candidate['kind']
    return name+':'+candidate['state']['profile'] if name=='descent_route' else name


def coverage(rows):
    occurrences, weights, situations, missing = Counter(), Counter(), Counter(), []
    for row in rows:
        prompt = json.loads(row['messages'][1]['content'])
        selected = [c for c in prompt['candidates'] if c['id'] in row['accepted_action_ids']]
        assert len(selected) == len(row['accepted_action_ids']) > 0
        ctx = context(row)
        situations[(ctx['error'],ctx['phase'],bool(ctx['visible_residual_fields']))] += 1
        for candidate in selected:
            occurrences[kind(candidate)] += 1
            weights[kind(candidate)] += Fraction(1,len(selected))
        if not ctx['visible_residual_fields']:
            missing.append(dict(id=row['id'], **ctx, targets=[kind(c) for c in selected]))
    assert sum(weights.values()) == len(rows)
    return dict(inputs=len(rows), responses=sum(occurrences.values()),
        multi_inputs=sum(len(r['accepted_action_ids'])>1 for r in rows),
        target_occurrences=occurrences, input_equivalent_weights={k:float(v) for k,v in weights.items()},
        contexts=[dict(error=k[0],phase=k[1],has_residual=k[2],inputs=v) for k,v in situations.items()],
        missing_residual=missing,
        early_missing_residual_inputs=sum(r['phase'] in EARLY_PHASES for r in missing))


def terminal(result):
    if result['success']:
        return None
    step = result['attempts'][-1]
    feedback = step['feedback'] or {}
    menu = candidates(feedback, step['state'], result['decisions'])
    return dict(attempt=step['index'], exhausted=len(result['attempts'])==3,
        error=feedback.get('error_type'), phase=feedback.get('evidence',{}).get('motion_context',{}).get('phase'),
        hypothetical_next_candidates=[dict(id=c['id'],kind=kind(c),changes=c['changes']) for c in menu],
        physical_continuation_tested=False)


def detail(group, old):
    result = {}
    for method, value in group.items():
        compact = old.compact(value)
        compact['terminal'] = terminal(value)
        compact['menus'] = [[dict(id=c['id'],kind=kind(c),changes=c['changes'])
                            for c in d['candidates']] for d in value['decisions']]
        result[method] = compact
    return result


def compare_groups(grouped, old):
    totals, differences, common_failures = {}, [], []
    for scene, group in grouped.items():
        details = {}
        for left,right in combinations(METHODS,2):
            name = left+'_vs_'+right
            value = old.compare(group[left],group[right])
            totals.setdefault(name,Counter()).update(value['counts'])
            if value['differences']:
                details[name] = value['differences']
        if details:
            differences.append(dict(scene=scene,differences=details))
        if not group['previous159']['success'] and not group['new189']['success']:
            common_failures.append(dict(scene=scene,methods=detail(group,old),differences=details))
    return totals, differences, common_failures


def training_review():
    rows = read(TRAIN)
    assert len(rows)==189 and sum(len(r['accepted_action_ids']) for r in rows)==197
    unresolved = [json.loads(s) for s in (PACK/'unresolved.jsonl').read_text().splitlines()]
    unresolved_missing = [dict(id=r['id'], **context(r), group=r['group'],
        tested_actions=len(r['tested_outcomes']), untested_actions=len(r['untested_action_ids']))
        for r in unresolved if not context(r)['visible_residual_fields']]
    prior = [json.loads(s) for s in (SOURCE.parent/'data_review_v1/output_v1/train_combined.jsonl').read_text().splitlines()]
    assert len(prior)==159
    assert all(r['messages']==p['messages'][:-1] and r['accepted_action_ids']==
               [json.loads(p['messages'][-1]['content'])['action_id']] for r,p in zip(rows[:159],prior))
    return dict(original159=coverage(rows[:159]),new30=coverage(rows[159:]),combined189=coverage(rows),
                unresolved_missing_residual=unresolved_missing)


def verify_all(manifest):
    rows, results = load(manifest['entries'])
    assert len(rows)==len(results)==EXPECTED_TASKS
    report = read(SOURCE/'verification.json')
    assert report['passed'] and report['complete'] and report['expected']==EXPECTED_TASKS
    assert rows==report['rows']
    old, physical, noisy = helper('route_loop_v1','verify'), helper('route_loop_v1','compare'), helper('noisy_loop_v1','verify')
    checks = dict(paired_initials=old.paired_initials(results),
        **physical.compare_physics(results), **noisy.paired_methods(results),
        candidate_checks=old.candidate_checks(results))
    assert all(report[k]==v for k,v in checks.items())
    grouped = {}
    for entry,result in zip(manifest['entries'],results):
        grouped.setdefault(entry['item']['scene_id'],{})[entry['method']] = result
    assert len(grouped)==EXPECTED_CONDITIONS
    assert all(set(g)==set(METHODS) for g in grouped.values())
    return rows,grouped,checks


def sources(manifest):
    paths = [SOURCE/'manifest.json',SOURCE/'verification.json',TRAIN,
             PACK/'unresolved.jsonl',PACK/'positive_sets.jsonl',
             SOURCE.parent/'failure_analysis_v1/analyze.py',
             SOURCE.parent/'set_sft_v1/verification.json']
    paths += list(ROOT.glob('*.py')) + list(ROOT.glob('*.sbatch'))
    for entry in manifest['entries']:
        paths += [SOURCE/'tasks'/entry['uid']/name for name in ('result.json','summary.json')]
    return {str(p):sha(p) for p in paths}


def main():
    assert not (ROOT/'summary.json').exists(), 'Analysis output already exists'
    manifest = verify()
    identities = sources(manifest)
    rows, grouped, checks = verify_all(manifest)
    comparisons, differences, failures = compare_groups(grouped, previous_helpers())
    assert len(failures)==4
    training = training_review()
    summary = dict(passed=True,audited_tasks=len(rows),conditions=len(grouped),
        failed_method_tasks=sum(not r['success'] for r in rows),
        common_failure_conditions=[r['scene'] for r in failures],
        comparisons=comparisons,physical_checks=checks,
        training_coverage=training,manifest_sha256=sha(SOURCE/'manifest.json'),
        verification_sha256=sha(SOURCE/'verification.json'),physical_reruns=0,
        new_training_samples=0,model_calls=0,test_used=False)
    save(ROOT/'cases.json',failures)
    save(ROOT/'differences.json',differences)
    save(ROOT/'source_hashes.json',identities)
    assert all(sha(p)==h for p,h in identities.items()), 'Analysis mutated its input'
    save(ROOT/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='training_coverage'},ensure_ascii=False))


if __name__=='__main__':
    main()
