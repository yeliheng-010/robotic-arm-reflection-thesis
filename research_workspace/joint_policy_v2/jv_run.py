import sys
import subprocess
from jv_register import ROOT,RUN,save,sha,verify

TIMEOUT = 180


def run(entry, mode):
    with (RUN/(entry['name']+'_'+mode+'.log')).open('x') as stream:
        try:
            result = subprocess.run([sys.executable,'-B',str(ROOT/'jv_probe.py'),entry['name'],mode],
                stdout=stream,stderr=subprocess.STDOUT,timeout=TIMEOUT,check=False)
        except subprocess.TimeoutExpired:
            return dict(status='timeout_unknown',passed=False)
    if result.returncode:
        return dict(status='verification_error',passed=False,returncode=result.returncode)
    return verify(RUN/mode/entry['name']/'result.json')


def main():
    manifest=verify(RUN/'manifest.json')
    rows=[]
    for entry in manifest['rows']:
        result=run(entry,'probe')
        if result['passed']:
            result=run(entry,'audit')
        row=dict(name=entry['name'],result=result)
        save(RUN/(entry['name']+'_summary.json'),row)
        rows.append(row)
        print(dict(name=entry['name'],passed=result['passed'],qualified=result.get('qualified')),flush=True)
    verify(RUN/'manifest.json')
    save(RUN/'result.json',dict(passed=all(r['result']['passed'] for r in rows),rows=rows,
        physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in RUN.glob('*_summary.json')}))
    assert all(r['result']['passed'] for r in rows)


if __name__ == '__main__':
    main()
