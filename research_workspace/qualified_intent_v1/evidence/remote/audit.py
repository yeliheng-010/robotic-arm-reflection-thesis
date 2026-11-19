"""独立重建模型意图、提示差异和全部端点结果，禁止任务积分。"""
import json
from qualified_intent_v1.common import ROOT, PROJECT, RUN as ORIGINAL, read, save, sha
from qualified_intent_v1.model_v2 import OUTPUT as COMPACT
from qualified_intent_v1.model_v3 import OUTPUT, verified, CLARIFICATION
from qualified_intent_v1.endpoints import check
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.model import parse


def prompt_pair(seed):
    old, new = read(COMPACT/f'{seed}/request.json'), read(OUTPUT/f'{seed}/request.json')
    assert old['image'] == new['image']
    assert new['messages'][0]['content'] == old['messages'][0]['content']+CLARIFICATION
    left, right = [json.loads(row['messages'][1]['content']) for row in (old, new)]
    right.pop('output_constraint')
    for action in right['actions']:
        action['args_spec'] = action.pop('allowed_values')
    assert left == right
    old_result = read(COMPACT/f'{seed}/validated.json')
    assert old_result['valid'] is False
    try:
        parse(read(COMPACT/f'{seed}/response.json'))
    except ValueError:
        return dict(same_observations=True, same_choices=True, original_schema_valid=False)
    raise AssertionError('Old response unexpectedly passed')


def evaluate(entry, cases):
    seed, folder = entry['seed'], OUTPUT/str(entry['seed'])
    paired = prompt_pair(seed)
    action = parse(read(folder/'response.json'))['action']
    assert action == read(folder/'validated.json')['action']
    source = read(ORIGINAL/f'{seed}/observation.json')
    proposal = propose(source['target_points'], source['nominal'], action)
    assert proposal == read(folder/'proposal.json')
    recorded = read(folder/'private_endpoints.json')
    rebuilt = check(cases[str(seed)], proposal, seed=seed)
    assert rebuilt == recorded
    return dict(seed=seed, prompt_pair=paired, valid=True, grasp_endpoint_passing=rebuilt['passing'],
        branches=len(rebuilt['rows']), independent_rebuild_identical=True,
        observation_source='Predicted SAM mask and noisy depth', full_path_verified=False)


def main():
    manifest = verified()
    frozen = {str(p): sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    cases = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases']
    rows = [evaluate(entry, cases) for entry in manifest['entries']]
    assert all(sha(p) == h for p, h in frozen.items())
    verified()
    result = dict(passed=True, rows=rows, original_schema_valid=0, revised_schema_valid=2,
        physical_attempts=0, training_runs=0, model_calls_this_audit=0, independent_process=True,
        identities=frozen, audit_source_sha256=sha(ROOT/'audit.py'))
    save(OUTPUT/'audit_result.json', result)
    print({k: v for k, v in result.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
