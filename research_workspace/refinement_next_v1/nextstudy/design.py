"""预登记完整因子设计；混合组只切换指定因素。"""
import copy
import itertools
from controlled.config import scenario, tasks
from reflection.reflector import Parameters

REPEATS = 2
COARSE_OFFSET = (-.04, 0., 0.)
DEPTHS = (0., -.01, -.02)


def compose_mixed(seed, *, layout, physics, feedback):
    config = copy.deepcopy(scenario(seed, 'mixed'))
    clean = scenario(seed, 'clean')
    if not layout:
        for name, body in config['bodies'].items():
            body.update({key: clean['bodies'][name][key] for key in ('xy', 'yaw_delta')})
        config['containers'] = clean['containers']
        config['layout_rejections'] = clean['layout_rejections']
        for key in ('xy_m', 'yaw_degrees', 'container_xy_m', 'shuffle'):
            config['profile'][key] = clean['profile'][key]
    if not physics:
        for body in config['bodies'].values():
            body.update(density_scale=1., friction_scale=1.)
        config['profile'].update(density_fraction=0., friction_fraction=0.)
    if not feedback:
        config['feedback'] = clean['feedback']
    return config


def physical_items(residual):
    rows = []
    offsets = ((0., 0., 0.), COARSE_OFFSET, (-residual[0], -residual[1], 0.))
    for offset, height, repeat in itertools.product(range(3), (.35, .25), range(REPEATS)):
        rows.append(dict(case=7, repeat=repeat, factors=dict(offset=offset, height=height),
                         parameters=dict(grasp_offset=offsets[offset], lift_height=height)))
    for case, depth, repeat in itertools.product((25, 37), DEPTHS, range(REPEATS)):
        rows.append(dict(case=case, repeat=repeat, factors=dict(depth=depth),
                         parameters=dict(candidate_index=1, grasp_offset=[0., 0., depth])))
    for layout, physics, feedback, repeat in itertools.product((False, True), repeat=4):
        rows.append(dict(case=47, repeat=int(repeat), parameters={},
                         factors=dict(layout=layout, physics=physics, feedback=feedback)))
    for index, row in enumerate(rows):
        row['id'] = f"A{index:02d}_case{row['case']}_r{row['repeat']}"
        row['parameters'] = Parameters().updated(row['parameters']).to_dict()
        row['task'] = tasks()[row['case']]
    return rows


def item_scenario(item):
    task = item['task']
    if item['case'] == 47:
        return compose_mixed(task['seed'], **item['factors'])
    return scenario(task['seed'], task['level'])
