from dataclasses import dataclass

from app.domain.randomness import RandomSource


@dataclass(frozen=True)
class CoinThrow:
    line_number: int
    coins: tuple[int, int, int]
    value: int


@dataclass(frozen=True)
class IChingResult:
    throws: tuple[CoinThrow, ...]
    primary_pattern: str
    changing_lines: tuple[int, ...]
    relating_pattern: str


def cast_iching(randomness: RandomSource) -> IChingResult:
    throws: list[CoinThrow] = []
    for line_number in range(1, 7):  # bottom to top
        coins = tuple(3 if randomness.bit() else 2 for _ in range(3))
        value = sum(coins)
        throws.append(CoinThrow(line_number, coins, value))  # type: ignore[arg-type]
    return derive_iching(tuple(throws))


def derive_iching(throws: tuple[CoinThrow, ...]) -> IChingResult:
    if len(throws) != 6 or any(t.value not in {6, 7, 8, 9} for t in throws):
        raise ValueError("an I Ching cast requires six valid line values")
    # Pattern strings are bottom-line first, matching persisted line ordering.
    primary = "".join("1" if t.value in {7, 9} else "0" for t in throws)
    relating = "".join("1" if t.value in {6, 7} else "0" for t in throws)
    changing = tuple(t.line_number for t in throws if t.value in {6, 9})
    return IChingResult(throws, primary, changing, relating)
