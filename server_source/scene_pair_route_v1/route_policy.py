"""目标箱碰撞反馈门控，不读取任务编号或成功标签。"""
def eligible(report, destination):
    if not report or report.get('error_type') != 'collision':
        return False
    pairs = report.get('evidence', {}).get('contacts', [])
    return any(destination in pair and any(root in pair for root in ('ur5e_base', '2f85_base')) for pair in pairs)


def first_feasible(rows, excluded):
    return next((row for row in rows if row['feasible'] and row['id'] not in excluded), None)
