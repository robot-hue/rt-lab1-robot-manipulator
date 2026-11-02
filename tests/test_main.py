"""Тесты для src/main.py."""
from pathlib import Path

import pytest

from main import (
    ARCH_DISTRIBUTED,
    ARCH_MULTI,
    ARCH_SINGLE,
    DEADLINE_ARBITRARY,
    DEADLINE_CONSTRAINED,
    DEADLINE_IMPLICIT,
    SYSTEM_HARD,
    SYSTEM_SOFT,
    Hardness,
    Task,
    classify_architecture,
    classify_system,
    critical_task,
    deadline_type,
    is_feasible,
    load_variant,
    required_reaction_time,
    slack,
    utilization,
    utilization_ok,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def make_task(
    name: str = "T",
    hardness: Hardness = Hardness.HARD,
    c: float = 1,
    d: float = 10,
    t: float = 10,
) -> Task:
    """Короткий конструктор задачи для тестов."""
    return Task(name, hardness, c, d, t)


def test_assignment_example() -> None:
    tasks, config = load_variant(DATA_DIR / "example_industrial.json")

    assert classify_system(tasks) == SYSTEM_HARD
    assert all(is_feasible(task) for task in tasks)

    critical = critical_task(tasks)
    assert critical is not None
    assert critical.name == "Аварийный останов"
    assert slack(critical) == 4

    assert required_reaction_time(tasks) == 5
    assert utilization(tasks) == pytest.approx(0.66)
    assert all(deadline_type(task) == DEADLINE_IMPLICIT for task in tasks)
    assert classify_architecture(config.n_cpu, config.has_network) == ARCH_SINGLE


def test_own_variant() -> None:
    tasks, config = load_variant(DATA_DIR / "variant.json")

    assert [slack(task) for task in tasks] == [3, 8, 32, 280]
    assert classify_system(tasks) == SYSTEM_HARD

    critical = critical_task(tasks)
    assert critical is not None
    assert critical.name == "Управление приводами"

    assert required_reaction_time(tasks) == 4
    assert utilization(tasks) == pytest.approx(0.64)
    assert classify_architecture(config.n_cpu, config.has_network) == ARCH_SINGLE


@pytest.mark.parametrize(
    ("d", "t", "expected"),
    [
        (10, 10, DEADLINE_IMPLICIT),
        (4, 5, DEADLINE_CONSTRAINED),
        (300, 250, DEADLINE_ARBITRARY),
    ],
)
def test_deadline_type(d: float, t: float, expected: str) -> None:
    assert deadline_type(make_task(d=d, t=t)) == expected


def test_infeasible_task() -> None:
    task = make_task(c=12, d=10, t=20)

    assert slack(task) == -2
    assert not is_feasible(task)


def test_no_hard_tasks() -> None:
    tasks = [
        make_task("A", Hardness.SOFT, c=8, d=100, t=100),
        make_task("B", Hardness.FIRM, c=5, d=50, t=50),
    ]

    assert classify_system(tasks) == SYSTEM_SOFT
    assert critical_task(tasks) is None
    assert required_reaction_time(tasks) == 50


def test_required_reaction_time_empty_list() -> None:
    with pytest.raises(ValueError):
        required_reaction_time([])


def test_utilization_overload() -> None:
    tasks = [make_task(c=6, d=10, t=10), make_task(c=5, d=10, t=10)]
    u = utilization(tasks)

    assert u == pytest.approx(1.1)
    assert not utilization_ok(u)


@pytest.mark.parametrize("text", ["жёсткое", "жесткое", " ЖЁСТКОЕ "])
def test_hardness_parse_normalizes(text: str) -> None:
    assert Hardness.parse(text) is Hardness.HARD


def test_hardness_parse_unknown() -> None:
    with pytest.raises(ValueError):
        Hardness.parse("жестокое")


@pytest.mark.parametrize(
    ("n_cpu", "has_network", "expected"),
    [
        (1, False, ARCH_SINGLE),
        (4, False, ARCH_MULTI),
        (1, True, ARCH_DISTRIBUTED),
    ],
)
def test_classify_architecture(n_cpu: int, has_network: bool, expected: str) -> None:
    assert classify_architecture(n_cpu, has_network) == expected


def test_negative_deadline_rejected() -> None:
    with pytest.raises(ValueError):
        make_task(d=-10)