"""独立记录思考预算控制与真实生成答案的教师服务。"""
from http.server import HTTPServer
import json
from stability.budget_forcing import BudgetForcedTeacher, OUTPUT
from training.refine.teacher_service import handler_class


def main():
    OUTPUT.mkdir(exist_ok=True)
    model = BudgetForcedTeacher()
    parent = handler_class(model, OUTPUT)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18823), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

