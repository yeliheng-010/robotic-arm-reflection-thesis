"""从公共镜像下载固定版本，并使用官方API提供的哈希逐文件核对。"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import urllib.parse
from stability.experiment import OUT

ROOT = OUT/'models/Qwen3.5-9B'
CHUNK = 8*1024*1024


def verify(path, entry):
    if path.stat().st_size != entry['size']:
        raise ValueError('Size mismatch: '+entry['name'])
    checksum = hashlib.sha256() if entry['sha256'] else hashlib.sha1()
    if not entry['sha256']:
        checksum.update(f"blob {entry['size']}\0".encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            checksum.update(chunk)
    assert checksum.hexdigest() == (entry['sha256'] or entry['blob']), entry['name']


def transfer(url, temporary):
    offset = temporary.stat().st_size if temporary.exists() else 0
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(request, timeout=90) as response:
        append = response.status == 206 and offset > 0
        if append:
            assert response.headers['Content-Range'].startswith(f'bytes {offset}-')
        with temporary.open('ab' if append else 'wb') as stream:
            for chunk in iter(lambda: response.read(CHUNK), b''):
                stream.write(chunk)


def download(entry, *, manifest):
    assert Path(entry['name']).name == entry['name']
    path = ROOT/entry['name']
    if path.exists():
        verify(path, entry)
        return entry['name']
    temporary = path.with_name(path.name+'.part')
    query = urllib.parse.urlencode({'Revision': 'master', 'FilePath': entry['name']})
    url = f"https://modelscope.cn/api/v1/models/{manifest['repo']}/repo?{query}"
    for attempt in range(3):
        try:
            if not temporary.exists() or temporary.stat().st_size != entry['size']:
                transfer(url, temporary)
            verify(temporary, entry)
            temporary.replace(path)
            print(json.dumps({'verified': entry['name'], 'bytes': entry['size']}), flush=True)
            return entry['name']
        except Exception as error:
            print(json.dumps({'file': entry['name'], 'attempt': attempt+1, 'error': str(error)}), flush=True)
            if attempt == 2:
                raise
            time.sleep(3)


def main():
    manifest = json.loads((OUT/'model9-manifest.json').read_text(encoding='utf-8-sig'))
    ROOT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        files = list(pool.map(lambda entry: download(entry, manifest=manifest), manifest['files']))
    (OUT/'model9-ready.json').write_text(json.dumps({'manifest': manifest, 'verified_files': files,
        'transport': 'modelscope_public_api', 'integrity': 'official_huggingface_pinned_revision_hashes'}, indent=2))


if __name__ == '__main__':
    main()
