"""抓取接近或到位碰撞后，第三次优先考虑已检查的竖直姿态。"""


def eligible(report):
    if not report or report.get('error_type') != 'collision':
        return False
    phase = report.get('evidence', {}).get('motion_context', {}).get('phase')
    return phase in ('grasp_pose', 'grasp_approach')


def ordered(rows):
    return [row for row in rows if row['id'] != 'original'] + [row for row in rows if row['id'] == 'original']
