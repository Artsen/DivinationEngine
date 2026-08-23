import pytest

from app.domain.casting import Orientation, draw_items
from app.domain.iching import CoinThrow, cast_iching, derive_iching
from app.domain.knowledge import interpretation_is_applicable
from tests.conftest import FakeRandom


def test_draw_count_uniqueness_and_determinism() -> None:
    results = draw_items(["a", "b", "c"], 3, True, True, FakeRandom([0, 1, 0]))
    assert len(results) == 3
    assert len({row.item for row in results}) == 3
    assert [row.orientation for row in results] == [
        Orientation.UPRIGHT,
        Orientation.REVERSED,
        Orientation.UPRIGHT,
    ]


def test_draw_validation_and_no_reversals() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        draw_items(["a"], 2, True, True, FakeRandom([1]))
    with pytest.raises(ValueError, match="at least"):
        draw_items(["a"], 0, True, True, FakeRandom([1]))
    result = draw_items(["a"], 1, False, True, FakeRandom([1]))
    assert result[0].orientation is Orientation.NONE


def test_iching_math_and_bottom_to_top_order() -> None:
    # Lines: 6, 9, 7, 8, 6, 9. Each consecutive triple is one line.
    bits = [0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1]
    result = cast_iching(FakeRandom(bits))
    assert [throw.line_number for throw in result.throws] == [1, 2, 3, 4, 5, 6]
    assert [throw.value for throw in result.throws] == [6, 9, 8, 7, 6, 9]
    assert all(len(throw.coins) == 3 for throw in result.throws)
    assert set(throw.value for throw in result.throws) <= {6, 7, 8, 9}
    assert result.primary_pattern == "010101"
    assert result.changing_lines == (1, 2, 5, 6)
    assert result.relating_pattern == "100110"


def test_derive_iching_accepts_six_and_applies_changes_bottom_to_top() -> None:
    throws = (
        CoinThrow(1, (2, 2, 2), 6),
        CoinThrow(2, (2, 2, 3), 7),
        CoinThrow(3, (2, 3, 3), 8),
        CoinThrow(4, (3, 3, 3), 9),
        CoinThrow(5, (2, 2, 3), 7),
        CoinThrow(6, (2, 3, 3), 8),
    )
    result = derive_iching(throws)
    assert result.primary_pattern == "010110"
    assert result.relating_pattern == "110010"
    assert result.changing_lines == (1, 4)


@pytest.mark.parametrize("count", [5, 7])
def test_derive_iching_rejects_wrong_throw_count(count: int) -> None:
    throws = tuple(CoinThrow(number, (2, 2, 2), 6) for number in range(1, count + 1))
    with pytest.raises(ValueError, match="exactly six"):
        derive_iching(throws)


def test_derive_iching_rejects_invalid_values_coins_and_order() -> None:
    valid = [CoinThrow(number, (2, 2, 2), 6) for number in range(1, 7)]
    invalid_value = [*valid]
    invalid_value[2] = CoinThrow(3, (2, 2, 2), 7)
    with pytest.raises(ValueError, match="valid coins"):
        derive_iching(tuple(invalid_value))
    invalid_coin = [*valid]
    invalid_coin[2] = CoinThrow(3, (1, 2, 3), 6)
    with pytest.raises(ValueError, match="valid coins"):
        derive_iching(tuple(invalid_coin))
    wrong_order = [*valid]
    wrong_order[0] = CoinThrow(6, (2, 2, 2), 6)
    with pytest.raises(ValueError, match="bottom-to-top"):
        derive_iching(tuple(wrong_order))


def test_orientation_relevance_rule_is_explicit_and_closed() -> None:
    assert interpretation_is_applicable("upright", "upright")
    assert interpretation_is_applicable("upright", "divinatory")
    assert not interpretation_is_applicable("upright", "reversed")
    assert interpretation_is_applicable("reversed", "reversed")
    assert not interpretation_is_applicable("reversed", "upright")
    assert not interpretation_is_applicable("reversed", "future-new-category")
