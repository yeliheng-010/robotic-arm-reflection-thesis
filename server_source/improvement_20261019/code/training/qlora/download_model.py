"""Download public ModelScope safetensors with size/hash checks and resumable partials."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.parse
import urllib.request


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--model-id', default='Qwen/Qwen2.5-7B-Instruct')
    args = parser.parse_args()
    root = args.root.resolve()
    model_dir = root / 'models' / args.model_id.split('/')[-1]
    model_dir.mkdir(parents=True, exist_ok=True)
    endpoint = 'https://modelscope.cn/api/v1/models/' + args.model_id
    with urllib.request.urlopen(endpoint + '/repo/files?Revision=master&Recursive=true', timeout=30) as response:
        metadata = json.load(response)
    if not metadata.get('Success'):
        raise RuntimeError('ModelScope did not return a successful file listing')
    files = []
    for item in metadata['Data']['Files']:
        name = item.get('Path', item.get('Name', ''))
        if '/' not in name and (name.endswith(('.safetensors', '.json', '.txt', '.model', '.jinja')) or name in ('LICENSE', 'README.md')):
            files.append(item)
    if not any(item.get('Name', '').endswith('.safetensors') for item in files):
        raise RuntimeError('No safetensors weights in the public repository')
    state = {'phase': 'downloading', 'model_id': args.model_id,
             'total_bytes': sum(item['Size'] for item in files), 'files': {}}
    lock = threading.Lock()

    def update(name, **values):
        with lock:
            state['files'].setdefault(name, {}).update(values)
            state['updated_at'] = time.time()
            state['downloaded_bytes'] = sum(v.get('bytes', 0) for v in state['files'].values())
            atomic_json(root / 'download_status.json', state)

    def digest(path):
        result = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                result.update(block)
        return result.hexdigest()

    def download(item):
        name = item.get('Path', item['Name'])
        target, partial = model_dir / name, model_dir / (name + '.partial')
        size = item['Size']
        expected_hash = item.get('Sha256') or item.get('SHA256')
        if target.exists() and target.stat().st_size == size:
            actual_hash = digest(target)
            if not expected_hash or actual_hash.lower() == expected_hash.lower():
                update(name, bytes=size, status='verified')
                return {'name': name, 'bytes': size, 'sha256': actual_hash, 'server_sha256': expected_hash}
            raise RuntimeError('Existing file checksum mismatch: ' + name)
        query = urllib.parse.urlencode({'Revision': 'master', 'FilePath': name})
        url = endpoint + '/repo?' + query
        for attempt in range(4):
            try:
                offset = partial.stat().st_size if partial.exists() else 0
                headers = {'Range': f'bytes={offset}-'} if offset else {}
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                    if offset and response.status != 206:
                        offset = 0
                    if response.status == 206:
                        content_range = response.headers.get('Content-Range', '')
                        if not content_range.startswith(f'bytes {offset}-'):
                            raise RuntimeError('Unexpected HTTP range for ' + name)
                    update(name, bytes=offset, status='downloading')
                    last_update = 0
                    with partial.open('ab' if offset else 'wb') as output:
                        while True:
                            block = response.read(4 * 1024 * 1024)
                            if not block:
                                break
                            output.write(block)
                            offset += len(block)
                            if time.monotonic() - last_update > 5:
                                update(name, bytes=offset)
                                last_update = time.monotonic()
                if offset != size:
                    raise RuntimeError(f'Incomplete file {name}: {offset}/{size}')
                update(name, bytes=offset, status='checking_hash')
                actual_hash = digest(partial)
                if expected_hash and actual_hash.lower() != expected_hash.lower():
                    raise RuntimeError('Downloaded file checksum mismatch: ' + name)
                partial.replace(target)
                update(name, bytes=size, status='verified')
                print('verified', name, size, flush=True)
                return {'name': name, 'bytes': size, 'sha256': actual_hash, 'server_sha256': expected_hash}
            except Exception as exc:
                update(name, status='retrying', error=type(exc).__name__)
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            downloaded = list(pool.map(download, files))
        manifest = {'model_id': args.model_id, 'downloaded_at': time.time(),
                    'revision_requested': 'master', 'files': downloaded}
        atomic_json(model_dir / 'download_manifest.json', manifest)
        state['phase'] = 'ready'
        state['model_dir'] = str(model_dir)
        state['updated_at'] = time.time()
        atomic_json(root / 'download_status.json', state)
    except BaseException:
        state['phase'] = 'failed'
        state['updated_at'] = time.time()
        atomic_json(root / 'download_status.json', state)
        raise


if __name__ == '__main__':
    main()
