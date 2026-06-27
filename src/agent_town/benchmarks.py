from __future__ import annotations

from dataclasses import dataclass
import statistics
import time

from .core import Agent, Location, Simulation, WORLD_HEIGHT, WORLD_WIDTH


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    entity_count: int
    iterations: int
    average_ms: float
    p95_ms: float
    threshold_ms: float
    passed: bool
    bottleneck: str


BENCHMARK_THRESHOLDS_MS = {
    "rule_agents": 8.0,
    "visible_entities_1000": 16.7,
    "visible_entities_5000": 33.0,
}


def percentile(values: list[float], percent: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percent / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def evaluate_threshold(name: str, entity_count: int, p95_ms: float) -> BenchmarkResult:
    threshold = BENCHMARK_THRESHOLDS_MS.get(name)
    if threshold is None and name == "visible_entities":
        threshold = 16.7 if entity_count <= 1000 else 33.0
    if threshold is None:
        threshold = 0.0
    return BenchmarkResult(
        name=name,
        entity_count=entity_count,
        iterations=0,
        average_ms=0.0,
        p95_ms=p95_ms,
        threshold_ms=threshold,
        passed=threshold == 0.0 or p95_ms <= threshold,
        bottleneck=_expected_bottleneck(name, entity_count),
    )


def run_rule_agent_benchmark(entity_count: int, *, iterations: int = 60) -> BenchmarkResult:
    if entity_count <= 0:
        raise ValueError("entity_count must be positive")
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    sim = build_synthetic_simulation(entity_count)
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        sim.step(0.1)
        samples.append((time.perf_counter() - start) * 1000)
    average = statistics.fmean(samples)
    p95 = percentile(samples, 95)
    threshold = evaluate_threshold("rule_agents", entity_count, p95)
    return BenchmarkResult(
        name="rule_agents",
        entity_count=entity_count,
        iterations=iterations,
        average_ms=average,
        p95_ms=p95,
        threshold_ms=threshold.threshold_ms,
        passed=threshold.passed,
        bottleneck=threshold.bottleneck,
    )


def build_synthetic_simulation(entity_count: int) -> Simulation:
    if entity_count <= 0:
        raise ValueError("entity_count must be positive")
    locations = [
        Location("Town Square", 1180, 780, "social", 120),
        Location("North Apartments", 530, 360, "home", 95),
        Location("South Row Homes", 1780, 1280, "home", 95),
        Location("Greenhouse Cafe", 760, 1110, "food", 88),
        Location("Archive Library", 1600, 455, "knowledge", 92),
        Location("Maker Hall", 1880, 800, "work", 96),
        Location("Riverside Park", 420, 1160, "social", 115),
        Location("Clinic Garden", 1260, 1240, "quiet", 82),
    ]
    agents = []
    for index in range(entity_count):
        location = locations[index % len(locations)]
        agents.append(
            Agent(
                id=f"agent-{index}",
                name=f"Agent {index}",
                x=float((index * 37) % WORLD_WIDTH),
                y=float((index * 53) % WORLD_HEIGHT),
                color=(90 + index % 120, 130, 185),
                traits=("curious",),
                destination=location.name,
                home="North Apartments",
                workplace="Maker Hall",
                preferred_places=("Town Square", "Riverside Park"),
                sprite_index=(index % 10) * 54,
                conversation_cooldown=999.0,
            )
        )
    return Simulation(locations, agents, seed=3)


def _expected_bottleneck(name: str, entity_count: int) -> str:
    if name == "rule_agents":
        return "simulation tick cost and social matching"
    if name == "visible_entities" and entity_count >= 5000:
        return "Pygame sprite draw, labels, and scaling"
    return "unknown until measured"
