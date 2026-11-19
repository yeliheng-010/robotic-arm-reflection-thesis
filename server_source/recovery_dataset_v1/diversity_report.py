"""同时报告全提案与资格通过子集，避免把筛选后成功率推广到全分布。"""
import os
from pathlib import Path
from collections import Counter
from collection_common import ROOT as COLLECTION, read, save, sha, verify

ROOT = Path(__file__).resolve().parent
CAMERA_FIELDS = ('azimuth_offset_deg','elevation_deg','distance_m','fovy')


def interval(values):
    return dict(min=min(values),max=max(values)) if values else None


def describe(cases):
    rows = [c for c in cases if c['item']['group']=='varied_noisy']
    configs = {c['item']['seed']:c['config'] for c in rows}
    camera = {k:interval([c['camera'][k] for c in configs.values()]) for k in CAMERA_FIELDS}
    bodies = sorted({name for c in configs.values() for name in c['bodies']})
    layouts = {name:dict(x=interval([c['bodies'][name]['position'][0] for c in configs.values() if name in c['bodies']]),
        y=interval([c['bodies'][name]['position'][1] for c in configs.values() if name in c['bodies']])) for name in bodies}
    colors = {name:dict(Counter(c['appearance'][name]['color'] for c in configs.values()))
        for name in ('BlueBin','RedBin','SortingTray')}
    assert all(c['sensor']==dict(depth_sigma_m=.003,dropout=.02) for c in configs.values())
    return dict(conditions=len(rows),seed_groups=len(configs),camera=camera,layouts=layouts,colors=colors,
        noise=dict(depth_sigma_m=.003,dropout=.02),tasks=dict(Counter(c['item']['source'] for c in rows)))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    proposed, qualified, rejection_rows, identities = [], [], [], {}
    for path in sorted(COLLECTION.glob('batches/*/qualification/result.json')):
        result, manifest = verify(path), verify(path.parent/'manifest.json')
        assert result['manifest_sha256']==sha(path.parent/'manifest.json')
        allowed = {r['id'] for r in result['rows'] if r['passed']}
        proposed.extend(manifest['cases'])
        qualified.extend(c for c in manifest['cases'] if c['item']['id'] in allowed)
        rejection_rows.extend(r for r in result['rows'] if not r['passed'])
        identities[str(path)] = sha(path)
        identities[str(path.parent/'manifest.json')] = sha(path.parent/'manifest.json')
    assert proposed
    save(ROOT/'diversity'/('job_'+os.environ['SLURM_JOB_ID']+'.json'),dict(proposed=describe(proposed),
        qualified=describe(qualified),rejections=dict(Counter(r['status'] for r in rejection_rows)),
        limitation='qualification_coverage_is_not_physical_success_or_all_distribution_performance',
        identities=dict(identities,**{str(Path(__file__)):sha(__file__)})))


if __name__=='__main__':
    main()
