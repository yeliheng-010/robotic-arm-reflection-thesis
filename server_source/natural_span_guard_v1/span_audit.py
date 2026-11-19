from contextlib import contextmanager
from pathlib import Path
import cv2
import numpy as np
import grasp_process as grasp
from f_common import read, sha
from span_filter import context as filter_context


def reconstruct(folder):
    trace = read(folder/'span_guard.json')
    if not trace['active']:
        assert 'selected' not in read(folder/'route.json')
        return None, trace
    assert sha(trace['artifact']) == trace['sha256']
    record = read(folder/'execution/result.json')['records'][0]
    source, field = folder/'execution/attempt_1/depth_evidence.npz', 'noisy'
    if record['depth_recovery']['changed']:
        source, field = Path(record['depth_recovery']['artifact']), 'effective'
    with np.load(source) as raw, np.load(trace['artifact']) as arrays:
        np.testing.assert_array_equal(raw[field].astype(np.float32), arrays['depth'])
        mask = cv2.imread(str(folder/'execution/attempt_1/mask.png'), cv2.IMREAD_GRAYSCALE)
        np.testing.assert_array_equal(mask > 0, arrays['mask'] > 0)
        rgb = np.zeros((*arrays['depth'].shape, 3), dtype=np.uint8)
        result = grasp.get_and_process_data(rgb, arrays['depth'], arrays['mask'], fovy=trace['fovy'])
        points = np.asarray(result[1].points)
        np.testing.assert_array_equal(points, arrays['camera_points'])
        matrix = np.asarray(trace['transform'])
        world = points@matrix[:3,:3].T+matrix[:3,3]
        np.testing.assert_allclose(world, arrays['world_points'], rtol=0, atol=1e-12)
    assert len(world) == trace['points']
    assert read(folder/'route.json')['observed_span_filter'] == trace
    return world, trace


@contextmanager
def context(folder, calibration):
    world, recorded = reconstruct(folder)
    if world is None:
        yield dict(active=False)
        return
    for key in ('transform', 'intrinsics'):
        np.testing.assert_allclose(recorded[key], calibration[key], rtol=0, atol=1e-12)
    trace = {}
    with filter_context(world, trace):
        yield trace
    assert trace['poses'] == recorded['poses']
