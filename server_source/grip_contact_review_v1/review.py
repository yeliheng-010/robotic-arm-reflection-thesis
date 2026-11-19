"""只读私有接触记录，用于材料范围工程审查，不导出AI监督。"""
import json
import os
from pathlib import Path
import numpy as np
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'recovery_collection_v1'
PAD_MU = {'left_pad1': .7, 'right_pad1': .7, 'left_pad2': .6, 'right_pad2': .6}
MIN_FORCE_N = 1e-6


def describe(values):
    return dict(zip(('p10', 'median', 'p90', 'max'),
        [float(v) for v in np.quantile(values, [.1, .5, .9, 1.])])) if values else None


def samples(path, source):
    phases = {}
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['action'] not in ('close_gripper', 'move_to_point'):
                continue
            forces, utilization = [], []
            for contact in row['contacts']:
                pads = set(contact['geoms']).intersection(PAD_MU)
                if source not in contact['roots'] or len(pads) != 1:
                    continue
                normal = abs(contact['force'][0])
                if normal <= MIN_FORCE_N:
                    continue
                forces.append(normal)
                utilization.append(float(np.linalg.norm(contact['force'][1:3])) / (PAD_MU[pads.pop()] * normal))
            if forces:
                phase = phases.setdefault(row['action'], dict(normal=[], utilization=[]))
                phase['normal'].append(sum(forces))
                phase['utilization'].append(max(utilization))
    return {name: dict(contact_samples=len(row['normal']), normal_total_N=describe(row['normal']),
        peak_contact_friction_utilization=describe(row['utilization'])) for name, row in phases.items()}


def main():
    assert os.environ.get('SLURM_JOB_ID')
    rows, identities = [], {}
    for manifest_path in sorted(SOURCE.glob('batches/*/physics/manifest.json')):
        manifest = read(manifest_path)
        for case in manifest['cases']:
            audit_path = manifest_path.parent/'audits'/(case['item']['id']+'.json')
            if not audit_path.exists():
                continue
            audit = read(audit_path)
            assert audit['passed'] and audit['manifest_sha256'] == sha(manifest_path)
            for entry in audit['row']['physical']:
                folder = Path(entry['path'])
                trace, step = folder/'contacts.jsonl', folder/'step.json'
                assert sha(trace) == audit['identities'][str(trace)]
                assert sha(step) == audit['identities'][str(step)]
                rows.append(dict(condition=case['item']['id'], source=case['item']['source'],
                    path=str(folder), success=read(step)['success'], phases=samples(trace, case['item']['source'])))
            identities[str(audit_path)] = sha(audit_path)
    save(ROOT/'results'/('job_'+os.environ['SLURM_JOB_ID']+'.json'), dict(rows=rows, partial=True,
        identities=identities, model_input=False, training_label=False, physical_attempts=0,
        limitation='Sampled local contact utilization; not proof of capacity, cause or recovery under changed material'))
    print(dict(attempt_records=len(rows), model_input=False, training_label=False), flush=True)


if __name__ == '__main__':
    main()
