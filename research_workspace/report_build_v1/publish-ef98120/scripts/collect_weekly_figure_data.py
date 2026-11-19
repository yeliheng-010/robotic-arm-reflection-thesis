"""只读提取冻结实验数据及已有截图，不运行仿真或模型。"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SOURCE_FILES = {
    "sft159": "candidate_sft_v2/training/updates.json",
    "sft189": "set_sft_v1/training/updates.json",
    "sft_audit": "candidate_sft_v2/verification.json",
    "closed_loop": "set_closed_loop_v2/verification.json",
    "aggregation": "observation_model_control_v1/verification.json",
    "active": "active_observation_model_v2/verification.json",
    "diagnostic": "observation_decision_diagnostic_v2/verification.json",
    "noise": "noise_feedback_v1/result.json",
    "scene_protocol": "scene_expansion_v1/protocol.json",
}
FACTORS = ("position_1cm", "position_3cm", "yaw_30deg", "combined", "container_1cm")
METHODS = ("fixed_first", "adaptive", "base_current", "base_history")
SCENE_SEED = 910001
CASE_ID = "M1_940301_grasp_place"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root, destination):
    records, provenance = {}, []
    for name, relative in SOURCE_FILES.items():
        path = root / relative
        records[name] = json.loads(path.read_text())
        provenance.append({"source": relative, "sha256": digest(path)})
    assert len(records["sft159"]) == 20 and len(records["sft189"]) == 24
    assert records["diagnostic"]["passed"] and records["diagnostic"]["complete"]
    for name in ("closed_loop", "aggregation", "active"):
        assert records[name]["passed"] and records[name]["complete"]
    destination.mkdir(parents=True, exist_ok=True)
    return records, provenance


def copy_image(root, relative, *, destination, name):
    source = root / relative
    output = destination / (name + ".png")
    shutil.copyfile(source, output)
    captured = datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()
    return {"file": output.name, "source": relative, "sha256": digest(source),
            "source_file_mtime_utc": captured,
            "crop": "none", "color_adjustment": "none"}


def scenes(root, destination, protocol):
    rows = []
    for factor in FACTORS:
        identity = f"E0_{SCENE_SEED}_{factor}"
        relative = f"scene_expansion_v1/qualification/{identity}/1/attempt_1/before.png"
        row = copy_image(root, relative, destination=destination, name=factor)
        row.update(condition=identity, scenario=protocol["scenarios"][identity])
        rows.append(row)
    identity = f"E0_{SCENE_SEED}_position_1cm"
    path = f"scene_expansion_v1/qualification/{identity}/0/attempt_1/before.png"
    row = copy_image(root, path, destination=destination, name="no_divider")
    row.update(condition=identity, note="同1cm布局的无挡板控制；不是零扰动基线")
    return [row] + rows


def recovery(root, destination):
    rows = []
    for method in METHODS:
        base = f"active_observation_model_v2/tasks/{CASE_ID}/{method}"
        result = json.loads((root / base / "result.json").read_text())
        image_path = f"{base}/attempt_3/attempt_1/after.png"
        row = copy_image(root, image_path, destination=destination, name="case_" + method)
        row.update(method=method, condition=CASE_ID, success=result["success"],
                   result_source=base + "/result.json",
                   result_sha256=digest(root / base / "result.json"))
        rows.append(row)
    return rows


def noise_rows(records):
    result = []
    for row in records["noise"]["rows"]:
        for field, audit in row["audit"].items():
            result.append({"fixture": row["fixture"], "seed": row["seed"],
                           "sigma_m": row["profile"]["sigma_m"],
                           "missing_probability": row["profile"]["missing_probability"],
                           "field": field, "missing": audit["missing"],
                           "delta_m": audit.get("delta"),
                           "original_m": audit["original"]})
    return result


def make_data(records):
    return {
        "training": {key: records[key] for key in ("sft159", "sft189")},
        "validation": {key: records["sft_audit"][key]["metrics"]
                       for key in ("before", "after")},
        "closed_loop": [r for r in records["closed_loop"]["metrics"] if r["field"] == "all"],
        "aggregation": records["aggregation"]["budget_analysis"]["curves"],
        "active": records["active"]["analysis"],
        "diagnostic": records["diagnostic"]["analysis"],
        "noise": noise_rows(records),
        "noise_summary": records["noise"]["summary"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records, provenance = snapshot(args.experiment_root, args.output)
    image_dir = args.output / "raw"
    image_dir.mkdir(exist_ok=True)
    data = make_data(records)
    data["scene_images"] = scenes(args.experiment_root, image_dir, records["scene_protocol"])
    data["recovery_images"] = recovery(args.experiment_root, image_dir)
    data["sources"] = provenance
    data["selection"] = {
        "scene": "预登记五种因素均展示；统一首个种子910001和RedBlock组合",
        "case": "展示已报告的自适应独胜案例940301；仅解释机制，不估计总体频率",
        "noise": "全部72投影的全部原有残差字段；缺失单列，不补零",
        "metrics": "使用全部原始更新/条件，无平滑、无挑选最佳epoch",
    }
    (args.output / "source_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(provenance), "images": 10,
                      "noise_fields": len(data["noise"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
