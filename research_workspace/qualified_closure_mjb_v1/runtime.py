"""相同GPU配置下零构造导入并核验全部来源。"""
import importlib
from qualified_closure_mjb_v1.protocol import verify_sources, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion


def checked_imports():
    with zero_motion() as counts:
        from reflection.__main__ import bootstrap
        bootstrap()
        for name in ('restore', 'backend', 'resources', 'worker', 'trace', 'partial', 'audit_states', 'audit', 'entry'):
            importlib.import_module('qualified_closure_mjb_v1.'+name)
        from qualified_closure_dynamics_v4.runtime import gpu_profile, read_snapshot
        from qualified_scene_candidate_v1.common import loaded_sources
        profile = gpu_profile()
        require(profile == read_snapshot()['gpu_profile'], 'GPU execution profile changed')
        identities = verify_sources()
        loaded = loaded_sources(identities)
        require(not any(counts.values()), 'Simulation requested during imports')
    return dict(identities=identities, loaded_sources=loaded, gpu_profile=profile, counts=counts)
