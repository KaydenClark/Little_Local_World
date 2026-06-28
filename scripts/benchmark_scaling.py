from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_town import colony, engine, governor  # noqa: E402
from agent_town.core import FactionState, Pawn  # noqa: E402


def make_colony(pawn_count: int) -> FactionState:
    state = colony.create_default_colony()
    templates = list(state.pawns.values())
    state.pawns.clear()
    for index in range(pawn_count):
        template = templates[index % len(templates)]
        state.pawns[f"pawn{index:04d}"] = Pawn(
            id=f"pawn{index:04d}",
            name=f"{template.name} {index}",
            skills=dict(template.skills),
            traits=template.traits,
            wants=template.wants,
            needs=dict(template.needs),
            mood=template.mood,
            schedule=template.schedule,
            assignment=None,
            x=2 + (index % max(1, colony.COLONY_WIDTH - 4)),
            y=2 + ((index // max(1, colony.COLONY_WIDTH - 4)) % max(1, colony.COLONY_HEIGHT - 4)),
            state=template.state,
        )
    return state


def benchmark_engine(pawn_count: int, steps: int) -> tuple[float, engine.StepResult]:
    state = make_colony(pawn_count)
    gov = governor.FallbackGovernor()
    last_result = engine.StepResult()
    start = time.perf_counter()
    for _ in range(steps):
        last_result = engine.step_hour(state, gov)
    elapsed = time.perf_counter() - start
    return elapsed / max(1, steps) * 1000, last_result


def benchmark_context(pawn_count: int, repeats: int) -> float:
    state = make_colony(pawn_count)
    start = time.perf_counter()
    for _ in range(repeats):
        governor.build_context(state)
    return (time.perf_counter() - start) / max(1, repeats) * 1000


def benchmark_draw(pawn_count: int, frames: int) -> float | None:
    if frames <= 0:
        return None

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame

        from agent_town.colony_view import (
            Camera,
            governor_status_line,
            load_colony_assets,
            render_colony,
        )

        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((1, 1))
        state = make_colony(pawn_count)
        assets = load_colony_assets()
        font = pygame.font.Font(None, 18)
        surface = pygame.Surface((856, 516))
        camera = Camera()
        status_line = governor_status_line(governor.FallbackGovernor())

        start = time.perf_counter()
        for _ in range(frames):
            render_colony(
                surface,
                state,
                assets,
                font,
                (12, 12),
                status_line=status_line,
                camera=camera,
                selected_pawn_id=next(iter(state.pawns), None),
                show_inspector=True,
            )
        elapsed = time.perf_counter() - start
        pygame.quit()
        return elapsed / frames * 1000
    except Exception as exc:
        print(f"draw_ms=skipped pawn_count={pawn_count} reason={exc}", file=sys.stderr)
        return None


def run(args: argparse.Namespace) -> int:
    print("pawns,engine_ms_per_hour,context_ms,draw_ms,actions_last_hour,buildings_completed")
    for pawn_count in args.pawns:
        engine_ms, result = benchmark_engine(pawn_count, args.steps)
        context_ms = benchmark_context(pawn_count, args.context_repeats)
        draw_ms = benchmark_draw(pawn_count, args.draw_frames)
        draw_value = "" if draw_ms is None else f"{draw_ms:.3f}"
        print(
            f"{pawn_count},{engine_ms:.3f},{context_ms:.3f},{draw_value},"
            f"{len(result.actions_applied)},{len(result.buildings_completed)}"
        )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Local Agent Town colony scaling boundaries.")
    parser.add_argument("--pawns", "--agents", nargs="+", type=int, default=[100, 500, 1000])
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--context-repeats", type=int, default=30)
    parser.add_argument("--draw-frames", type=int, default=20)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
