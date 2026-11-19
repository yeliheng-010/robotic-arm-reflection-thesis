"""精确输入去重、歧义标签隔离与分组防泄漏。"""
import hashlib
import json
from collections import defaultdict


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(encoded.encode()).hexdigest()


def input_digest(messages):
    canonical = []
    for message in messages:
        content = message['content']
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            pass
        canonical.append(dict(role=message['role'], content=content))
    return digest(canonical)


def verify_groups(rows):
    seen = {}
    for row in rows:
        key = (row['batch'], row['seed'])
        previous = seen.setdefault(key, row['split'])
        if previous != row['split']:
            raise ValueError(f'Seed group crosses splits: {key}')


def curate(rows):
    verify_groups(rows)
    by_input = defaultdict(list)
    for row in rows:
        by_input[row['input_hash']].append(row)
    kept, rejected = [], []
    for key, group in sorted(by_input.items()):
        if len({r['target'] for r in group}) > 1:
            rejected.extend(dict(uid=r['uid'], reason='ambiguous_target') for r in group)
            continue
        evaluation = any(r['split'] != 'train' for r in group)
        by_split = defaultdict(list)
        for row in group:
            if evaluation and row['split'] == 'train':
                rejected.append(dict(uid=row['uid'], reason='eval_overlap'))
            else:
                by_split[row['split']].append(row)
        kept.extend(merge(key, members) for members in by_split.values())
    return kept, rejected


def merge(key, members):
    first = members[0]
    return dict(id=digest([key, first['target'], first['split']]), input_hash=key,
                target=first['target'], split=first['split'], messages=first['messages'],
                members=sorted(r['uid'] for r in members),
                sources=sorted({r['source'] for r in members}),
                groups=sorted({f"{r['batch']}:{r['seed']}" for r in members}))


def verify_export(kept, rejected, rows):
    membership = [uid for r in kept for uid in r['members']]
    membership += [r['uid'] for r in rejected]
    assert len(membership) == len(set(membership)) == len(rows)
    assert set(membership) == {r['uid'] for r in rows}
    train = {r['input_hash'] for r in kept if r['split']=='train'}
    evaluation = {r['input_hash'] for r in kept if r['split']!='train'}
    assert not train & evaluation
    assert all(len({r['target'] for r in kept if r['input_hash']==key})==1
               for key in {r['input_hash'] for r in kept})
