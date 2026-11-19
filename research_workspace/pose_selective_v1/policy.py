"""只根据已有质量检查结果决定是否使用修复候选，不读取真值。"""


def choose(original_quality, repaired_quality):
    if original_quality is True:
        return "original"
    if repaired_quality is True:
        return "repaired"
    return None
