"""一次静态会话只绑定已审计原始模型动作，不赋予执行权限。"""
import json
from pathlib import Path
from qualified_prompt_checkpoint_v1.protocol import read, save, sha, require

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
SOURCE = PROJECT / 'qualified_prompt_checkpoint_v2/run'
CAPS = dict(max_preflight_sessions=1, max_audit_replays=1, max_model_calls=0,
            max_physical_attempts=0, max_training_runs=0)


def source_action(source=SOURCE):
    from model_grasp_intent_v1.model import parse
    result, audit = read(source / 'result.json'), read(source / 'audit_result.json')
    action = parse(read(source / 'response.json'))['action']
    require(result['valid'] and result['status'] == 'novel_action_unchecked', 'source_not_novel')
    require(result['action'] == action and action['id'] == 'PROPOSE_GRASP', 'source_action_mismatch')
    require(audit['passed'] and audit['full_tensor_reencoding_equal'], 'source_not_audited')
    require(audit['checked'] == {key: result[key] for key in ('valid', 'action', 'status')}, 'audit_mismatch')
    history = json.loads(read(source / 'request.json')['messages'][1]['content'])['history']
    require(all(row['action'] != action for row in history), 'source_repeated')
    return action


def verify(run=RUN):
    manifest = read(run / 'manifest.json')
    for key, expected in CAPS.items():
        require(type(manifest[key]) is int and manifest[key] == expected, 'unauthorized_budget')
    for name, expected in manifest['identities'].items():
        require(sha(name) == expected, 'changed_frozen_source: ' + name)
    require(sha(run / 'input.json') == manifest['input_sha256'], 'input_not_bound')
    return manifest


def reserve(run=RUN):
    manifest = verify(run)
    save(run / 'preflight_claim.json', dict(consumed=1, input_sha256=manifest['input_sha256']))
