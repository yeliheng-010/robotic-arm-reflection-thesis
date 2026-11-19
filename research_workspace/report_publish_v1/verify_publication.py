"""核对发布链接、统计、图片和公开来源，不访问远端实验环境。"""
import ast
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

import fitz

ROOT = Path(__file__).resolve().parents[1] / "thesis-research-progress"
EVIDENCE = ROOT / "evidence/visibility_6495_6497"
PACKAGES = ("model_grasp_gpu_v3", "surface_grasp_v1", "surface_physical_v1", "held_observation_v3")


def engineering_context():
    rows = []
    for package in PACKAGES:
        source = ROOT.parent / package / "REPORT.md"
        rows.append(f"| {package}/REPORT.md | `{hashlib.sha256(source.read_bytes()).hexdigest()}` |")
    text = """# 前序工程进展的报告摘录

以下为已有原报告的精选事实；完整轨迹和报告保留实验环境，哈希标识来源版本。不是本次重新执行的结果。

- 6481：模型两次合法抓取意图，第二次根据plan_rejected修改抓点；安全规划均拒绝，0物理执行。
- 6484：表面候选surface_0022找到安全端点和静态路径，仍不等于抓放成功。
- 6486：单次抓起、搬运、释放、归位，终态物体箱外；作业FAILED/1:0。6488补回原审计配置上下文后只读复算通过，task_success=false，未重跑动作。
- 搬运227/227采样有双侧指垫接触，物体相对TCP变化64.96 mm，释放前预测偏差63.33 mm；TCP水平误差2.75 mm，终态物体相对箱中心水平偏差81.34 mm。这些私有审计量不输入模型，不唯一证明滑移或滚动。
- 6492：抬升后、释放前各0/32个全帧合格视角；6494复现拒绝，旧在线观察严格无扰动审计仍false。新独立快照渲染实现不代表已修复旧入口。
- 累计物理成功账本3/8来自不同工程迭代，非同版本统一评测，不与早期5/24等批次合并。

| 实验包内报告标识 | SHA256 |
|---|---|
"""
    (EVIDENCE / "engineering_context.md").write_text(text + "\n".join(rows) + "\n", encoding="utf-8")


def check_documents():
    paths = [ROOT / "README.md", *ROOT.glob("docs/*.md"), *EVIDENCE.glob("*.md")]
    failures = []
    count = 0
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"!?\[[^\]]*\]\(([^\s)]+)\)", content):
            link = match.group(1).split("#")[0]
            if not link or re.match(r"[a-zA-Z]+:", link):
                continue
            count += 1
            if not (path.parent / unquote(link)).exists():
                failures.append(f"{path.relative_to(ROOT)}: {link}")
    return {"links_checked": count, "missing_links": failures}


def check_figures():
    results = []
    for pdf in (ROOT / "assets/visibility_6495_6497").glob("*.pdf"):
        with fitz.open(pdf) as document:
            page = document[0]
            width, height = page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72
            assert abs(width - 180) < 0.01 and abs(height - 112) < 0.01
            results.append({"figure": pdf.stem, "width_mm": width, "height_mm": height})
    assert len(results) == 3
    return results


def check_scripts():
    results = []
    for name in ("collect_visibility_report.py", "plot_visibility_report.py"):
        path = ROOT / "scripts" / name
        code = path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        assert len(code.splitlines()) <= 300
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
                assert len(node.args.args) <= 3, node.name
        results.append(name)
    return results


def main():
    engineering_context()
    result = check_documents()
    result["figures"] = check_figures()
    result["scripts"] = check_scripts()
    with (EVIDENCE / "measurements.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 192
    result["measurement_count"] = len(rows)
    result["passed"] = not result["missing_links"]
    (ROOT.parent / "report_publish_v1/validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert result["passed"], "文档含失效的相对链接"


if __name__ == "__main__":
    main()
