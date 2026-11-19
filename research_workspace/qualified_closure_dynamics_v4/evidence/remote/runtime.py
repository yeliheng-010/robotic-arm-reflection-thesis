"""相同GPU配置下的受保护实际导入；成功和失败均保存计数。"""
import importlib
import os
from qualified_closure_dynamics_v3.guarded_imports import zero_motion, load_runtime as load_v3
from qualified_closure_dynamics_v4.protocol import (
    ROOT, read_snapshot, validate_runtime, verify_preparation, save, require)


def require_gpu(profile):
    require(profile['slurm'] and profile['gpu_allocated'], 'GPU Slurm allocation required')
    require(profile['torch_devices'] == profile['open3d_devices'] == 1, 'Exactly one visible GPU required')
    require(profile['open3d_backend'] == 'cuda', 'Open3D CUDA branch required')


def gpu_profile():
    import torch
    import open3d
    allocated = any(os.environ.get(key, '').strip() not in ('', '0')
                    for key in ('SLURM_JOB_GPUS', 'SLURM_STEP_GPUS', 'SLURM_GPUS_ON_NODE'))
    profile = dict(slurm=bool(os.environ.get('SLURM_JOB_ID')), gpu_allocated=allocated,
        torch_devices=torch.cuda.device_count(), open3d_devices=open3d.core.cuda.device_count(),
        open3d_backend=open3d.__DEVICE_API__)
    require_gpu(profile)
    profile.update(device_name=torch.cuda.get_device_name(0),
                   capability=list(torch.cuda.get_device_capability(0)))
    return profile


def load_runtime():
    load_v3()
    for name in ('preflight', 'audit_imports', 'entry'):
        importlib.import_module('qualified_closure_dynamics_v4.' + name)


def checked_imports():
    manifest = verify_preparation()
    with zero_motion() as counts:
        try:
            load_runtime()
            profile, snapshot = gpu_profile(), read_snapshot()
            require(profile == snapshot['gpu_profile'], 'GPU execution profile changed')
            checked = validate_runtime(snapshot)
            require(not any(counts.values()), 'Simulation attempted during import check')
        except Exception as error:
            save(ROOT / ('failed_import_check_' + os.environ['SLURM_JOB_ID'] + '.json'),
                 dict(error=type(error).__name__ + ': ' + str(error), counts=counts))
            raise
    return dict(**checked, counts=counts, gpu_profile=profile,
                verified_identities=len(manifest['identities']))
