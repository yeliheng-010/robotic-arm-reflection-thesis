"""仅当原过滤器拒绝全部候选，补充世界竖直候选并再次完整过滤。"""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sd_common import save, sha
from world_candidates import generate
from candidate_rank import ranking

EXHAUSTED = '所有候选均发生碰撞或夹爪内部为空'


def filtering(original, captured, trace, *, camera, arrays):
    def run(group, detector):
        try:
            return original(group, detector)
        except RuntimeError as exc:
            if str(exc) != EXHAUSTED:
                raise
        trace.update(active=True, reason=EXHAUSTED, camera=camera,
                     detector_parameters={k: float(v) for k, v in vars(detector).items()
                                          if isinstance(v, (int, float))})
        arrays.update(target=captured['points'], scene_voxels=detector.scene_points.copy(),
                      original=group.grasp_group_array.copy())
        alternate = generate(captured['points'], camera)
        arrays['generated'] = alternate.grasp_group_array.copy()
        arrays['safe'] = np.empty((0, 17))
        safe = original(alternate, detector)
        arrays['safe'] = safe.grasp_group_array.copy()
        return safe
    return run


def save_trace(directory, trace, arrays, *, record):
    if arrays:
        artifact = directory/'world_candidates.npz'
        np.savez_compressed(artifact, **arrays)
        trace.update(artifact=str(artifact), sha256=sha(artifact),
                     generated=len(arrays['generated']), safe=len(arrays['safe']))
        record['candidate_trace']['original_generated'] = arrays['original'].tolist()
        record['candidate_trace']['generated'] = arrays['generated'].tolist()
    record['world_candidate_fallback'] = trace
    save(directory/'world_candidates.json', trace)


@contextmanager
def context(config):
    from diversity import runtime
    import stability.runtime as stable
    import stability.inference as inference
    import grasp_process as grasp
    original = runtime.DiverseEngine._attempt

    def attempt(self, *args, **kwargs):
        trace, arrays, captured = dict(active=False), {}, {}
        previous = stable.generate
        def capture(points):
            captured['points'] = np.asarray(points).copy()
            return previous(points)
        filtered = filtering(inference.filter_then_nms, captured, trace, camera=config['camera'], arrays=arrays)
        ranked = ranking(grasp.rank_grasp_candidates, trace, config['camera'])
        with patch.object(stable, 'generate', capture), patch.object(inference, 'filter_then_nms', filtered), \
             patch.object(grasp, 'rank_grasp_candidates', ranked):
            record, report = original(self, *args, **kwargs)
        save_trace(Path(args[6]), trace, arrays, record=record)
        return record, report
    with patch.object(runtime.DiverseEngine, '_attempt', attempt):
        yield
