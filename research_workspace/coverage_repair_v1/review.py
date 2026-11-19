import ast
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import final_review
from common import ROOT, read, save, sha, verify


def main():
    files = []
    with patch.object(final_review,'ROOT',ROOT):
        for path in ROOT.glob('*.py'):
            source = path.read_text()
            assert len(source.splitlines())<=300
            tree = ast.parse(source)
            compile(tree,str(path),'exec')
            files.append(dict(path=str(path),functions=final_review.functions(path,tree)))
    verify(ROOT/'manifest.json')
    registry = verify(ROOT/'camera_v2/manifest.json')
    grasp = verify(ROOT/'audit/grasp_964347/result.json')
    rows = []
    for spec in registry['rows']:
        path = ROOT/'camera_v2/audit'/spec['name']/'result.json'
        value = read(path)
        assert value==read(ROOT/'camera_v2/probe'/spec['name']/'result.json')
        rows.append(dict(name=spec['name'],accepted=value['accepted'],checked=value['checked']))
    paths = [p for p in ROOT.rglob('*') if p.is_file() and 'evidence' not in p.parts]
    save(ROOT/'review.json',dict(passed=True,files=files,cameras=rows,grasp=grasp,
        physical_attempts=0,model_calls=0,training_updates=0,
        identities={str(p):sha(p) for p in paths if p.suffix!='.md'}))
    print(dict(passed=True,python_files=len(files),cameras=rows),flush=True)


if __name__=='__main__':
    main()
