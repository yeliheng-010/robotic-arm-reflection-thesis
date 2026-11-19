import sys
import subprocess
from ot_register_v2 import ROOT,RUN,save,sha,verify


def run(entry, mode):
    with (RUN/(entry['name']+'_'+mode+'.log')).open('x') as stream:
        try:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'ot_probe_v2.py'),entry['name'],mode],
                stdout=stream,stderr=subprocess.STDOUT,timeout=600,check=False)
        except subprocess.TimeoutExpired:
            return dict(passed=False,status='timeout_unknown')
    if result.returncode:
        return dict(passed=False,status='verification_error',returncode=result.returncode)
    return verify(RUN/mode/entry['name']/'result.json')


def main():
    manifest=verify(RUN/'manifest.json')
    rows=[]
    for entry in manifest['rows']:
        result=run(entry,'probe')
        if result['passed']:
            result=run(entry,'audit')
        rows.append(dict(name=entry['name'],result=result))
        print(dict(name=entry['name'],**{k:v for k,v in result.items() if k!='identities'}),flush=True)
    verify(RUN/'manifest.json')
    paths=list(RUN.glob('*/*/result.json'))
    save(RUN/'result.json',dict(passed=all(r['result']['passed'] for r in rows),rows=rows,
        reused=manifest['reused'],physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in paths}))
    assert all(r['result']['passed'] for r in rows)


if __name__=='__main__':
    main()
