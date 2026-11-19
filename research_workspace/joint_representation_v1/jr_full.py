"""独立复算等价角路径及完整抓取/搬运链。"""
import sys
from reflection.__main__ import bootstrap
bootstrap()
from cp_probe import inspect
from cp_common import current
from js_common import NAME, save, read, sha, verify
from js_audit import audit_edges
from jr_probe import ROOT,RUN
from jr_scope import context


def main(mode):
    assert mode in ('full','audit')
    verify(RUN/'manifest.json')
    result = verify(RUN/'result.json')
    if result['selected'] is None:
        save(ROOT/(mode+'_skipped.json'),dict(reason='no_safe_pregrasp',physical_attempts=0))
        return
    checks = audit_edges(result['selected'])
    with context(result['selected']):
        plan,trace = inspect(current(NAME))
    output = ROOT/mode
    save(output/'plan.json',plan)
    save(output/'trace.json',trace)
    save(output/'edges.json',checks)
    if mode == 'audit':
        assert plan == read(ROOT/'full/plan.json')
        assert trace == read(ROOT/'full/trace.json')
        assert checks == read(ROOT/'full/edges.json')
    verify(RUN/'manifest.json')
    save(output/'result.json',dict(qualified=plan['selected'] is not None,passed=True,
        independent=mode=='audit',selected_id=(plan['selected'] or {}).get('id'),status=plan['status'],
        physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in output.glob('*.json')}))
    print(dict(mode=mode,qualified=plan['selected'] is not None,status=plan['status']),flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
