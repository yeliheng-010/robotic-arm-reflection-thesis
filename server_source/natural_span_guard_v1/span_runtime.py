from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import grasp_process as grasp
import goal_runtime
from f_common import save, sha
from span_filter import context as filter_context
from qp_runtime import QualifiedSession


def capture_data(original, captured):
    def process(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.update(points=np.asarray(result[1].points).copy(), depth=np.asarray(result[4]).copy(),
            mask=np.asarray(result[3]).copy(), fovy=float(kwargs.get('fovy', np.pi/4)))
        return result
    return process


def choose_wrapper(original, captured, *, folder, trace):
    def choose(flow, **kwargs):
        assert set(captured) == {'points', 'depth', 'mask', 'fovy'}
        transform, intrinsics = grasp.camera_calibration_from_env(flow.env, image_shape=captured['depth'].shape)
        world = captured['points']@transform.R.T+transform.t
        path = folder/'span_inputs.npz'
        assert not path.exists()
        np.savez_compressed(path, camera_points=captured['points'], world_points=world,
            depth=captured['depth'], mask=captured['mask'])
        trace.update(active=True, artifact=str(path), sha256=sha(path), points=len(world),
            transform=transform.A.tolist(), intrinsics=list(intrinsics), fovy=captured['fovy'],
            source='actual_inference_mask_and_noisy_depth_camera_points')
        with filter_context(world, trace):
            result = original(flow, **kwargs)
        result['observed_span_filter'] = dict(trace)
        return result
    return choose


@contextmanager
def capture(folder):
    captured, trace = {}, dict(active=False)
    process = capture_data(grasp.get_and_process_data, captured)
    choose = choose_wrapper(goal_runtime.choose, captured, folder=folder, trace=trace)
    try:
        with patch.object(grasp, 'get_and_process_data', process), patch.object(goal_runtime, 'choose', choose):
            yield
    finally:
        save(folder/'span_guard.json', trace)


class SpanSession(QualifiedSession):
    def _engine(self):
        with capture(self.folder):
            super()._engine()
