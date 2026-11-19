"""只读量化完整数组差异与像素中心射线误差。"""
from pathlib import Path
import numpy as np
from surface_grasp_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent


def main():
    folder = ROOT / 'sampling'
    assert read(folder / 'audit.json')['passed']
    result = read(folder / 'result.json')
    with np.load(ROOT / 'run/pixels.npz') as old, np.load(folder / 'original.npz') as current:
        difference = np.abs(old['depth'].astype(float) - current['depth'])
        delta = dict(changed_pixels=int(np.count_nonzero(difference)),
            maximum_m=float(difference.max()), p99_m=float(np.percentile(difference, 99)),
            pixels_over_1mm=int(np.count_nonzero(difference > .001)),
            shape=list(difference.shape))
    closest = min(result['pixel_center_rays'], key=lambda r:
        abs(r['ray_depth_m'] - result['variants']['no_msaa']['focus_depth_m']))
    comparison = {label: abs(row['focus_depth_m'] - closest['ray_depth_m'])
                  for label, row in result['variants'].items()}
    save(folder / 'stats.json', dict(original_rerender_delta=delta,
        closest_diagnostic_ray=dict(u=closest['u'], v=closest['v'], depth_m=closest['ray_depth_m']),
        focus_ray_error_m=comparison, selection='post-hoc closest of nine diagnostic rays',
        source_result_sha256=sha(folder / 'result.json'), new_rendering=False,
        control_deployed=False, script_sha256=sha(Path(__file__))))
    print(dict(original_rerender_delta=delta, focus_ray_error_m=comparison), flush=True)


if __name__ == '__main__':
    main()
