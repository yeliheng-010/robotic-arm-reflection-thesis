from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="未来具身智能家庭仿真演示")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-realtime", action="store_true", help="关闭演示节奏等待，用于测试")
    parser.add_argument("--web", action="store_true", help="使用可选的网页调试控制台")
    parser.add_argument("--run-command", help="不启动网页，直接执行一条受控中文指令")
    parser.add_argument(
        "--memory",
        default=str(Path("logs") / "future_ai_memory.sqlite3"),
        help="长期记忆数据库路径",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/future-embodied-matplotlib")

    # The native viewer must select the desktop OpenGL backend itself.  Keep
    # headless EGL isolated to the web/CLI paths, which own off-screen renders.
    if not args.web and not args.run_command:
        from .native_viewer import NativeViewerApp

        return NativeViewerApp(
            memory_path=args.memory,
            realtime=not args.no_realtime,
        ).run()

    os.environ.setdefault("MUJOCO_GL", "egl")

    from .engine import DemoEngine
    from .simulator import MobileHomeSimulator

    simulator = MobileHomeSimulator(realtime=not args.no_realtime)
    engine = DemoEngine(simulator=simulator, memory_path=args.memory)
    if args.run_command:
        try:
            engine.start(args.run_command, background=False)
            state = engine.state()
            print(
                json.dumps(
                    {
                        "status": state["status"],
                        "completed": state["completed"],
                        "revision": state["revision"],
                        "world": {
                            key: value["zone"]
                            for key, value in state["world"]["entities"].items()
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if state["status"] == "completed" else 1
        finally:
            engine.close()

    if args.web:
        from .dashboard import DashboardServer

        server = DashboardServer(engine, args.host, args.port)
        print("Future AI Emulator 网页调试器（离线、无大模型 API）已启动：")
        print(server.url)
        print("按 Ctrl+C 停止。")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            engine.close()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
