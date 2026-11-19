"""固定请求边界、一次性预算和结果分类；不提供规划入口。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
CHECKPOINT = ('输出前逐项比较拟选动作与history中所有已拒绝动作的完整参数。'
              '不要重复任何已拒绝动作；根据相同观测自主选择另一个白名单内动作。'
              '如果无法选择，输出STOP且args为空对象。仍只输出原约定的action JSON。')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_request(original, draft):
    require(draft['status'] == 'unactivated_not_sent' and draft['budget_registered'] is False,
            'not_frozen_draft')
    body = json.loads(original['messages'][1]['content'])
    result = deepcopy(draft['request'])
    candidate = json.loads(result['messages'][1]['content'])
    checkpoint = candidate.pop('decision_checkpoint')
    require(checkpoint == dict(latest_public_rejection=body['history'][-1], instruction=CHECKPOINT),
            'changed_checkpoint_or_private_fields')
    require(candidate == body, 'draft_changed_baseline_fields')
    restored = deepcopy(result)
    restored['messages'][1]['content'] = original['messages'][1]['content']
    require(restored == original, 'changed_image_or_system')
    require(body['budget'] == dict(decisions=1, planning=1, observations=0), 'unexpected_baseline_budget')
    candidate['budget'] = dict(decisions=1, planning=0, observations=0)
    candidate['decision_checkpoint'] = checkpoint
    result['messages'][1]['content'] = json.dumps(candidate, ensure_ascii=False, separators=(',', ':'))
    return result


def verify(run=RUN):
    manifest = read(run / 'manifest.json')
    for key, expected in [('max_model_calls', 1), ('max_planning', 0), ('max_physical', 0), ('max_training', 0)]:
        require(manifest[key] == expected, 'changed_budget')
    for name, expected in manifest['identities'].items():
        require(sha(name) == expected, 'changed_frozen_input: ' + name)
    return manifest


def reserve(run=RUN):
    verify(run)
    save(run / 'model_claim.json', dict(ordinal=1, consumed=1, request_sha256=sha(run / 'request.json')))


def classify(response, history):
    from model_grasp_intent_v1.model import parse
    from qualified_feedback_v1.policy import permitted
    try:
        action = parse(response)['action']
        status = permitted(action, history)
        require(status != 'unsupported_action', 'unsupported_action')
    except (ValueError, TypeError, KeyError) as error:
        return dict(valid=False, action=None, status='invalid', error=str(error))
    status = 'novel_action_unchecked' if status == 'proposal' else status
    return dict(valid=True, action=action, status=status, error=None)
