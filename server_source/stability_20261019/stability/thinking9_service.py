"""独立9B思考诊断；固定权重、输入seed与2048输出token预算。"""
from http.server import HTTPServer
import json
from unittest.mock import patch
from stability.experiment import OUT
from stability.sampling_runtime import SamplingModel
from stability.teacher9_service import REVISION
from training.refine.runtime import MODEL_PATHS
from training.refine.teacher_service import handler_class

OUTPUT = OUT/'teacher9_thinking'


class ThinkingTeacher(SamplingModel):
    def __init__(self):
        ready = json.loads((OUT/'model9-ready.json').read_text())
        assert ready['manifest']['revision'] == REVISION
        assert len(ready['verified_files']) == len(ready['manifest']['files'])
        with patch.dict(MODEL_PATHS, qwen35=str(OUT/'models/Qwen3.5-9B')):
            super().__init__()
        self.max_new_tokens = 2048

    def identity(self):
        return dict(super().identity(), revision=REVISION,
                    audit_log=str(OUTPUT/'requests.jsonl'))


def main():
    OUTPUT.mkdir(exist_ok=True)
    model = ThinkingTeacher()
    parent = handler_class(model, OUTPUT)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18823), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

