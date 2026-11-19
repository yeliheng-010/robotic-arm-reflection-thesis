"""适配现有 Generator/VisualGenerator；不加载模型、不启动服务。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from model_grasp_intent_v1.contract import BUDGET_CAPS, require, validate_response
from model_grasp_intent_v1.requests import messages

MAX_RESPONSE_CHARS = 4096


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def parse(response):
    require(response.get('finish_reason') == 'stop', 'incomplete_generation')
    text = response.get('text')
    require(type(text) is str and len(text) <= MAX_RESPONSE_CHARS, 'invalid_response_text')
    value = json.loads(text, object_pairs_hook=unique_object)
    return dict(action=validate_response(value))


def image_paths(records, root):
    require(type(records) is list and 1 <= len(records) <= 2, 'invalid_image_count')
    paths = []
    for row in records:
        require(type(row) is dict and set(row) == {'path', 'sha256'}, 'invalid_image_record')
        path = Path(row['path']).resolve(strict=True)
        require(path.is_relative_to(root) and path.suffix.lower() == '.png', 'invalid_image_path')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], 'image_hash_mismatch')
        paths.append(str(path))
    return paths


class ModelPolicy:
    def __init__(self, generator, *, max_calls, images=None, image_root=None):
        require(type(max_calls) is int and 0 < max_calls <= BUDGET_CAPS['decisions'], 'invalid_call_budget')
        require((images is None) == (image_root is None), 'incomplete_image_registration')
        self.generator, self.maximum = generator, max_calls
        self.images = deepcopy(images)
        self.root = Path(image_root).resolve(strict=True) if images is not None else None
        self.calls, self.generations = 0, 0

    def __call__(self, request):
        require(self.calls < self.maximum, 'model_budget_exhausted')
        self.calls += 1
        prompt = messages(request)
        if self.images is None:
            values = self.generator.prepare(prompt)
        else:
            revision = request['observation']['revision']
            require(revision in self.images, 'image_revision_missing')
            paths = image_paths(self.images[revision], self.root)
            values, _ = self.generator.prepare_images(prompt, paths)
        self.generations += 1
        return parse(self.generator.generate(values))
