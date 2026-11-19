"""9B思考的独立4096-token预算诊断，保留2048版本日志。"""
from http.server import HTTPServer
import json
from stability.experiment import OUT
from stability.thinking9_service import ThinkingTeacher
from training.refine.teacher_service import handler_class

OUTPUT = OUT/'teacher9_thinking4096'


class BudgetTeacher(ThinkingTeacher):
    def __init__(self):
        super().__init__()
        self.max_new_tokens = 4096

    def identity(self):
        return dict(super().identity(), audit_log=str(OUTPUT/'requests.jsonl'))


def main():
    OUTPUT.mkdir(exist_ok=True)
    model = BudgetTeacher()
    parent = handler_class(model, OUTPUT)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18823), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

