from dataclasses import dataclass
from typing import Literal

from app.domain.randomness import RandomSource


@dataclass(frozen=True)
class CoinThrow:
    line_number: int
    coins: tuple[int, int, int]
    value: int


@dataclass(frozen=True)
class YarrowManipulation:
    operation: int
    starting_stalks: int
    left_pile: int
    right_pile: int
    removed_from_right: int
    left_remainder: int
    right_remainder: int
    removed_total: int
    remaining_stalks: int


@dataclass(frozen=True)
class YarrowThrow:
    line_number: int
    manipulations: tuple[YarrowManipulation, ...]
    value: int


@dataclass(frozen=True)
class IChingResult:
    throws: tuple[CoinThrow | YarrowThrow, ...]
    primary_pattern: str
    changing_lines: tuple[int, ...]
    relating_pattern: str


def cast_iching(randomness: RandomSource) -> IChingResult:
    """Backward-compatible alias for the traditional three-coin cast."""
    return cast_three_coin(randomness)


def cast_three_coin(randomness: RandomSource) -> IChingResult:
    throws: list[CoinThrow] = []
    for line_number in range(1, 7):  # bottom to top
        coins = tuple(3 if randomness.bit() else 2 for _ in range(3))
        value = sum(coins)
        throws.append(CoinThrow(line_number, coins, value))  # type: ignore[arg-type]
    return derive_iching(tuple(throws))


def cast_yarrow_stalk(randomness: RandomSource) -> IChingResult:
    """Perform the 49-working-stalk reconstruction: 3 manipulations x 6 lines."""
    throws: list[YarrowThrow] = []
    for line_number in range(1, 7):
        stalks = 49
        manipulations: list[YarrowManipulation] = []
        for operation in range(1, 4):
            # A hand split is modeled by four equiprobable remainder classes. This
            # preserves the received manipulation and yields its reconstructed ratios;
            # the line value is never selected directly.
            remainder_class = randomness.randbelow(4)
            valid_splits = [
                candidate_left
                for candidate_left in range(1, stalks)
                if candidate_left % 4 == remainder_class
            ]
            left = valid_splits[randomness.randbelow(len(valid_splits))]
            right = stalks - left
            right_after_one = right - 1
            left_remainder = left % 4 or 4
            right_remainder = right_after_one % 4 or 4
            removed = 1 + left_remainder + right_remainder
            remaining = stalks - removed
            if remaining % 4:
                raise AssertionError("yarrow manipulation did not leave a multiple of four")
            manipulations.append(
                YarrowManipulation(
                    operation=operation,
                    starting_stalks=stalks,
                    left_pile=left,
                    right_pile=right,
                    removed_from_right=1,
                    left_remainder=left_remainder,
                    right_remainder=right_remainder,
                    removed_total=removed,
                    remaining_stalks=remaining,
                )
            )
            stalks = remaining
        throws.append(YarrowThrow(line_number, tuple(manipulations), stalks // 4))
    return derive_iching(tuple(throws))


def cast_by_method(
    randomness: RandomSource, method: Literal["three-coin", "yarrow-stalk"]
) -> IChingResult:
    return cast_three_coin(randomness) if method == "three-coin" else cast_yarrow_stalk(randomness)


def derive_iching(throws: tuple[CoinThrow | YarrowThrow, ...]) -> IChingResult:
    if len(throws) != 6:
        raise ValueError("an I Ching cast requires exactly six throws")
    if [throw.line_number for throw in throws] != list(range(1, 7)):
        raise ValueError("I Ching lines must be ordered bottom-to-top from 1 through 6")
    for throw in throws:
        if throw.value not in {6, 7, 8, 9}:
            raise ValueError("each throw requires a line value from 6 through 9")
        if isinstance(throw, CoinThrow) and (
            len(throw.coins) != 3
            or any(coin not in {2, 3} for coin in throw.coins)
            or throw.value != sum(throw.coins)
        ):
            raise ValueError("each coin throw requires three valid coins and their summed value")
        if isinstance(throw, YarrowThrow) and len(throw.manipulations) != 3:
            raise ValueError("each yarrow line requires exactly three manipulations")
    # Pattern strings are bottom-line first, matching persisted line ordering.
    primary = "".join("1" if t.value in {7, 9} else "0" for t in throws)
    relating = "".join("1" if t.value in {6, 7} else "0" for t in throws)
    changing = tuple(t.line_number for t in throws if t.value in {6, 9})
    return IChingResult(throws, primary, changing, relating)
