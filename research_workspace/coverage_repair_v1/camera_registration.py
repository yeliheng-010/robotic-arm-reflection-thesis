"""明确选择同一varied_noisy布局；无合格配置不得回退baseline。"""
def configuration(cases, seed):
    rows = [c['config'] for c in cases if c['item']['seed']==seed
        and c['item']['group']=='varied_noisy']
    if not rows or rows[0].get('group')!='varied_noisy' or not isinstance(rows[0].get('camera'),dict):
        raise ValueError('Missing varied camera configuration')
    if any(row!=rows[0] for row in rows):
        raise ValueError('Conflicting same-seed camera configurations')
    return rows[0]
