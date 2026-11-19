"""重算逐任务门禁，证明选择首个合格提案且无配置漂移。"""
from sd_common import read, sha
from sf_camera import framed, proposal, PROPOSAL_BUDGET
from sf_common import ROOT
from sf_gate import accepted


def audit_attempt(attempt, expected, *, boxes, bodies):
    assert attempt['camera'] == expected
    assert attempt['framing'] == framed(boxes, expected)
    visible = attempt['visibility']
    if visible is not None:
        for row in visible.values():
            assert row['visible_fraction'] == row['pixels']/max(1, row['isolated_pixels'])
            assert row['qualified'] == (row['pixels'] >= 64 and row['visible_fraction'] >= .70)
    if attempt['framing']['passed']:
        assert visible is not None
        if all(visible[name]['qualified'] for name in bodies):
            assert attempt['calibration'] is not None
    assert attempt['accepted'] == accepted(attempt['framing'], visible,
                                          attempt['calibration'], bodies=bodies)


def selection(item, manifest, previous):
    source = previous['configs'][f"{item['seed']}_varied_noisy"]
    selected = manifest['configs'][item['id']]
    assert {k: v for k, v in selected.items() if k not in ('camera', 'camera_accepted')} == {
        k: v for k, v in source.items() if k not in ('camera', 'camera_accepted')}
    folder = ROOT/'selection'/item['id']
    row = read(folder/'selection.json')
    bodies = (item['source'], item['destination'])
    assert row['bodies'] == list(bodies) and row['seed'] == item['seed']
    assert row['accepted'] == selected['camera_accepted']
    attempts = row['attempts']
    assert 1 <= len(attempts) <= PROPOSAL_BUDGET
    for index, attempt in enumerate(attempts):
        expected = source['camera'] if index == 0 else proposal(item['seed'], index, boxes=row['settled_boxes'])
        assert attempt['index'] == index
        audit_attempt(attempt, expected, boxes=row['settled_boxes'], bodies=bodies)
        assert not attempt['accepted'] or index == len(attempts)-1
    if row['accepted']:
        assert attempts[-1]['accepted'] and selected['camera'] == attempts[-1]['camera']
        assert row['capture']['calibration']['passed']
        assert row['capture']['visibility'] == attempts[-1]['visibility']
        assert row['capture']['rgb_sha256'] == sha(folder/'rgb.png')
        assert row['capture']['sensor_sha256'] == sha(folder/'sensor.npz')
    else:
        assert len(attempts) == PROPOSAL_BUDGET and not attempts[-1]['accepted']
    return row
