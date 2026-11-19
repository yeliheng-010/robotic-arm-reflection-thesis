"""Slurm内冻结实现来源；不创建动力学授权或claim。"""
import ast
import os
from qualified_closure_dynamics_v1.protocol import ROOT, PROJECT, BUDGET, read, save, sha, require, commands


def check_sources():
    rows = {}
    for path in sorted(ROOT.glob('*.py')):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(path))
        require(len(source.splitlines()) <= 300, 'File too long: ' + path.name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                require(node.end_lineno - node.lineno + 1 <= 50, 'Function too long: ' + node.name)
        rows[path.name] = sha(path)
    return rows


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(not (ROOT / 'authorization.json').exists(), 'Preparation must not activate dynamics')
    require(not (ROOT / 'run').exists(), 'Unexpected dynamics run directory')
    parent = PROJECT / 'qualified_closure_reachability_v1/run'
    manifest = read(parent / 'manifest.json')
    identities = dict(manifest['identities'])
    for name, digest in identities.items():
        require(sha(name) == digest, 'Frozen source changed: ' + name)
    for path in parent.iterdir():
        if path.is_file():
            identities[str(path)] = sha(path)
    sources = check_sources()
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in ('.py', '.sbatch', '.md', '.json'):
            identities[str(path)] = sha(path)
    require(commands() == read(ROOT / 'controls.reference.json')['control_commands'], 'Control sequence')
    require(commands() == read(parent / 'controls.json')['control_commands'], 'Server control sequence')
    save(ROOT / 'preparation_manifest.json', dict(status='implementation_prepared_not_authorized',
         execution_authorized=False, proposed_budget=BUDGET, identities=identities, sources=sources,
         setup_steps=0, task_steps=0, model_calls=0, training_runs=0, job=os.environ['SLURM_JOB_ID']))
    print(dict(prepared=True, sources=len(sources), identities=len(identities), dynamics_authorized=False), flush=True)


if __name__ == '__main__':
    main()
