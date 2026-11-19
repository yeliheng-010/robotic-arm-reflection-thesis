"""生成前保存实际输入、模板及来源指纹。"""
import hashlib
import importlib.metadata
from pathlib import Path
import sys
import numpy as np
from qualified_prompt_checkpoint_v1.protocol import PROJECT, RUN, save, sha


def loaded_project_sources(manifest):
    paths = set()
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if not name:
            continue
        path = Path(name).resolve()
        if path.is_relative_to(PROJECT) and path.suffix == '.py' and 'site-packages' not in path.parts:
            paths.add(path)
    result = {}
    for path in sorted(paths):
        expected = manifest['identities'].get(str(path))
        assert expected is not None and sha(path) == expected, str(path)
        result[str(path)] = expected
    return result


def record(generator, values, *, manifest, encoding):
    arrays = {key: value.detach().cpu().contiguous().numpy() for key, value in values.items()}
    with (RUN / 'input_tensors.npz').open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    tensors = {key: dict(shape=list(a.shape), dtype=str(a.dtype),
                        sha256=hashlib.sha256(a.tobytes()).hexdigest()) for key, a in arrays.items()}
    processor = generator.processor
    save(RUN / 'encoding.json', dict(encoding=encoding, identity=generator.identity,
         input_ids=arrays['input_ids'].tolist(), attention_mask=arrays['attention_mask'].tolist(),
         tensors=tensors, npz_sha256=sha(RUN / 'input_tensors.npz')))
    save(RUN / 'templates.json', dict(processor_chat_template=processor.chat_template,
         tokenizer_chat_template=processor.tokenizer.chat_template,
         decoded_input=processor.tokenizer.decode(arrays['input_ids'][0].tolist(), skip_special_tokens=False)))
    from f_response import MAX_INPUT_TOKENS, MAX_TOKENS, SEED
    save(RUN / 'generation_config.json', dict(model=generator.model.generation_config.to_dict(),
         explicit=dict(max_new_tokens=MAX_TOKENS, do_sample=False, use_cache=True, logits_to_keep=1,
                       pad_token_id=generator.tokenizer.pad_token_id),
         seed=SEED, enable_thinking=False, max_input_tokens=MAX_INPUT_TOKENS,
         environment=generator.environment,
         versions={name: importlib.metadata.version(name) for name in
                   ('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes', 'numpy', 'Pillow')},
         loaded_project_sources=loaded_project_sources(manifest)))
