"""新采集只可读取通过当前可见性策略的配置。"""
import json
from pathlib import Path
from cv_policy import frame_gate, require_frame


def approved_config(folder, original):
    folder = Path(folder)
    report = json.loads((folder/'selection.json').read_text(encoding='utf-8'))
    if not report['accepted']:
        raise ValueError('No eligible camera; exclude this scene without fallback')
    selected = report['attempts'][-1]
    require_frame(frame_gate(selected['measurements']))
    if not selected.get('calibration', {}).get('passed'):
        raise ValueError('Missing successful calibration')
    if any(row['accepted'] for row in report['attempts'][:-1]):
        raise ValueError('Selection is not the first eligible camera')
    config = json.loads((folder/'accepted_config.json').read_text(encoding='utf-8'))
    if config['camera'] != selected['camera']:
        raise ValueError('Approved camera identity mismatch')
    unchanged = lambda value: {key: val for key, val in value.items() if key != 'camera'}
    if unchanged(config) != unchanged(original):
        raise ValueError('Layout, appearance or noise changed')
    return config
