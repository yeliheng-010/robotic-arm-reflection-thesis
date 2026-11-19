"""预登记有限分支策略；只使用候选语义，不查看物理结果。"""
MAX_ALTERNATIVES = 2
MAX_ATTEMPTS = 3
ORDER = ('descent_route', 'measured_grasp', 'measured_place',
         'exploratory_candidate', 'exploratory_depth', 'exploratory_slow', 'exploratory_lift')


def semantic(row):
    return (row['kind'], row['state']['profile'] if row['kind'] == 'descent_route' else '')


def alternatives(rows, selected):
    rank = {kind: index for index, kind in enumerate(ORDER)}
    ordered = sorted(rows, key=lambda r: (rank.get(r['kind'], len(ORDER)), r['id']))
    seen, result = {semantic(selected)}, []
    for row in ordered:
        key = semantic(row)
        if key not in seen:
            result.append(row)
            seen.add(key)
        if len(result) == MAX_ALTERNATIVES:
            break
    return result


def outcome_set(observed):
    return sorted({row['action_id'] for row in observed if row['terminal_success']})
