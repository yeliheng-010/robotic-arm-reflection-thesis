"""复核本地归档；不导入仿真、调用模型或连接服务器。"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files():
    delivery = read(EVIDENCE / 'DELIVERY.json')
    sources = 0
    seen = set()
    for item in delivery['files']:
        name = item['path']
        assert name not in seen, name
        seen.add(name)
        path = (REMOTE / name).resolve()
        assert path.is_relative_to(REMOTE.resolve()), name
        assert sha(path) == item['sha256'], name
        if len(Path(name).parts) == 1 and path.suffix in ('.py', '.sbatch', '.md'):
            assert sha(ROOT / name) == item['sha256'], name
            sources += 1
    inventory = read(REMOTE / 'run/closeout_inventory.json')['files']
    for name, digest in inventory.items():
        assert sha(REMOTE / name) == digest, name
    closeout = read(REMOTE / 'run/closeout_result.json')
    assert sha(REMOTE / 'run/closeout_inventory.json') == closeout['inventory_sha256']
    assert sources == delivery['sourceMatches']
    return dict(downloaded_files=len(seen), frozen_inventory_files=len(inventory),
                local_sources_matched=sources)


def verify_images():
    provenance = read(EVIDENCE / 'FIGURE_PROVENANCE.json')
    checks = {}
    for label, phase in [('initial', 'initial_observation'), ('final', 'final_observation')]:
        item = provenance[label]
        folder = REMOTE / 'run/physical' / phase
        with np.load(ROOT / item['source'], allow_pickle=False) as data:
            # 独立按差分逐帧恢复，避免仅信任原图像生成器。
            pixels = data['first'].astype(np.int32)
            for delta in data['deltas']:
                pixels = pixels + delta.astype(np.int32)
                assert np.all((pixels >= 0) & (pixels <= 255))
        pixels = pixels.astype(np.uint8)
        digest = hashlib.sha256(pixels.tobytes()).hexdigest()
        qualification = read(folder / 'qualification.json')
        assert digest == item['decoded_rgb_sha256']
        assert digest == qualification['rgb']['post']['after_sha256']
        png = EVIDENCE / f'{phase}.png'
        assert sha(png) == item['png_sha256']
        with Image.open(png) as image:
            assert np.array_equal(pixels, np.asarray(image.convert('RGB')))
        assert qualification['accepted'] is (label == 'initial')
        isolation = read(folder / 'isolation.json')
        assert isolation['passed'] is True and isolation['fields'] == 5623
        checks[label] = dict(rgb_sha256=digest, accepted=qualification['accepted'])
    assert sha(EVIDENCE / 'initial_vs_stopped.png') == provenance['figure_sha256']
    assert sha(ROOT / 'figure.py') == provenance['generator_sha256']
    assert provenance['final_image_private_diagnostic_only'] is True
    return checks


def verify_verdict():
    claim = read(REMOTE / 'run/attempt_claim.json')
    assert claim['consumed'] == 1
    assert claim['execution_manifest_sha256'] == sha(REMOTE / 'run/execution_manifest.json')
    result = read(REMOTE / 'run/physical/result.json')
    assert result['success'] is False and result['physical_attempts'] == 1
    assert result['steps'] == 3040
    assert result['stages'] == ['approach_started', 'close_started']
    assert result['safety_error']['error_type'] == 'collision'
    assert result['model_calls'] == 0 and result['training_runs'] == 0
    closeout = read(REMOTE / 'run/closeout_result.json')
    findings = closeout['findings']
    assert findings['failure_verdict_corroborated'] is True
    assert findings['original_exact_audit_passed'] is False
    assert findings['original_exact_audit_failure_preserved'] is True
    assert '6732|FAILED|1:0|' in closeout['job_accounting']
    log = (REMOTE / 'closeout-6757.log').read_text(encoding='utf-8')
    assert 'Ran 10 tests' in log and '\nOK\n' in log
    return dict(success=False, consumed_attempts=1, original_exact_audit_passed=False,
                archived_server_tests=10, server_tests_rerun_this_session=False)


def report_targets():
    report = ROOT / 'REPORT.md'
    names = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    return [(report.parent / name).resolve() for name in names if '://' not in name]


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope='local_archive_only', files=verify_files(),
                  images=verify_images(), verdict=verify_verdict())
    targets = report_targets()
    for target in targets:
        assert target.is_file() or target == OUTPUT.resolve(), str(target)
    result.update(report_links_checked=len(targets), verifier_sha256=sha(Path(__file__)),
                  physical_attempts_added=0, model_calls_added=0, training_runs_added=0,
                  remote_connection_used=False, pending_authorized_closeout_work=[])
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file(), 'Run with --write to create the missing final record'
    for target in targets:
        assert target.is_file(), str(target)
    saved = read(OUTPUT)
    for key in ('files', 'images', 'verdict', 'verifier_sha256', 'report_links_checked'):
        assert saved[key] == result[key], key
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
