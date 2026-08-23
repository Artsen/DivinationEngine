import secrets
from collections.abc import MutableSequence, Sequence
from typing import Protocol, TypeVar

T = TypeVar("T")


class RandomSource(Protocol):
    def sample(self, population: Sequence[T], count: int) -> list[T]: ...

    def bit(self) -> int: ...

    def randbelow(self, upper_bound: int) -> int: ...


class SecureRandomSource:
    """Operating-system backed randomness for real casts."""

    def sample(self, population: Sequence[T], count: int) -> list[T]:
        pool: MutableSequence[T] = list(population)
        chosen: list[T] = []
        for _ in range(count):
            chosen.append(pool.pop(secrets.randbelow(len(pool))))
        return chosen

    def bit(self) -> int:
        return secrets.randbits(1)

    def randbelow(self, upper_bound: int) -> int:
        return secrets.randbelow(upper_bound)
