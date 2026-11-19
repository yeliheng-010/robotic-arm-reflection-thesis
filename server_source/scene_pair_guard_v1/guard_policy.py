"""任务内新增安全门控的纯判定。"""
import math

ROBOTS = ('ur5e_base', '2f85_base')
SUPPORTS = ('world', 'table1', 'table2', 'simple_table')
PADS = ('left_pad1', 'left_pad2', 'right_pad1', 'right_pad2')
XY_TOLERANCE_M = .020
Z_TOLERANCE_M = .040


def forbidden(contact, source):
    roots, geoms = contact['roots'], contact['geoms']
    robot = [index for index, root in enumerate(roots) if root in ROBOTS]
    if len(robot) != 1:
        return False
    index = robot[0]
    other = roots[1-index]
    if other.startswith(SUPPORTS):
        return False
    return not (other == source and roots[index] == '2f85_base' and geoms[index] in PADS)


def release_reason(evidence):
    if not evidence['held']:
        return 'object_dropped'
    actual, expected = evidence['actual'], evidence['expected']
    if not all(math.isfinite(value) for value in actual+expected):
        return 'placement_offset'
    xy_error = math.hypot(actual[0]-expected[0], actual[1]-expected[1])
    if xy_error > XY_TOLERANCE_M or abs(actual[2]-expected[2]) > Z_TOLERANCE_M:
        return 'placement_offset'
    return None
