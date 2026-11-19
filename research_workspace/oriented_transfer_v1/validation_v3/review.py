import ast
from cc_common import save, sha, verify
from register import ROOT, PARENT
from final_review import functions


def main():
    rows = []
    for path in ROOT.glob('*.py'):
        source = path.read_text()
        assert len(source.splitlines()) <= 300
        tree = ast.parse(source)
        compile(tree, str(path), 'exec')
        rows.append(dict(path=str(path), functions=functions(path, tree)))
    verify(PARENT/'physical_fix_v1/review.json')
    verify(PARENT/'physical_fix_v1/partial_audit.json')
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    save(ROOT/'review.json', dict(passed=True, files=rows,
        identities={str(p): sha(p) for p in paths}))
    print(dict(passed=True, python_files=len(rows), source_files=len(paths)))


if __name__ == '__main__':
    main()
