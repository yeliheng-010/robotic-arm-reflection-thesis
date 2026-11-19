"""几何可见性门槛；不把它等同于语义识别成功。"""
import math

REQUIRED = ('BlueBin', 'RedBin', 'SortingTray', 'RedBlock', 'GreenCylinder',
            'PurpleCapsule', 'OrangeSphere', 'Apple', 'Banana', 'Hammer',
            'Knife', 'Duck', 'Flashlight', 'rubik')
MIN_FRACTION = .85
MIN_PIXELS = 576
MIN_SHORT_SIDE = 16
MIN_COMPONENT_FRACTION = .80
RASTER_RELATIVE_TOLERANCE = .02
RASTER_ABSOLUTE_TOLERANCE = 4


def finite_count(value):
    return (type(value) in (int, float) and math.isfinite(value)
            and value >= 0 and int(value) == value)


def object_gate(row):
    keys = ('pixels', 'isolated_pixels', 'short_side', 'largest_component')
    if not all(finite_count(row.get(key)) for key in keys):
        return dict(passed=False, reasons=['invalid_measurement'])
    pixels, isolated = row['pixels'], row['isolated_pixels']
    if isolated == 0 or row['largest_component'] > pixels:
        return dict(passed=False, reasons=['invalid_measurement'])
    fraction = min(1., pixels / isolated)
    component = row['largest_component'] / max(1, pixels)
    checks = dict(framed=row.get('framed') is True,
                  visible_fraction=fraction >= MIN_FRACTION,
                  pixels=pixels >= MIN_PIXELS,
                  short_side=row['short_side'] >= MIN_SHORT_SIDE,
                  connected=component >= MIN_COMPONENT_FRACTION,
                  raster_consistent=pixels <= isolated * (1 + RASTER_RELATIVE_TOLERANCE)
                  + RASTER_ABSOLUTE_TOLERANCE)
    return dict(passed=all(checks.values()), visible_fraction=fraction,
                component_fraction=component,
                reasons=[key for key, passed in checks.items() if not passed])


def frame_gate(rows):
    objects = {name: object_gate(rows.get(name, {})) for name in REQUIRED}
    rejected = [name for name, result in objects.items() if not result['passed']]
    return dict(passed=not rejected, rejected=rejected, objects=objects)


def require_frame(report):
    """下游必须调用；不合格时禁止静默使用旧相机。"""
    if not report.get('passed'):
        raise ValueError('Unusable camera observation: ' + str(report.get('rejected')))
