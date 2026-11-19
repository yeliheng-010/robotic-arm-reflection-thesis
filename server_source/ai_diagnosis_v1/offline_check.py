"""只读旧记录并导出接口样例；没有模型请求、仿真或实际动作。"""
import hashlib
import json
from pathlib import Path
from boundary import build_request
from prompts import messages

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
SOURCE = WORKSPACE/'scene_pair_route_v3'
EXPECTED_MANIFEST = 'f9c4f178756ce13a4c3703530d71930feb2c154729caab5861ce09b9d70fc829'
AUDITED_SOURCES = (
    'scene_pair_v2/pair_run.py', 'scene_pair_v2/pair_runtime.py', 'scene_pair_v2/drop_recovery.py',
    'scene_diversity_v2/sd_physics.py', 'active_observation_model_v2/am_policy.py',
    'active_observation_model_v2/am_decision.py', 'active_observation_model_v2/am_client.py',
    'active_observation_model_v2/worker.py', 'active_observation_pilot_v1/ap_sensor.py',
    'active_observation_pilot_v1/ap_policy.py', 'bounded_reflection_v1/bounded/candidates.py',
    'route_loop_v1/loopstudy/actions.py', 'route_loop_v1/loopstudy/episode.py',
    'route_loop_v1/loopstudy/runtime.py', 'controlled/feedback.py',
    'feedback_semantics_v2/semanticfix2/context.py', 'scene_pair_route_v3/goal_runtime.py',
    'scene_pair_route_v2/waypoint_runtime.py', 'scene_pair_route_v2/waypoint_paths.py',
    'scene_pair_contact_diagnostic_v1/contact_capture.py',
    'scene_pair_contact_diagnostic_v1/contact_data.py',
)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def example(case):
    folder = SOURCE/'physics'/case['id']
    ledger_path, record_path = folder/'result.json', folder/'attempt_3/result.json'
    ledger = read(ledger_path)
    assert ledger['steps'][-1]['result_sha256'] == sha(record_path)
    assert ledger['manifest_sha256'] == EXPECTED_MANIFEST
    record = read(record_path)['records'][0]
    request = build_request(ledger, record)
    assert request['budget']['executions_remaining'] == 0
    assert [r['id'] for r in request['actions']] == ['STOP']
    body = json.dumps(request, ensure_ascii=False)
    for forbidden in ('error_type', 'object_dropped', 'contact_bounds_world',
                      'initial_qpos', 'physical_success', 'simulation_ground_truth', case['id']):
        assert forbidden not in body, forbidden
    bundle = dict(request=request, direct_messages=messages(request, mode='direct'),
                  diagnostic_messages=messages(request, mode='diagnostic'))
    save(ROOT/'examples'/(case['id']+'.json'), bundle)
    return dict(id=case['id'],ledger_sha256=sha(ledger_path), record_sha256=sha(record_path),
                remaining_executions=0, legal_actions=['STOP'], model_called=False,
                source_use='used_seed_development_interface_example')


def main():
    assert sha(SOURCE/'manifest.json') == EXPECTED_MANIFEST
    before = {name: sha(WORKSPACE/name) for name in AUDITED_SOURCES}
    (ROOT/'examples').mkdir(exist_ok=False)
    cases = [c for c in read(SOURCE/'manifest.json')['cases'] if not c['reused_success']]
    rows = [example(case) for case in cases]
    assert len(rows) == 2
    assert before == {name: sha(WORKSPACE/name) for name in AUDITED_SOURCES}
    save(ROOT/'OFFLINE_VERIFICATION.json', dict(passed=True, kind='offline_boundary_only',
         cases=rows, source_sha256=before, original_manifest_sha256=EXPECTED_MANIFEST,
         model_calls=0, physics_attempts=0, training_runs=0, live_integration_ready=False,
         implementation_sha256={p.name: sha(p) for p in ROOT.glob('*.py')}))
    print('Offline boundary verified: 2 exhausted ledgers; 21 source identities unchanged; no model or physics')


if __name__ == '__main__':
    main()
