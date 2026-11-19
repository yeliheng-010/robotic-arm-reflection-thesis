"""RGB保留原上下文；几何深度和分割独立创建，退出完整释放。"""
from contextlib import contextmanager
import hashlib
import mujoco
import numpy as np
from reflection.sim_sensing import SegmentationRenderer
from cv_metrics import isolated_mask, object_metrics
from cv_policy import REQUIRED, frame_gate
from sd_render import depth_check
from sensor_independent_v1.resources import geometry_resources


def rgb(env):
    env.mj_renderer.update_scene(env.mj_data, 'cam')
    return env.mj_renderer.render().copy()


def rgb_identity(before, after):
    np.testing.assert_array_equal(before, after)
    return dict(unchanged=True, sha256=hashlib.sha256(before.tobytes()).hexdigest(), shape=list(before.shape))


@contextmanager
def paired(env, original_segmentation):
    depth_factory = lambda: mujoco.Renderer(env.mj_model, env.height, env.width)
    seg_factory = lambda: SegmentationRenderer(env.mj_model, env.height, env.width)
    assert int(env.mj_model.vis.quality.offsamples) == 4
    with geometry_resources(env.mj_model, [depth_factory, seg_factory]) as (depth, segment):
        depth.enable_depth_rendering()
        actual = dict(rgb=int(env.mj_renderer._mjr_context.offSamples),
            original_depth=int(env.mj_depth_renderer._mjr_context.offSamples),
            original_segmentation=int(original_segmentation.renderer._mjr_context.offSamples),
            no_msaa_depth=int(depth._mjr_context.offSamples),
            no_msaa_segmentation=int(segment.renderer._mjr_context.offSamples))
        assert actual == dict(rgb=4, original_depth=4, original_segmentation=4,
                              no_msaa_depth=0, no_msaa_segmentation=0)
        assert int(env.mj_model.vis.quality.offsamples) == 4
        yield dict(original=(env.mj_depth_renderer, original_segmentation),
                   no_msaa=(depth, segment)), actual
    assert int(env.mj_model.vis.quality.offsamples) == 4


def capture(env, resources, frame):
    depth_renderer, segment = resources
    roots = segment.root_map(env.mj_data)
    rows, outlines = {}, {}
    for name in REQUIRED:
        outline = isolated_mask(env, segment, name)
        rows[name] = object_metrics(roots == env.mj_model.body(name).id, outline)
        rows[name]['framed'] = frame['bodies'][name]['passed']
        outlines[name] = outline
    depth_renderer.update_scene(env.mj_data, 'cam')
    depth = depth_renderer.render().copy()
    calibration = depth_check(env, depth, roots)
    gate = frame_gate(rows)
    report = dict(measurements=rows, gate=gate, framing=frame, calibration=calibration,
                  accepted=bool(gate['passed'] and calibration['passed']))
    return dict(report=report, depth=depth, roots=roots, outlines=outlines)
