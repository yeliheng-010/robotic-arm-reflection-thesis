"""使用新的真实碰撞报告检查冻结教师，结果仅用于开发诊断。"""
import json
import os
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters
from stability.teacher import AuditedTeacher
from stability.experiment import OUT


def main():
    rows = []
    name = os.environ.get('PROBE_NAME', 'compact_teacher_probe')
    cases = os.environ.get('PROBE_CASES', '01,03,05').split(',')
    assert all(case in ('01', '03', '05') for case in cases)
    for case in cases:
        result = json.loads((OUT/'train_v3'/case/'stable/result.json').read_text())
        record = result['records'][0]
        raw = record['error']
        report = ErrorReport(ErrorType(raw['error_type']), raw['message'], raw['evidence'], detector=raw['detector'])
        teacher = AuditedTeacher(result['instruction'], OUT/name/case)
        try:
            answer = teacher.reflect(report, Parameters().updated(record['parameters']))
            rows.append(dict(case=case, answer=answer.to_dict()))
        except RuntimeError as exc:
            rows.append(dict(case=case, error=str(exc)))
    (OUT/(name+'.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == '__main__':
    main()
