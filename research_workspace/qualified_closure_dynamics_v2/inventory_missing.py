"""只列出旧清单的项目导入漏项；不自动批准、不创建准备清单。"""
import os
from unittest.mock import patch
from qualified_closure_dynamics_v2.protocol import ROOT, RUN, save, require
from qualified_closure_dynamics_v2 import preflight
from qualified_closure_dynamics_v2.guarded_imports import zero_motion, load_runtime


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not RUN.exists() and not (ROOT / 'authorization.json').exists(), 'Diagnostics only')
    identities = preflight.frozen_inputs()
    with zero_motion() as counts:
        load_runtime()
        with patch.object(preflight, 'project_binding', return_value=None):
            snapshot = preflight.collect_runtime(identities)
        require(not any(counts.values()), 'Attempted simulation')
    caches = {r['cached'] for r in snapshot['modules'].values() if 'cached' in r}
    missing = {name: row['sha256'] for name, row in snapshot['files'].items()
               if row['category'] == 'project' and name not in identities and name not in caches}
    save(ROOT / 'missing_project_sources.json', dict(approved=False, identities=missing,
         counts=counts, job=os.environ['SLURM_JOB_ID'], modules=len(snapshot['modules']),
         files=len(snapshot['files']), packages=len(snapshot['distributions']['packages'])))
    print(dict(unbound_project_files=len(missing), counts=counts, approved=False), flush=True)


if __name__ == '__main__':
    main()
