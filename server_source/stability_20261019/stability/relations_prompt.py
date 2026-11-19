"""开发提示变体：只计算已观测包围盒关系，不生成动作答案。"""
import copy
import json
from stability.prompt import build_messages as original_messages

NOTE = ('commanded_tcp_xyz是该时刻规划指令值，不是MuJoCo实测TCP或物体位置。'
        'body_aabb_relations仅由contact_bounds_world计算；overlap_xyz是各轴区间交叠长度，'
        'first_bottom_minus_second_top_z是第一个物体底面减第二个物体顶面的高度差。'
        'commanded_tcp_inside_each_aabb按XYZ全部落入区间判断。'
        'AABB是包围盒近似，不能据此保证整条路径可达；没有提供任何推荐修正。')


def relation(pair, boxes, command):
    first, second = [boxes[name] for name in pair]
    overlap = [max(0., min(a, b)-max(c, d)) for a, b, c, d in zip(
        first['upper_xyz'], second['upper_xyz'], first['lower_xyz'], second['lower_xyz'])]
    row = {'bodies': list(pair), 'overlap_xyz': overlap,
           'first_bottom_minus_second_top_z': first['lower_xyz'][2]-second['upper_xyz'][2]}
    if command is not None:
        row['commanded_tcp_inside_each_aabb'] = [all(low <= x <= high for x, low, high in
            zip(command, box['lower_xyz'], box['upper_xyz'])) for box in (first, second)]
    return row


def add_relations(report):
    value = copy.deepcopy(report)
    evidence = value.setdefault('evidence', {})
    diagnostics = evidence.get('diagnostics', {})
    boxes = {row['body']: row for row in diagnostics.get('contact_bounds_world', [])}
    pairs = dict.fromkeys(tuple(pair) for pair in evidence.get('contacts', []))
    evidence['body_aabb_relations'] = [relation(pair, boxes, diagnostics.get('commanded_tcp_xyz'))
        for pair in pairs if len(pair) == 2 and all(name in boxes for name in pair)]
    return value


def build_messages(instruction, report, *, parameters, history=()):
    previous = [{**item, 'error': add_relations(item['error'])} for item in history]
    messages = original_messages(instruction, add_relations(report), parameters=parameters, history=previous)
    messages[0]['content'] += '\n'+NOTE
    return messages

