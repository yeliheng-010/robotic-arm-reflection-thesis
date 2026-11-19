from pathlib import Path
from unittest.mock import patch
import check
from visual_requests_v2 import build


if __name__=='__main__':
    source=Path(__file__).resolve().parent
    previous=check.read(source/'verification.json')
    assert all(check.sha(p)==h for p,h in previous['identities'].items())
    target=source/'revision_v2'
    target.mkdir(exist_ok=False)
    with patch.object(check,'build',build),patch.object(check,'ROOT',target):
        # 原检查脚本的身份列表引用ROOT/visual_requests.py，提供新版本身份文件。
        (target/'visual_requests.py').write_bytes((source/'visual_requests_v2.py').read_bytes())
        check.main()
    bundle=check.read(target/'input.json')
    assert 'All attempts' not in bundle['request']['execution_semantics']['fixed_executor']
    check.save(target/'revision_identity.json',dict(previous_verification_sha256=check.sha(source/'verification.json'),
        identities={str(source/n):check.sha(source/n) for n in ('visual_requests_v2.py','check_v2.py')}))
