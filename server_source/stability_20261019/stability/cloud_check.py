"""训练点云上的固定网格对照，不使用新种子调参。"""
import json
from pathlib import Path
import numpy as np
from geometry.candidates import generate
from stability.detector import StableDetector, OriginalDetector

OUT = Path('/home/yeliheng/grasp_server/stability_20261019')
CLOUDS = Path('/home/yeliheng/grasp_server/geometry_20261019')


def main():
    rows = []
    for path in sorted(CLOUDS.glob('*.npz')):
        data = np.load(path)
        group = generate(data['target']).nms()
        group.sort_by_score()
        row = {'scene': path.stem, 'count': len(group)}
        for name, factory in [('old', OriginalDetector), ('stable', StableDetector)]:
            detector = factory(data['scene'], voxel_size=.008)
            c, e, parts = detector.detect(group, approach_dist=.06, collision_thresh=.01,
                return_empty_grasp=True, empty_thresh=.003, return_ious=True)
            row[name] = {'survivors': int(np.sum(~(c | e))), 'iou': parts[0].tolist()}
        rows.append(row)
    (OUT/'cloud_check.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()

