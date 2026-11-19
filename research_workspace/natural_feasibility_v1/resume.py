"""只继续未完成静态条件，每条件独立进程释放MuJoCo资源。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import hashlib

ROOT=Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'result.json').exists()
    manifest=read(ROOT/'manifest.json')
    assert all(sha(p)==h for p,h in manifest['identities'].items())
    reused,rows=[],[]
    for case in manifest['cases']:
        name=case['item']['id']
        result=ROOT/'results'/(name+'.json')
        if result.exists():
            row=read(result)
            assert row['id']==name and sha(row['path'])==row['sha256']
            reused.append(name)
        else:
            with (ROOT/(name+'-resume.log')).open('x') as log:
                subprocess.run([sys.executable,'-B',str(ROOT/'qualify_one.py'),name],
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
            row=read(result)
        rows.append(row)
        print(dict(id=name,reused=name in reused,passed=row['passed']),flush=True)
    assert all(sha(p)==h for p,h in manifest['identities'].items())
    with (ROOT/'result.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(rows=rows,reused_static_results=reused,physical_attempts=0,model_calls=0,
            training_ready=False,identities={str(ROOT/n):sha(ROOT/n) for n in ('resume.py','qualify_one.py','resume.sbatch')},
            limitation='Finite nominal geometric search; no physical recovery claims'),stream,indent=2)


if __name__=='__main__':
    main()
