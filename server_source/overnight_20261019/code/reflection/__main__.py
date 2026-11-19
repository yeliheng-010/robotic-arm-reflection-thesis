import argparse
import os
from pathlib import Path
import sys


def bootstrap():
    root = Path(__file__).resolve().parents[1]
    for directory in (root, root / "manipulator_grasp", root / "graspnet-baseline/models",
                      root / "graspnet-baseline/dataset", root / "graspnet-baseline/utils"):
        sys.path.insert(0, str(directory))
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/grasp-reflection-matplotlib")
    if not os.environ.get("DISPLAY"):
        os.environ.setdefault("MUJOCO_GL", "egl")


def add_options(parser):
    parser.add_argument("--reflector", choices=("rule", "llm"), default="rule")
    parser.add_argument("--perception", choices=("simulation", "vlm"), default="simulation")
    parser.add_argument("--segmentation", choices=("simulation", "sam"), default="simulation")
    parser.add_argument("--grasp-backend", choices=("geometric", "graspnet", "hybrid"), default="geometric")
    parser.add_argument("--visual-verify", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=3)
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--viewer", action="store_true")
    display.add_argument("--headless", action="store_true")
    parser.add_argument("--task-parser", choices=("auto", "rule", "llm"), default="auto")


def build_engine(args, memory=None):
    from .engine import FeedbackEngine
    from .reflector import LLMReflector, RuleReflector
    if not 1 <= args.max_attempts <= 10:
        raise ValueError("max-attempts must be in [1, 10]")
    client = None
    if args.reflector == "llm" or args.perception == "vlm" or args.visual_verify or args.task_parser == "llm":
        from .llm import LLMClient
        client = LLMClient()
    reflector = LLMReflector(client) if args.reflector == "llm" else RuleReflector()
    engine = FeedbackEngine(reflector=reflector, memory=memory, client=client,
                           perception=args.perception, segmentation=args.segmentation,
                           grasp_backend=args.grasp_backend, headless=not args.viewer, max_attempts=args.max_attempts,
                           visual_verify=args.visual_verify, task_parser=args.task_parser,
                           scene_jitter=getattr(args, "scene_jitter", 0.0))
    return engine


def main():
    bootstrap()
    from .engine import METHODS
    from .fault_injection import FAULTS
    from .memory import ExperienceMemory
    parser = argparse.ArgumentParser(description="UR5e error-feedback and reflection experiment")
    add_options(parser)
    parser.add_argument("--method", choices=METHODS, default="reflection_memory")
    parser.add_argument("--fault", choices=FAULTS, default="collision")
    parser.add_argument("--source", choices=("RedBlock", "GreenCylinder", "PurpleCapsule", "OrangeSphere"))
    parser.add_argument("--destination", choices=("BlueBin", "RedBin", "SortingTray"))
    parser.add_argument("--instruction")
    parser.add_argument("--interactive", action="store_true", help="Read successive tasks from the terminal")
    parser.add_argument("--context", default="default")
    parser.add_argument("--output", default="logs/reflection/demo")
    parser.add_argument("--memory", default="logs/reflection/experiences.sqlite3")
    args = parser.parse_args()
    if args.interactive and not args.headless:
        args.viewer = True
    if args.viewer and not os.environ.get("DISPLAY"):
        parser.error("没有图形显示服务；请使用 --headless 运行无头模式")
    if args.interactive and (args.source is not None or args.destination is not None):
        parser.error("--interactive uses language targets; omit --source and --destination")
    memory = ExperienceMemory(args.memory)
    engine = None
    try:
        engine = build_engine(args, memory)
        instruction = args.instruction
        task_number = 0
        while True:
            if args.viewer:
                engine.prepare_scene(args.fault)
            if args.interactive and instruction is None:
                try:
                    instruction = input("请输入任务（输入 exit 退出）：").strip()
                except EOFError:
                    break
                if instruction.casefold() in {"exit", "quit", "退出"}:
                    break
                if not instruction:
                    instruction = None
                    continue
            directory = Path(args.output)
            if args.interactive:
                task_number += 1
                directory /= f"task_{task_number:03d}"
                while directory.exists():
                    task_number += 1
                    directory = Path(args.output) / f"task_{task_number:03d}"
            try:
                result = engine.run(source=args.source, destination=args.destination,
                    method=args.method, fault=args.fault, output=directory, instruction=instruction, context=args.context)
            except (ValueError, RuntimeError) as exc:
                if not args.interactive:
                    parser.error(str(exc))
                print(f"任务未完成：{exc}", flush=True)
            else:
                print(f"Result: success={result['success']} attempts={result['attempts']} memory_hit={result['memory_hit']}")
                print(str(directory.resolve() / "result.json"))
            if not args.interactive:
                break
            instruction = None
    except KeyboardInterrupt:
        print("\n已停止运行")
    finally:
        memory.close()
        if engine is not None:
            engine.close()
        if engine is not None and engine.client is not None:
            engine.client.close()


if __name__ == "__main__":
    main()
