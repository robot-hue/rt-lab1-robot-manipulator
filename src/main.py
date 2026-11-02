"""Лабораторная работа №1 по СРВ.

Классификация систем реального времени и расчёт требуемого времени реакции.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
    