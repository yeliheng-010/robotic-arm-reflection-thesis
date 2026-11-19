"""冻结教师推理预算实验；不修改旧服务，不加载适配器。"""
from http.server import HTTPServer
import json
from stability.experiment import OUT
from training.refine.runtime import FrozenModel
from training.refine.teacher_service import handler_class


def main():
    output = OUT/'teacher_reasoning'
    output.mkdir(exist_ok=True)
    model = FrozenModel('qwen35', thinking=True)
    model.max_new_tokens = 4096
    with HTTPServer(('127.0.0.1', 18823), handler_class(model, output)) as server:
        print(json.dumps({'ready': True, 'thinking': True, 'max_new_tokens': 4096}), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
