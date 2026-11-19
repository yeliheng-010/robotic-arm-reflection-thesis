"""只输出全帧合格方向；拟合先保存，私有真值后评价。"""
from unittest.mock import patch
import cv2
import numpy as np
from visibility_calibration_v1 import capture
from pose_fresh_v1 import estimate, evaluate
from sensor_independent_v1.common import NOISE_PREFIX, save, sha


def accepted(env, data, *, config, row, folder, rgb):
    folder.mkdir(exist_ok=False)
    assert data['report']['accepted']
    snapshot = dict(case=dict(item=dict(seed=config['seed'], source='PurpleCapsule'), config=config))
    mask = (data['roots'] == env.mj_model.body('PurpleCapsule').id) & data['outlines']['PurpleCapsule']
    with patch.object(capture, 'SEED_PREFIX', NOISE_PREFIX):
        clouds, metadata = capture.noisy_clouds(env, data['depth'], mask=mask, snapshot=snapshot,
                                               phase_id=0, index=0)
    view_folder = folder / 'view_0'
    view_folder.mkdir(exist_ok=False)
    with (view_folder / 'clouds.npz').open('xb') as stream:
        np.savez_compressed(stream, **{f'noise_{i}': cloud for i, cloud in enumerate(clouds)})
    save(view_folder / 'metadata.json', dict(metadata, clouds_sha256=sha(view_folder / 'clouds.npz')))
    report = data['report']
    view = dict(index=0, pool_index=row['index'], camera=row['camera'], report=report,
        calibration=report['calibration'], calibration_passed=True, full_frame_qualified=True,
        source_fraction=report['gate']['objects']['PurpleCapsule']['visible_fraction'],
        source_pixels=report['measurements']['PurpleCapsule']['pixels'],
        training_eligible=False, control_eligible=False)
    save(folder / 'views.json', [view])
    assert cv2.imwrite(str(folder / 'qualified.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    save(folder / 'fits.json', estimate.run([view], {0: clouds}))
    geom = env.mj_model.geom('purple_capsule').id
    save(folder / 'private_truth.json', dict(center=env.mj_data.geom_xpos[geom].tolist(),
        axis=env.mj_data.geom_xmat[geom].reshape(3, 3)[:, 2].tolist(), private_simulation_truth=True))
    return dict(index=row['index'], qualified=True, **evaluate.run(folder))
