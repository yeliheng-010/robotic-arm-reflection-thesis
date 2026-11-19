"""独立9B教师：固定权重版本、量化与解码，复用原解析接口。"""
from http.server import HTTPServer
import json
from unittest.mock import patch
from stability.experiment import OUT
from training.refine.runtime import FrozenModel, MODEL_PATHS
from training.refine.teacher_service import handler_class

REVISION = 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'
AUDIT = OUT/'teacher9/requests.jsonl'


class StrongTeacher(FrozenModel):
    def __init__(self):
        ready = json.loads((OUT/'model9-ready.json').read_text())
        assert ready['manifest']['revision'] == REVISION
        assert len(ready['verified_files']) == len(ready['manifest']['files'])
        with patch.dict(MODEL_PATHS, qwen35=str(OUT/'models/Qwen3.5-9B')):
            super().__init__('qwen35', thinking=False)
        self.max_new_tokens = 512

    def identity(self):
        return dict(model=self.path, architecture=self.architecture, adapter=None, frozen=True,
            thinking=False, max_new_tokens=self.max_new_tokens, revision=REVISION,
            decoding={'do_sample': False}, audit_log=str(AUDIT))

    def generate(self, messages):
        return dict(super().generate(messages), **self.identity())


def main():
    AUDIT.parent.mkdir(exist_ok=True)
    model = StrongTeacher()
    parent = handler_class(model, AUDIT.parent)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18823), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
