"""仅在当前执行进程中补缺失定位深度，保留原始传感数组证据。"""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sd_common import save, sha
from depth_estimate import estimate


def validator(original, events, arrays):
    from reflection.errors import TaskAbort, ErrorType

    def validate(pixel, depth, *args):
        roots, expected_id = args
        try:
            return original(pixel, depth, roots, expected_id)
        except TaskAbort as exc:
            if exc.report.error_type != ErrorType.DEPTH_INVALID:
                raise
            row = estimate(depth, roots == expected_id, pixel=pixel)
            row['expected_id'] = int(expected_id)
            events.append(row)
            if not row['accepted']:
                raise
            if not arrays:
                arrays['raw'] = depth.copy()
                arrays['roots'] = roots.copy()
            u, v = row['pixel_uv']
            depth[v, u] = row['value_m']
            arrays['effective'] = depth.copy()
            return original(pixel, depth, roots, expected_id)
    return validate


@contextmanager
def context():
    from diversity import runtime
    from reflection import engine
    original = runtime.DiverseEngine._attempt

    def attempt(self, *args, **kwargs):
        assert self.segmentation == 'simulation', 'This adapter uses the existing simulation mask'
        directory = Path(args[6])
        events, arrays = [], {}
        with patch.object(engine, 'validate_grounding', validator(engine.validate_grounding, events, arrays)):
            record, report = original(self, *args, **kwargs)
        artifact = directory/'depth_recovery.npz'
        if arrays:
            np.savez_compressed(artifact, **arrays)
        record['depth_recovery'] = dict(events=events, changed=bool(arrays),
            artifact=str(artifact) if arrays else None, sha256=sha(artifact) if arrays else None,
            source='noisy_depth_and_existing_simulation_segmentation', extra_observations=0)
        save(directory/'depth_recovery.json', record['depth_recovery'])
        return record, report
    with patch.object(runtime.DiverseEngine, '_attempt', attempt):
        yield
