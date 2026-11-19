"""精确核对策略使用的深度/状态；RGB微差仅作为未输入文本模型的存档。"""
import cv2
from f_common import read
from audit_sensor_live import frame
from f_rgb_diagnostic import compare

RGB_NOT_SENT = 'captured_artifact_not_sent_to_text_model'


def repeated(public, private, *, sensing):
    assert len(public) == len(private) == 3
    assert len({r['time_s'] for r in public}) == 1
    for key in ('state_sha256', 'clean_sha256'):
        assert len({r[key] for r in private}) == 1, key
    assert len({r['noisy_sha256'] for r in private}) == 3
    same_rgb = len({r['rgb_sha256'] for r in private}) == 1
    if not same_rgb:
        assert sensing['rgb'] == RGB_NOT_SENT, 'RGB variation unresolved for an image-input policy'
    return dict(state_and_clean_depth_identical=True, noisy_frames_distinct=True,
                rgb_bitwise_identical=same_rgb, rgb_sent_to_model=False)


def audit(folder, case, *, success):
    assert not success and case['config']['group'] == 'varied_noisy'
    paths = sorted((folder/'observations').glob('observation_*'))
    assert len(paths) == 3
    rows = [frame(path, case['config'], index=i) for i, path in enumerate(paths)]
    public, private = [r[0] for r in rows], [r[1] for r in rows]
    summary = read(folder/'observation_summary.json')
    assert public == summary['public'] and private == summary['private']
    assert summary['additional_observations'] == 2 and summary['remaining'] == 0
    sensing = read(folder/'model_input.json')['request']['sensing_status']
    exact = repeated(public, private, sensing=sensing)
    images = [cv2.imread(str(path/'rgb.png'), cv2.IMREAD_UNCHANGED) for path in paths]
    measured = [compare(images[0], images[i]) for i in (1, 2)]
    expected = read(folder.parent/'rgb_diagnostic.json')['rows']
    assert measured == [r['rgb'] for r in expected]
    return dict(passed=True, frames=3, extra=2, noise=[r['stats'] for r in private],
                rgb_difference=measured, **exact)
