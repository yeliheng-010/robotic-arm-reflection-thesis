"""接线正确与失败分支被覆盖是不同门禁；单帧不能验证独立补看。"""


def evaluate(rows):
    motion = all(r['motion']['actual_motion'] and r['motion']['grasp_checked']
                 and r['motion']['carry_checked'] for r in rows)
    failures = [r for r in rows if not r['success']]
    repeated = any(r['observation']['frames'] == 3 and r['observation']['extra'] == 2
                   and r['lifecycle']['evidence'] == 'runtime_event' for r in failures)
    noisy_failure = any('varied_noisy' in r['id'] and r['observation']['frames'] == 3
                        and r['observation']['extra'] == 2 for r in failures)
    meaningful = any(set(r['model_input']['actions'])-{'STOP'} for r in rows)
    return dict(motion_wiring_verified=motion, failure_state_resampling_verified=repeated,
                noisy_failure_resampling_verified=noisy_failure, nonterminal_model_input_available=meaningful,
                model_smoke_gate=motion and repeated and noisy_failure and meaningful,
                failed_cases=len(failures), additional_live_observations=sum(r['observation']['extra'] for r in rows))
