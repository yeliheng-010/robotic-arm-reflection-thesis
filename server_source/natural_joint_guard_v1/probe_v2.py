from pathlib import Path
from unittest.mock import patch
import probe
from bounded_ik_v2 import context


if __name__=='__main__':
    original = Path(__file__).resolve().parent
    previous = probe.read(original/'manifest.json')
    assert all(probe.sha(p)==h for p,h in previous['identities'].items())
    target = original/'revision_v2'
    target.mkdir(exist_ok=False)
    # 测试发现仍从原目录读取，输出写入新版本，不覆盖已冻结证据。
    original_discover = probe.unittest.defaultTestLoader.discover
    with patch.object(probe, 'context', context), patch.object(probe,'ROOT',target), \
         patch.object(probe.unittest.defaultTestLoader,'discover',lambda _:original_discover(str(original))):
        probe.main()
    probe.save(target/'revision_identity.json', dict(previous_manifest_sha256=probe.sha(original/'manifest.json'),
        identities={str(p):probe.sha(p) for p in original.iterdir() if p.suffix in ('.py','.sbatch')}))
