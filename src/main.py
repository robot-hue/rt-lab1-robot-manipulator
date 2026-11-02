"""Лабораторная работа №1 по СРВ.

Классификация систем реального времени и расчёт требуемого времени реакции.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Файл с данными по умолчанию: <корень проекта>/data/variant.json
DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "data" / "variant.json"

# Типы дедлайна
DEADLINE_IMPLICIT = "неявный (D = T)"
DEADLINE_CONSTRAINED = "ограниченный (D ≤ T)"
DEADLINE_ARBITRARY = "произвольный (D > T)"

# Классы системы
SYSTEM_HARD = "жёсткого реального времени"
SYSTEM_SOFT = "мягкого реального времени"

# Предел загрузки процессора (необходимое условие U <= 1)
UTILIZATION_LIMIT = 1.0

# Архитектуры
ARCH_SINGLE = "однопроцессорная"
ARCH_MULTI = "многопроцессорная"
ARCH_DISTRIBUTED = "распределённая"

def _normalize(text: str) -> str:
    """Привести строку к единому виду: без пробелов по краям, строчные, ё -> е."""
    return text.strip().lower().replace("ё", "е")


class Hardness(Enum):
    """Класс жёсткости задачи."""

    HARD = "жёсткое"
    FIRM = "твёрдое"
    SOFT = "мягкое"

    @classmethod
    def parse(cls, text: str) -> Hardness:
        """Преобразовать строку из файла в элемент Hardness."""
        key = _normalize(text)
        for member in cls:
            if _normalize(member.value) == key:
                return member
        raise ValueError(f"Неизвестный класс жёсткости: {text!r}")


@dataclass(frozen=True)
class Task:
    """Периодическая задача: C, D, T задаются в миллисекундах."""

    name: str
    hardness: Hardness
    C: float
    D: float
    T: float

    def __post_init__(self) -> None:
        if self.C <= 0 or self.D <= 0 or self.T <= 0:
            raise ValueError(
                f"Задача {self.name!r}: C, D и T должны быть больше нуля "
                f"(C={self.C}, D={self.D}, T={self.T})"
            )


@dataclass(frozen=True)
class SystemConfig:
    """Конфигурация системы: число процессоров и наличие сети."""

    n_cpu: int
    has_network: bool

    def __post_init__(self) -> None:
        if self.n_cpu < 1:
            raise ValueError(f"Число процессоров должно быть >= 1, получено {self.n_cpu}")


def _as_bool(value: object) -> bool:
    """Преобразовать значение из файла в bool (принимает true/false и строки)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        if key == "true":
            return True
        if key == "false":
            return False
    raise ValueError(f"Ожидалось true или false, получено {value!r}")


def load_variant(path: Path) -> tuple[list[Task], SystemConfig]:
    """Прочитать JSON-файл и вернуть список задач и конфигурацию системы."""
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    try:
        system_raw = data["system"]
        config = SystemConfig(
            n_cpu=int(system_raw["n_cpu"]),
            has_network=_as_bool(system_raw["has_network"]),
        )
        tasks_raw = data["tasks"]
    except KeyError as error:
        raise ValueError(f"В файле {path} нет обязательного поля {error}") from error

    if not tasks_raw:
        raise ValueError("Список задач пуст")

    tasks: list[Task] = []
    for number, item in enumerate(tasks_raw, start=1):
        try:
            tasks.append(
                Task(
                    name=str(item["name"]),
                    hardness=Hardness.parse(item["hardness"]),
                    C=float(item["C"]),
                    D=float(item["D"]),
                    T=float(item["T"]),
                )
            )
        except KeyError as error:
            raise ValueError(f"Задача №{number}: нет поля {error}") from error
        except ValueError as error:
            raise ValueError(f"Задача №{number}: {error}") from error

    return tasks, config


def slack(task: Task) -> float:
    """Запас времени L = D - C."""
    return task.D - task.C


def is_feasible(task: Task) -> bool:
    """Задача выполнима, если запас неотрицателен: L >= 0."""
    return slack(task) >= 0


def deadline_type(task: Task) -> str:
    """Определить тип дедлайна по соотношению D и T."""
    if math.isclose(task.D, task.T):
        return DEADLINE_IMPLICIT
    if task.D < task.T:
        return DEADLINE_CONSTRAINED
    return DEADLINE_ARBITRARY


def _hard_tasks(tasks: list[Task]) -> list[Task]:
    """Выбрать только задачи жёсткого класса."""
    return [task for task in tasks if task.hardness is Hardness.HARD]


def classify_system(tasks: list[Task]) -> str:
    """Система жёсткого РВ, если есть хотя бы одна жёсткая задача, иначе мягкого."""
    return SYSTEM_HARD if _hard_tasks(tasks) else SYSTEM_SOFT


def critical_task(tasks: list[Task]) -> Task | None:
    """Критическая задача: жёсткая задача с минимальным запасом L."""
    hard = _hard_tasks(tasks)
    if not hard:
        return None
    return min(hard, key=slack)


def required_reaction_time(tasks: list[Task]) -> float:
    """R_треб = min(D) по жёстким задачам, а если их нет, по всем задачам."""
    if not tasks:
        raise ValueError("Список задач пуст")
    pool = _hard_tasks(tasks) or tasks
    return min(task.D for task in pool)


def utilization(tasks: list[Task]) -> float:
    """Суммарная загрузка процессора U = сумма C_i / T_i."""
    return sum(task.C / task.T for task in tasks)


def utilization_ok(u: float) -> bool:
    """Необходимое условие загрузки: U <= 1."""
    return u <= UTILIZATION_LIMIT


def classify_architecture(n_cpu: int, has_network: bool) -> str:
    """Определить архитектуру: сеть -> распределённая, иначе по числу процессоров."""
    if n_cpu < 1:
        raise ValueError(f"Число процессоров должно быть >= 1, получено {n_cpu}")
    if has_network:
        return ARCH_DISTRIBUTED
    if n_cpu == 1:
        return ARCH_SINGLE
    return ARCH_MULTI


def fmt(value: float) -> str:
    """Число без лишнего «.0»: 4.0 -> '4', 0.5 -> '0.5'."""
    return f"{value:g}"


def print_table(tasks: list[Task]) -> None:
    """Вывести таблицу задач с автоматической шириной колонок."""
    header = ["Задача", "Класс", "C", "D", "T", "L", "Выполнимо", "Тип дедлайна"]
    rows = [
        [
            task.name,
            task.hardness.value,
            fmt(task.C),
            fmt(task.D),
            fmt(task.T),
            fmt(slack(task)),
            "да" if is_feasible(task) else "нет",
            deadline_type(task),
        ]
        for task in tasks
    ]
    widths = [max(len(cell) for cell in column) for column in zip(header, *rows)]

    def line(cells: list[str]) -> str:
        return " | ".join(cell.ljust(width) for cell, width in zip(cells, widths))

    print(line(header))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(line(row))


def main() -> int:
    """Точка входа: прочитать файл, вывести таблицу. Возвращает код выхода."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Классификация систем реального времени и расчёт времени реакции."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="путь к JSON-файлу с данными (по умолчанию data/variant.json)",
    )
    args = parser.parse_args()

    try:
        tasks, config = load_variant(args.input)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print_table(tasks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
    