from app.domain.casting import Orientation

_APPLICABLE_TYPES: dict[Orientation, frozenset[str]] = {
    Orientation.UPRIGHT: frozenset(
        {"upright", "divinatory", "symbolism", "description", "commentary"}
    ),
    Orientation.REVERSED: frozenset({"reversed", "symbolism", "description", "commentary"}),
    Orientation.NONE: frozenset({"divinatory", "symbolism", "description", "commentary"}),
}


def interpretation_is_applicable(orientation: str, interpretation_type: str) -> bool:
    """Apply only the documented orientation rule; unknown types remain available, not applied."""
    try:
        normalized_orientation = Orientation(orientation)
    except ValueError:
        return False
    return interpretation_type in _APPLICABLE_TYPES[normalized_orientation]
