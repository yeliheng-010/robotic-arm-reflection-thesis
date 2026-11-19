"""只读量化暂停状态三帧的RGB差异，不新增渲染或仿真步。"""
import os
import cv2
import numpy as np
from f_common import ROOT, read, save, sha, verify


def compare(first, second):
    difference = second.astype(np.int16)-first.astype(np.int16)
    active = np.any(difference != 0, axis=2)
    counts = np.unique(difference, return_counts=True)
    return dict(shape=list(first.shape), changed_pixels=int(active.sum()), total_pixels=int(active.size),
                max_absolute_channel_difference=int(np.max(np.abs(difference))),
                mean_absolute_channel_difference=float(np.mean(np.abs(difference))),
                channel_difference_histogram={str(int(v)): int(n) for v, n in zip(*counts)})


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify()
    folders = [ROOT/'run/observations'/f'observation_{i}' for i in range(3)]
    rgb = [cv2.imread(str(p/'rgb.png'), cv2.IMREAD_UNCHANGED) for p in folders]
    audits = [read(p/'audit.json') for p in folders]
    public = [read(p/'public.json') for p in folders]
    depth = [np.load(p/'private_sensor.npz')['clean'] for p in folders]
    rows = [dict(index=i, rgb=compare(rgb[0], rgb[i]),
                 clean_depth_identical=bool(np.array_equal(depth[0], depth[i])),
                 state_digest_identical=audits[0]['state_sha256'] == audits[i]['state_sha256'],
                 time_identical=public[0]['time_s'] == public[i]['time_s']) for i in (1, 2)]
    value = dict(rows=rows, physical_executions=0, new_renders=0,
                 identities={str(p/'rgb.png'): sha(p/'rgb.png') for p in folders})
    save(ROOT/'rgb_diagnostic.json', value)
    print(value, flush=True)


if __name__ == '__main__':
    main()
