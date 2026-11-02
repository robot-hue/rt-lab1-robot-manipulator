"""Лабораторная работа №1 по СРВ.

Классификация систем реального времени и расчёт требуемого времени реакции.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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