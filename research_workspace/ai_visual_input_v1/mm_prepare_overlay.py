import os
from mm_common import ROOT, read, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID')
    previous = ROOT/'temporal_v2'
    manifest = read(previous/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    assert (previous/'failure.json').exists() and not list(previous.glob('*_generation_started.json'))
    assert 'Torchvision' in read(previous/'failure.json')['error']
    overlay = ROOT/'torchvision_overlay'
    metadata = overlay/'torchvision-0.21.0+cu124.dist-info/METADATA'
    assert metadata.exists()
    target = ROOT/'temporal_v3'
    target.mkdir(exist_ok=False)
    save(target/'input.json', read(previous/'input.json'))
    identities = dict(manifest['identities'])
    files = [p for p in overlay.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for path in [*files, previous/'manifest.json', previous/'failure.json', target/'input.json',
                 ROOT/'dependencies.sbatch', ROOT/'mm_prepare_overlay.py', ROOT/'mm_overlay_run.py',
                 ROOT/'overlay_prepare.sbatch', ROOT/'overlay_model.sbatch', ROOT/'validate_dependencies.sbatch']:
        identities[str(path)] = sha(path)
    save(target/'manifest.json', dict(identities=identities, model_calls=2, prior_generation_calls=0,
        physical_attempts=0, training_ready=False, dependency_scope='isolated_torchvision_overlay',
        torch='2.6.0+cu124', torchvision='0.21.0+cu124', overlay_files=len(files)))
    print(dict(overlay_files=len(files), frozen=sha(target/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
