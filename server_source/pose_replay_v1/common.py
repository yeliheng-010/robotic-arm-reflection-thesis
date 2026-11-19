import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
PHASES = ("preflight", "after_lift", "before_release")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def folders():
    result = {phase: PROJECT / "visibility_calibration_v1/phases" / phase for phase in PHASES}
    result.update({f"boundary_v{v}": PROJECT / f"visibility_boundary_v{v}" for v in (1, 2)})
    return result


def truth_path(name, folder):
    if name.startswith("boundary"):
        return PROJECT / "visibility_calibration_v1/phases/before_release/private_truth.json"
    return folder / "private_truth.json"


def load(folder, index, *, repeat):
    path = folder / f"view_{index}"
    with np.load(path / "clouds.npz") as arrays:
        return arrays[f"noise_{repeat}"].copy()


def identities():
    result = {}
    for name, folder in folders().items():
        fits = read(folder / "fits.json")
        paths = [folder / n for n in ("fits.json", "views.json", "private_errors.json")]
        paths.append(truth_path(name, folder))
        for index in sorted({r["index"] for r in fits["singles"]}):
            path = folder / f"view_{index}"
            assert sha(path / "clouds.npz") == read(path / "metadata.json")["clouds_sha256"]
            paths.extend([path / "clouds.npz", path / "metadata.json"])
        result.update({str(p.relative_to(PROJECT)): sha(p) for p in paths})
    paths = [PROJECT / p for p in read(ROOT / "source_identities.json")]
    result.update({str(p.relative_to(PROJECT)): sha(p) for p in paths})
    return result
