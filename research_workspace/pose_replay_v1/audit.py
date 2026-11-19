"""独立进程对预定首中末样本复算，完整来源与统计核对。"""
from pose_replay_v1.common import ROOT, folders, identities, read, save, load, truth_path
from pose_replay_v1.runtime import single, pair
from pose_replay_v1.evaluate import annotate, compare


def selected(rows):
    return [rows[i] for i in sorted({0, len(rows)//2, len(rows)-1})] if rows else []


def check_fits(folder, fitted):
    checks = []
    for kind in ("singles", "pairs"):
        for row in selected(fitted[kind]):
            repeat = row["repeat"]
            indices = row.get("indices", [row.get("index")])
            clouds = [load(folder, index, repeat=repeat) for index in indices]
            actual = single(clouds[0]) if kind == "singles" else pair(clouds, [single(c) for c in clouds])
            expected = {key: value for key, value in row.items() if key not in ("index", "indices", "repeat")}
            assert expected == actual
            checks.append(dict(kind=kind, indices=indices, repeat=repeat, identical=True))
    return checks


def main():
    before = read(ROOT / "started.json")["inputs"]
    assert before == identities()
    report = read(ROOT / "analysis.json")["groups"]
    checks = {}
    for name, folder in folders().items():
        fitted = read(ROOT / f"{name}_fits.json")
        checks[name] = check_fits(folder, fitted)
        original = read(folder / "private_errors.json")
        truth = read(truth_path(name, folder))
        actual = {kind: annotate(fitted[kind], original[kind], truth) for kind in ("singles", "pairs")}
        assert actual == read(ROOT / f"{name}_private_errors.json")
        assert report[name] == {kind: compare(original[kind], actual[kind]) for kind in actual}
    assert before == identities()
    save(ROOT / "audit.json", dict(passed=True, checks=checks, inputs_unchanged=True,
         independent_process=True, physical_success_verified=False))
    print(dict(passed=True, checks=sum(len(v) for v in checks.values())), flush=True)


if __name__ == "__main__":
    main()
