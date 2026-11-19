"""相机必须同时通过完整入画、目标可见性和既有深度检查。"""
TASK_BODIES = ('RedBlock', 'BlueBin', 'PurpleCapsule', 'RedBin')


def accepted(framing, visibility, calibration):
    return (framing['passed'] and calibration['passed']
            and all(visibility[name]['qualified'] for name in TASK_BODIES))
