import subprocess
import time
POLL_SECONDS=10
ACCOUNTING_GRACE=120

def active(job):
    return bool(subprocess.check_output(['squeue','-h','-j',job,'-o','%i'],text=True).strip())


def wait_job(job,deadline):
    missing=None
    while time.monotonic()<deadline:
        if not active(job):
            text=subprocess.check_output(['sacct','-X','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode'],text=True)
            rows=[r.split('|')[:3] for r in text.splitlines() if r.strip()]
            if rows:
                assert all(r[1:]==['COMPLETED','0:0'] for r in rows),str(rows)
                return rows
            missing=missing or time.monotonic()
            assert time.monotonic()-missing<ACCOUNTING_GRACE,'Accounting unavailable'
        time.sleep(POLL_SECONDS)
    raise TimeoutError('Controller deadline reached')


