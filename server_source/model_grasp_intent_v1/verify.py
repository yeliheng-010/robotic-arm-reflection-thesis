"""排他保存本地验证，禁止把测试替身结果计为模型或物理成功。"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SUITES = (('new_contract', 'model_grasp_intent_v1', 'test_*.py'),
          ('existing_top_fit', 'observed_top_pose_v1', 'test_fit.py'),
          ('existing_span', 'natural_grasp_span_audit_v1', 'test_span.py'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def tests(folder):
    rows = []
    for label, directory, pattern in SUITES:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', pattern, '-v']
        result = subprocess.run(command, cwd=PROJECT, capture_output=True, timeout=60)
        log = folder/(label+'.log')
        with log.open('xb') as stream:
            stream.write(result.stdout+result.stderr)
        rows.append(dict(label=label, command=command, exit_code=result.returncode, sha256=sha(log)))
    return rows


def frozen_sources():
    rows = []
    for directory, key in [('coverage_repair_v1', 'entries'), ('joint_policy_v2', 'files')]:
        source = json.loads((PROJECT/directory/'SOURCE_VERIFICATION.json').read_text(encoding='utf-8'))
        for row in source[key]:
            file = PROJECT/row['path']
            rows.append(dict(path=row['path'], matched=file.exists() and sha(file)==row['sha256']))
    return rows


def complexity(node):
    branches = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)
    return 1 + sum(isinstance(child, branches) for child in ast.walk(node)) + sum(
        len(child.values)-1 for child in ast.walk(node) if isinstance(child, ast.BoolOp))


def nesting(node, level=0):
    controls = (ast.If, ast.For, ast.While, ast.With, ast.Try)
    level += isinstance(node, controls)
    return max([level] + [nesting(child, level) for child in ast.iter_child_nodes(node)])


def structure():
    rows = []
    for path in sorted(ROOT.glob('*.py')):
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        rows.append(dict(path=path.name, lines=len(text.splitlines()),
                         max_function_lines=max((n.end_lineno-n.lineno+1 for n in functions), default=0),
                         max_positional_args=max((len(n.args.args) for n in functions), default=0),
                         max_complexity=max((complexity(n) for n in functions), default=0),
                         max_nesting=nesting(tree)))
    return rows


def constants(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    result = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            result[target.id] = value
        elif isinstance(target, ast.Tuple):
            result.update({item.id: part for item, part in zip(target.elts, value)})
    return result


def safety_constants():
    from model_grasp_intent_v1 import geometry
    old_width = constants(PROJECT/'geometry/candidates.py')
    old_pose = constants(PROJECT/'observed_top_pose_v1/top_runtime.py')
    return dict(width=geometry.MAX_WIDTH_M == old_width['MAX_WIDTH'],
                margin=geometry.WIDTH_MARGIN_M == old_width['WIDTH_MARGIN'],
                translation=geometry.MAX_TRANSLATION_M == old_pose['MAX_TRANSLATION_M'])


def valid_structure(rows):
    limits = dict(lines=300, max_function_lines=50, max_positional_args=3,
                  max_complexity=10, max_nesting=3)
    return all(row[key] <= value for row in rows for key, value in limits.items())


def main(folder):
    folder.mkdir(parents=True, exist_ok=False)
    checks, frozen, sizes = tests(folder), frozen_sources(), structure()
    guards = safety_constants()
    size_ok = valid_structure(sizes)
    passed = all(r['exit_code'] == 0 for r in checks) and all(r['matched'] for r in frozen)
    passed = passed and size_ok and all(guards.values())
    result = dict(passed=passed, checked_at=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, tests=checks, structure=sizes, frozen_sources=frozen,
                  unchanged_safety_constants=guards, physical_attempts=0, real_model_calls=0,
                  training_runs=0, validation_scope='local_synthetic_and_existing_numeric_regressions',
                  sources={p.name: sha(p) for p in sorted(ROOT.glob('*.py'))})
    save(folder/'verification.json', result)
    print(json.dumps(dict(passed=passed, suites=len(checks), frozen_files=len(frozen),
                         structure_passed=size_ok, evidence=str(folder)), ensure_ascii=False))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
