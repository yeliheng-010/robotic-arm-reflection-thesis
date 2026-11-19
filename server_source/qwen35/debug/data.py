"""Text-only reflection format. No injected fault label or future outcome is an input."""
import json

SYSTEM = (
    'Diagnose a UR5e pick-and-place failure using only the supplied evidence. '
    'Return one JSON object {"cause":str,"changes":{...}}. Changes are absolute values; '
    'omit unchanged fields. Allowed fields: replan/reground (boolean); lift_height '
    '(metres, 0.10..0.48); time_scale (duration multiplier, 0.5..3); grasp_offset/place_offset '
    '(metre xyz vectors, each component -0.25..0.25); candidate_index (integer 0..4). '
    'Use evidence and earlier attempts; do not invent measurements. No images are available.'
)


def stable_error(error):
    return {k: v for k, v in error.items() if k not in ('timestamp', 'image_paths')}


def make_messages(instruction, error, parameters, history, answer):
    evidence = {
        'instruction': instruction,
        'error': stable_error(error),
        'parameters': parameters,
        'history': [
            {'error': stable_error(item['error']), 'reflection': item['reflection']}
            for item in history
        ],
    }
    return [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))},
        {'role': 'assistant', 'content': json.dumps(answer, ensure_ascii=False, separators=(',', ':'))},
    ]


def encode_example(tokenizer, messages, max_length, chat_template_kwargs=None):
    """Mask all prompt tokens and reject truncation rather than silently losing labels."""
    if [m.get('role') for m in messages] != ['system', 'user', 'assistant']:
        raise ValueError('Expected system, user, assistant messages')
    kwargs = chat_template_kwargs or {}
    prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, **kwargs)
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False, **kwargs)
    prompt_ids = tokenizer(prompt, add_special_tokens=False)['input_ids']
    full_ids = tokenizer(full, add_special_tokens=False)['input_ids']
    if full_ids[:len(prompt_ids)] != prompt_ids:
        raise ValueError('Chat template does not preserve the prompt prefix')
    if len(full_ids) > max_length:
        raise ValueError(f'Example has {len(full_ids)} tokens, exceeds max_length={max_length}; no truncation applied')
    if len(full_ids) <= len(prompt_ids):
        raise ValueError('Example has no answer tokens')
    return {
        'input_ids': full_ids,
        'attention_mask': [1] * len(full_ids),
        'labels': [-100] * len(prompt_ids) + full_ids[len(prompt_ids):],
    }
