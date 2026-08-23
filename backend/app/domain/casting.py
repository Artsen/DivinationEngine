from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from app.domain.randomness import RandomSource

T = TypeVar("T")


class Orientation(StrEnum):
    UPRIGHT = "upright"
    REVERSED = "reversed"
    NONE = "none"


@dataclass(frozen=True)
class Drawn(Generic[T]):  # noqa: UP046 - conventional syntax is widely supported
    item: T
    orientation: Orientation


def draw_items(  # noqa: UP047 - conventional syntax remains friendlier to type checkers
    items: list[T],
    count: int,
    supports_reversals: bool,
    reversals_enabled: bool,
    randomness: RandomSource,
) -> list[Drawn[T]]:
    if count < 1:
        raise ValueError("count must be at least 1")
    if count > len(items):
        raise ValueError("count cannot exceed the number of items in the collection")
    selected = randomness.sample(items, count)
    results = []
    for item in selected:
        if not supports_reversals:
            orientation = Orientation.NONE
        elif reversals_enabled:
            orientation = Orientation.REVERSED if randomness.bit() else Orientation.UPRIGHT
        else:
            orientation = Orientation.UPRIGHT
        results.append(Drawn(item=item, orientation=orientation))
    return results
