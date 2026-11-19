"""输入等权、输入内成功回复等权；输出仍是单个合法候选。"""
import json


def weighted_variants(groups):
    if not groups or any(not g['variants'] for g in groups):
        raise ValueError('Expected nonempty inputs with at least one successful response')
    for group in groups:
        weight = 1.0/(len(groups)*len(group['variants']))
        for row in group['variants']:
            yield row, weight


def score_text(text, *, candidates, accepted):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate key')
            value[key] = item
        return value
    try:
        value = json.loads(text, object_pairs_hook=unique)
        valid = isinstance(value, dict) and set(value) == {'action_id'}
        valid = valid and isinstance(value['action_id'], str)
        legal = bool(valid and candidates.count(value['action_id']) == 1)
        return dict(json_valid=bool(valid), candidate_valid=legal,
                    set_match=bool(legal and value['action_id'] in accepted),
                    action_id=value['action_id'] if legal else None)
    except (ValueError, TypeError):
        return dict(json_valid=False, candidate_valid=False, set_match=False, action_id=None)
