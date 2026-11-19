"""从完整原始结果构建汇总，允许未调用模型的首次成功。"""
import json


def read_events(directory, *, calls):
    path = directory/'requests.jsonl'
    if not path.exists() and calls == 0:
        return []
    events = [json.loads(s) for s in path.read_text().splitlines()]
    if len(events) != calls:
        raise ValueError('Request count differs from raw reflection records')
    return events


def reconstruct(directory, *, case, arm):
    result = json.loads((directory/'result.json').read_text())
    calls = sum('reflection' in r or 'reflection_error' in r for r in result['records'])
    events = read_events(directory, calls=calls) if arm in ('base', 'adapted') else []
    return dict(case=case, arm=arm, task={k: result[k] for k in ('source', 'destination', 'fault', 'seed')},
        success=result['success'], attempts=result['attempts'], calls=calls,
        invalid=sum('reflection_error' in r for r in result['records']),
        service_errors=sum(e.get('service_error', False) for e in events), result=str(directory/'result.json'))
