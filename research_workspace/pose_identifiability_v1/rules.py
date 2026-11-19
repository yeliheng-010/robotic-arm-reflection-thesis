"""离线规则统计，不修改任务资格或释放许可。"""
import math


def evaluate_rule(rows, threshold):
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("invalid_threshold")
    accepted = [row for row in rows if row.get("quality_passed") is True
                and math.isfinite(row["visibility"]) and threshold <= row["visibility"] <= 1]
    correct = sum(row["accurate"] for row in accepted)
    return dict(total=len(rows), accepted=len(accepted), correct_accepted=correct,
                false_accepted=len(accepted)-correct, rejected=len(rows)-len(accepted),
                coverage=len(accepted)/len(rows) if rows else None,
                accepted_accuracy=correct/len(accepted) if accepted else None)
