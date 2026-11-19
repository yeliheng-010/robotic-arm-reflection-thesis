"""新增文件规模与冻结源核验；不覆盖旧final_review输出。"""
import ast
from pathlib import Path
import final_review
from cc_common import save, sha, verify, read

ROOT = Path(__file__).resolve().parent


def main():
    rows = []
    for path in ROOT.glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300
        tree = ast.parse(source)
        compile(tree, str(path), 'exec')
        rows.append(dict(path=str(path), functions=final_review.functions(path, tree)))
    verify(ROOT.parent/'trial_gpu_v2/manifest.json')
    verify(ROOT.parent/'path_v2/results/manifest.json')
    verify(ROOT/'partial_audit.json')
    identities = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')}
    assert read(ROOT/'partial_audit.json')['new_verified_successes'] == 0
    save(ROOT/'review.json', dict(passed=True, files=rows, identities=identities,
        scope='Local revision checks plus unchanged prior frozen sources and partial evidence'))
    print(dict(review_passed=True, python_files=len(rows), source_files=len(identities)))


if __name__ == '__main__':
    main()
