"""作业结束后封存审计清单，保留原运行中日志快照。"""
import ast
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import final_review
from common import ROOT, read, save, sha, verify


def settled_identities(prior):
    scheduler = (ROOT/'scheduler.txt').read_text().splitlines()
    job = next(line.split() for line in scheduler if line.split()[0]=='6472')
    assert job[1:3]==['COMPLETED','0:0']
    identities, updates = {}, []
    for name, digest in prior['identities'].items():
        current = sha(name)
        if current!=digest:
            assert name==str(ROOT/'camera-v2-6472.log'), name
            updates.append(dict(path=name,old=digest,new=current,
                reason='Final review print appended after running-log snapshot'))
        identities[name] = current
    return identities, updates


def main():
    verify(ROOT/'manifest.json')
    verify(ROOT/'camera_v2/manifest.json')
    prior = read(ROOT/'review.json')
    identities, updates = settled_identities(prior)
    files = []
    with patch.object(final_review,'ROOT',ROOT):
        for path in ROOT.glob('*.py'):
            source = path.read_text()
            assert len(source.splitlines())<=300
            tree = ast.parse(source)
            compile(tree,str(path),'exec')
            files.append(dict(path=str(path),functions=final_review.functions(path,tree)))
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py','.sbatch','.sh')]
    paths += [ROOT/'review.json',ROOT/'scheduler.txt']
    identities.update({str(p):sha(p) for p in paths})
    result = dict(prior,files=files,identities=identities,settled_log_updates=updates)
    save(ROOT/'final_review.json',result)
    verify(ROOT/'final_review.json')
    print(dict(passed=True,python_files=len(files),settled_log_updates=len(updates)),flush=True)


if __name__=='__main__':
    main()
