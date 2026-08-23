import pytest

from app.domain.casting import Orientation, draw_items
from app.domain.iching import cast_iching
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
