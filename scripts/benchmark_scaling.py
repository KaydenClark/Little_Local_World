from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_town.core import Agent, Simulation, WORLD_HEIGHT, WORLD_WIDTH, create_default_simulation
from agent_town.llm import build_decision_context
from agent_town.persistence import SQLiteSimulationStore, simulation_to_snapshot


def make_simulation(agent_count: int, *, seed: int = 42) -> Simulation:
    base = create_default_simulation()
    template_agents = list(base.agents.values())
    locations = list(base.locations.values())
    rng = random.Random(seed)
    agents: list[Agent] = []
    for index in range(agent_count):
        template = template_agents[index % len(template_agents)]
        destination = locations[index % len(locations)]
        agents.append(
            Agent(
                id=f"{template.id}_{index}",
                name=f"{template.name} {index}",
                x=rng.uniform(0, WORLD_WIDTH),
                y=rng.uniform(0, WORLD_HEIGHT),
                color=template.color,
                traits=template.traits,
                energy=template.energy,
                hunger=template.hunger,
                social=template.social,
                curiosity=template.curiosity,
                destination=destination.name,
                home=template.home,
                workplace=template.workplace,
                preferred_places=template.preferred_places,
                sprite_index=template.sprite_index,
            )
        )
    return Simulation(locations, agents, seed=seed)


def benchmark_core(agent_count: int, steps: int, dt: float) -> tuple[float, dict[str, int], Simulation]:
    sim = make_simulation(agent_count)
    start = time.perf_counter()
    for _ in range(steps):
        sim.step(dt)
    elapsed = time.perf_counter() - start
    return elapsed / steps * 1000, dict(sim.last_step_metrics), sim


def benchmark_context(sim: Simulation, repeats: int) -> float:
    agent_id = next(iter(sim.agents))
    start = time.perf_counter()
    for _ in range(repeats):
        build_decision_context(sim, agent_id)
    return (time.perf_counter() - start) / repeats * 1000


def benchmark_persistence(sim: Simulation) -> tuple[float, float, int, int, int]:
    payload = simulation_to_snapshot(sim)
    snapshot_bytes = len(str(payload).encode("utf-8"))
    memory_entries = sum(len(agent.memories) for agent in sim.agents.values())
    with tempfile.TemporaryDirectory() as temp_dir:
        store = SQLiteSimulationStore(Path(temp_dir) / "town.sqlite3")
        start = time.perf_counter()
        store.save_snapshot(sim)
        save_ms = (time.perf_counter() - start) * 1000
        db_bytes = (Path(temp_dir) / "town.sqlite3").stat().st_size
        start = time.perf_counter()
        store.load_snapshot()
        load_ms = (time.perf_counter() - start) * 1000
    return save_ms, load_ms, snapshot_bytes, db_bytes, memory_entries


def benchmark_draw(agent_count: int, frames: int) -> float | None:
    if frames <= 0:
        return None

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        from agent_town.app import App

        app = App(make_simulation(agent_count), smoke_test=True)
        start = time.perf_counter()
        for _ in range(frames):
            app._draw()
        elapsed = time.perf_counter() - start
        app.llm_scheduler.shutdown(wait=False)

        import pygame

        pygame.quit()
        return elapsed / frames * 1000
    except Exception as exc:
        print(f"draw_ms=skipped agent_count={agent_count} reason={exc}", file=sys.stderr)
        return None


def run(args: argparse.Namespace) -> int:
    print(
        "agents,core_ms_per_step,context_ms,draw_ms,save_ms,load_ms,"
        "snapshot_bytes,sqlite_bytes,memory_entries,events,"
        "social_candidate_visits,social_distance_checks,conversations_started"
    )
    for agent_count in args.agents:
        core_ms, metrics, sim = benchmark_core(agent_count, args.steps, args.dt)
        context_ms = benchmark_context(sim, args.context_repeats)
        save_ms, load_ms, snapshot_bytes, db_bytes, memory_entries = benchmark_persistence(sim)
        draw_ms = benchmark_draw(agent_count, args.draw_frames)
        draw_value = "" if draw_ms is None else f"{draw_ms:.3f}"
        print(
            f"{agent_count},{core_ms:.3f},{context_ms:.3f},{draw_value},"
            f"{save_ms:.3f},{load_ms:.3f},{snapshot_bytes},{db_bytes},"
            f"{memory_entries},{len(sim.events)},"
            f"{metrics['social_candidate_visits']},"
            f"{metrics['social_distance_checks']},"
            f"{metrics['conversations_started']}"
        )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Local Agent Town scaling boundaries.")
    parser.add_argument("--agents", nargs="+", type=int, default=[100, 500, 1000])
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--context-repeats", type=int, default=30)
    parser.add_argument("--draw-frames", type=int, default=20)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
