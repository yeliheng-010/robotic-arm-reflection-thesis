"""只将白名单测量提供给反思器；原始记录和独立评分不改变。"""
import copy
import numpy as np
from reflection.errors import ErrorReport, ErrorType
from flashnext.client import append

MEASUREMENTS = ('grasp_residual_xy', 'placement_residual_xy', 'held', 'closure', 'contacts',
                'inside_xy', 'inside_z', 'supported', 'settled', 'tilt_deg')
DIAGNOSTICS = ('available_candidate_count', 'selected_candidate_index', 'failure_stage',
               'action', 'motion_segment', 'observation_phase', 'last_completed_motion')
OPTIONAL = ('grasp_residual_xy', 'placement_residual_xy', 'held', 'closure', 'contacts', 'tilt_deg')
RESIDUALS = ('grasp_residual_xy', 'placement_residual_xy')
CLIP_SIGMA = 3


def project_report(report, config, *, attempt):
    raw, opt = report.get('evidence', {}), config['feedback']
    evidence = {k: copy.deepcopy(raw[k]) for k in MEASUREMENTS if k in raw}
    diagnostic = raw.get('diagnostics', {})
    evidence['diagnostics'] = {k: copy.deepcopy(diagnostic[k]) for k in DIAGNOSTICS if k in diagnostic}
    for index, key in enumerate(OPTIONAL):
        if key not in evidence:
            continue
        rng = np.random.default_rng(np.random.SeedSequence([config['seed'], 401, attempt, index]))
        if rng.random() < opt['missing_probability']:
            del evidence[key]
        elif key in RESIDUALS:
            noise = np.clip(rng.normal(size=2), -CLIP_SIGMA, CLIP_SIGMA)*opt['residual_sigma_m']
            evidence[key] = (np.asarray(evidence[key])+noise).tolist()
    evidence['measurement_protocol'] = dict(opt, labels='ideal_error_class_and_stage',
                                            units='metres', input='text_only')
    return dict(error_type=report['error_type'], stage=report['stage'],
                message='Detected task failure: '+report['error_type'], evidence=evidence,
                detector='controlled_measurement_projection', image_paths=[], timestamp=0, action_index=None)


def check_action(answer, parameters, *, candidate_count=None):
    if any(answer.changes.get(key) for key in ('replan', 'reground')):
        raise ValueError('Unsupported action for fixed planner/perception: replan or reground')
    updated = parameters.updated(answer.changes)
    if updated == parameters:
        raise ValueError('Correction does not change any parameter')
    if 'candidate_index' in answer.changes and candidate_count is not None:
        if answer.changes['candidate_index'] >= candidate_count:
            raise ValueError('Unavailable candidate index')
    return answer


class ProjectedReflector:
    def __init__(self, inner, config, *, directory):
        self.inner, self.config = inner, config
        self.path = directory/'feedback.jsonl'
        self.history = []
        self.calls = 0

    def reflect(self, report, parameters, history=()):
        self.calls += 1
        projected = project_report(report.to_dict(), self.config, attempt=self.calls)
        event = dict(attempt=self.calls, projected=projected, history=copy.deepcopy(self.history))
        value = ErrorReport(ErrorType(projected['error_type']), projected['message'],
                            projected['evidence'], detector=projected['detector'], timestamp=0)
        try:
            answer = self.inner.reflect(value, parameters, self.history)
            count = value.evidence['diagnostics'].get('available_candidate_count')
            check_action(answer, parameters, candidate_count=count)
            event['answer'] = answer.to_dict()
            self.history.append({'error': projected, 'reflection': answer.to_dict()})
            return answer
        except (ValueError, RuntimeError) as error:
            event['error'] = repr(error)
            raise
        finally:
            append(self.path, event)
