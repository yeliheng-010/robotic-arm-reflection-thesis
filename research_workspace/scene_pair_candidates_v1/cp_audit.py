"""重建世界候选并用保存的实际场景体素复核原碰撞过滤器。"""
from unittest.mock import patch
from pathlib import Path
import cv2
import numpy as np
from sd_common import read, save, sha
import sf_audit
from dr_audit import recovery
from stability.detector import StableDetector
from stability.proposals import filter_then_nms
from grasp_process import GraspGroup
from grasp_process import rank_grasp_candidates
from candidate_rank import ranking
from world_candidates import generate
from candidate_runtime import EXHAUSTED
from cp_common import ROOT, SOURCE, verify
from cp_prepare import scan


def candidate_audit(step, config):
    record = read(step['result_path'])['records'][0]
    trace = record['world_candidate_fallback']
    if not trace['active']:
        return
    assert trace['camera'] == config['camera'] and sha(trace['artifact']) == trace['sha256']
    with np.load(trace['artifact']) as arrays:
        generated = generate(arrays['target'], config['camera'])
        np.testing.assert_array_equal(arrays['generated'], generated.grasp_group_array)
        detector = object.__new__(StableDetector)
        detector.scene_points = arrays['scene_voxels']
        for key, value in trace['detector_parameters'].items():
            setattr(detector, key, value)
        safe = np.empty((0,17))
        try:
            safe = filter_then_nms(generated, detector).grasp_group_array
        except RuntimeError as exc:
            assert str(exc) == EXHAUSTED
        np.testing.assert_array_equal(arrays['safe'], safe)
        np.testing.assert_array_equal(arrays['generated'], record['candidate_trace']['generated'])
        assert trace['generated'] == len(generated) and trace['safe'] == len(safe)
        for returned in record['candidate_trace'].get('returned', []):
            assert any(np.array_equal(returned, row) for row in safe)
        if len(safe):
            audit_ranking(step, arrays, config=config, record=record)


def audit_ranking(step, arrays, *, config, record):
    folder = Path(step['result_path']).parent/'attempt_1'
    path = folder/'depth_evidence.npz'
    field = 'noisy'
    if record['depth_recovery']['changed']:
        path, field = record['depth_recovery']['artifact'], 'effective'
    with np.load(path) as data:
        depth = data[field]
    mask = cv2.imread(str(folder/'mask.png'), cv2.IMREAD_GRAYSCALE)
    rows = []
    try:
        rows = ranking(rank_grasp_candidates, {'active':True}, config['camera'])(
            GraspGroup(arrays['safe']), arrays['target'], mask, depth,
            fovy=np.deg2rad(config['camera']['fovy']))
    except RuntimeError as exc:
        assert str(exc).startswith('没有候选同时满足')
    actual = record['candidate_trace'].get('returned', [])
    assert bool(rows) == bool(actual)
    if actual:
        expected = np.stack([r[0].grasp_array for r in rows[:len(actual)]])
        np.testing.assert_array_equal(expected, actual)
    assert record['world_candidate_fallback']['ranking_angle_frame'] == 'world_down'


def main():
    manifest = verify()
    source = read(SOURCE/'paired_ledger.json')
    assert read(ROOT/'scan.json') == [scan(row) for row in source]
    rows = []
    for row in source:
        item, old = row['item'], row['new']
        reused = item['id'] not in manifest['selected']
        new = old
        if not reused:
            with patch.object(sf_audit, 'ROOT', ROOT):
                new = sf_audit.enhanced(item, manifest)
            for step in new['steps']:
                recovery(step)
                candidate_audit(step, manifest['configs'][item['id']])
        rows.append(dict(item=item, old=old, new=new, reused=reused))
    metrics = {scene: sf_audit.summarize([r for r in rows if r['item']['group'] == scene])
               for scene in ('baseline', 'varied_noisy')}
    reference = reference_metrics(rows)
    save(ROOT/'verification.json', dict(passed=True, complete=True, accounted=len(rows), metrics=metrics,
         original_enhanced_comparison=reference,
         actual_new_attempts=sum(len(r['new']['steps']) for r in rows if not r['reused']),
         reused_conditions=sum(r['reused'] for r in rows),
         promotion_allowed=reference['gains'] > 0 and reference['regressions'] == 0,
         manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0, training_approved=False, test_used=False))
    save(ROOT/'paired_ledger.json', rows)
    print(dict(metrics=metrics, reference=reference), flush=True)


def reference_metrics(rows):
    return sf_audit.summarize([dict(r, old=sf_audit.old_row(r['item']))
                              for r in rows if r['item']['group']=='varied_noisy'])


if __name__ == '__main__':
    main()
