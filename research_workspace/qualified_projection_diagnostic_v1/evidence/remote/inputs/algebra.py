"""独立XML刚体变换复算；不依赖MuJoCo或运动学检查器。"""
import xml.etree.ElementTree as ET
import numpy as np


def vector(text, default):
    return np.fromstring(text, sep=' ') if text is not None else np.asarray(default, dtype=float)


def quaternion(q):
    w, x, y, z = np.asarray(q) / np.linalg.norm(q)
    return np.array([[1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
                     [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
                     [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]])


def rotation(axis, angle):
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle)*skew + (1 - np.cos(angle))*(skew @ skew)


def joint_defaults(root):
    defaults = {}
    def visit(node, inherited):
        attributes = dict(inherited)
        joint = node.find('joint')
        if joint is not None:
            attributes.update(joint.attrib)
        if 'class' in node.attrib:
            defaults[node.attrib['class']] = attributes
        for child in node.findall('default'):
            visit(child, attributes)
    visit(root.find('default'), {})
    return defaults


def poses(source, values):
    root = ET.parse(source).getroot()
    defaults, result = joint_defaults(root), {}
    def visit(body, parent, inherited):
        name = body.attrib['name']
        position, frame = parent
        position = position + frame @ vector(body.get('pos'), [0, 0, 0])
        frame = frame @ quaternion(vector(body.get('quat'), [1, 0, 0, 0]))
        childclass = body.get('childclass', inherited)
        for joint in body.findall('joint'):
            attrs = dict(defaults.get(joint.get('class', childclass), {}), **joint.attrib)
            if attrs.get('type') == 'free':
                free = values[joint.attrib['name']]
                position, frame = np.asarray(free[:3]), quaternion(free[3:])
            else:
                anchor = vector(attrs.get('pos'), [0, 0, 0])
                turning = rotation(vector(attrs.get('axis'), [0, 0, 1]), values[joint.attrib['name']])
                position = position + frame @ (anchor - turning @ anchor)
                frame = frame @ turning
        result[name] = (position, frame)
        for child in body.findall('body'):
            visit(child, (position, frame), childclass)
    visit(root.find('./worldbody/body'), (np.zeros(3), np.eye(3)), None)
    return result


def residuals(source, values, equalities):
    frames = poses(source, values)
    root_rotation = frames['2f85_base'][1]
    rows = []
    for row in equalities:
        if row['type'] != 0:
            continue
        first, second = (frames[name] for name in row['names'])
        anchors = np.asarray(row['data'])
        delta = first[0] + first[1] @ anchors[:3] - second[0] - second[1] @ anchors[3:6]
        rows.append(dict(id=row['id'], world=delta.tolist(), local=(root_rotation.T @ delta).tolist()))
    return rows
