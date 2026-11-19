"""测试通过后登记真实导入来源，仍禁止模型构造和积分。"""
import os
from qualified_closure_mjb_v1.protocol import ROOT, PREPARED, RUN, read, save, sha, require
from qualified_closure_mjb_v1.runtime import checked_imports


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not RUN.exists() and not (ROOT/'authorization.json').exists(), 'Unexpected dynamics registration')
    selected = read(ROOT/'TEST_RESULT.json')
    require(sha(ROOT/selected['path']) == selected['sha256'], 'Test evidence changed')
    tests = read(ROOT/selected['path'])
    require(tests['passed'] and not any(tests['counts'].values()), 'Tests not passed without simulation')
    imports = checked_imports()
    save(PREPARED/'loaded_sources.json', imports['loaded_sources'])
    save(PREPARED/'manifest.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'],
         tests=tests, identities=imports['identities'], gpu_profile=imports['gpu_profile'], counts=imports['counts'],
         execution_authorized=False, entrypoint_ready=False, bindings_sha256=sha(ROOT/'BINDINGS.json')))
    print(dict(passed=True, tests=tests['tests'], identities=len(imports['identities']), counts=imports['counts']), flush=True)


if __name__ == '__main__':
    main()
