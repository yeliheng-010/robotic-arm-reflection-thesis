"""闭合静态采样门禁；不将静态通过等同动态安全。"""


def summarize(rows, *, expected_count):
    complete = expected_count > 0 and len(rows) == expected_count
    rejected = [i for i, row in enumerate(rows)
                if row.get('valid') is not True or row.get('contacts') != []]
    passed = complete and not rejected
    return dict(passed=passed, samples=len(rows), expected_samples=expected_count,
                complete=complete, first_rejected_index=rejected[0] if rejected else None,
                dynamic_safety_proven=False)


def public_feedback(result):
    return dict(status='passed' if result['passed'] else 'rejected', stage='gripper_closure')
