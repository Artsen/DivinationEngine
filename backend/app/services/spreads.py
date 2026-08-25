from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models

BUILTIN_NAMESPACE = uuid.UUID("08adfe3c-ea2d-4e83-b17d-172ee8c75a76")
BUILTIN_CLASSIFICATION = "modern-editorial-layout"
BUILTIN_SOURCE = "DivinationEngine project-provided layout"


@dataclass(frozen=True)
class BuiltinPosition:
    key: str
    label: str
    description: str
    x: float
    y: float


@dataclass(frozen=True)
class BuiltinSpread:
    key: str
    name: str
    description: str
    system_types: tuple[str, ...]
    positions: tuple[BuiltinPosition, ...]


BUILTIN_SPREADS = (
    BuiltinSpread(
        "single-card",
        "Single Card",
        "One card placed at the focus of the reading.",
        ("tarot",),
        (
            BuiltinPosition(
                "focus",
                "Focus",
                "The central theme, influence, or focus of the question.",
                0.5,
                0.5,
            ),
        ),
    ),
    BuiltinSpread(
        "single-rune",
        "Single Rune",
        "One rune placed at the focus of the reading.",
        ("runes",),
        (
            BuiltinPosition(
                "focus",
                "Focus",
                "The central theme, influence, or focus of the question.",
                0.5,
                0.5,
            ),
        ),
    ),
    BuiltinSpread(
        "past-present-future",
        "Past / Present / Future",
        "A modern three-position reading layout organized by time.",
        ("tarot", "runes"),
        (
            BuiltinPosition(
                "past",
                "Past",
                "Background and prior influences relevant to the question.",
                0.15,
                0.5,
            ),
            BuiltinPosition(
                "present",
                "Present",
                "Current conditions and influences surrounding the question.",
                0.5,
                0.5,
            ),
            BuiltinPosition(
                "future",
                "Future",
                "The likely direction if the current course continues.",
                0.85,
                0.5,
            ),
        ),
    ),
    BuiltinSpread(
        "situation-challenge-advice",
        "Situation / Challenge / Advice",
        "A modern three-position reading layout organized by practical roles.",
        ("tarot", "runes"),
        (
            BuiltinPosition(
                "situation",
                "Situation",
                "The central circumstances or conditions of the question.",
                0.15,
                0.5,
            ),
            BuiltinPosition(
                "challenge",
                "Challenge",
                "What is obstructing, complicating, or testing the situation.",
                0.5,
                0.5,
            ),
            BuiltinPosition(
                "advice", "Advice", "A perspective or action to consider in response.", 0.85, 0.5
            ),
        ),
    ),
)


def stable_id(value: str) -> str:
    return str(uuid.uuid5(BUILTIN_NAMESPACE, value))


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def resolved_position_values(positions: list, *, spread_id: str) -> list[dict]:
    count = len(positions)
    used: set[str] = set()
    resolved = []
    for index, position in enumerate(sorted(positions, key=lambda row: row.order), 1):
        base_key = position.key or slugify(position.label, f"position-{index}")
        key = base_key
        suffix = 2
        while key in used:
            key = f"{base_key}-{suffix}"
            suffix += 1
        used.add(key)
        x = position.x if position.x is not None else index / (count + 1)
        y = position.y if position.y is not None else 0.5
        resolved.append(
            {
                "id": str(uuid.uuid4()),
                "spread_id": spread_id,
                "key": key,
                "label": position.label.strip(),
                "description": position.description,
                "x": x,
                "y": y,
                "rotation": position.rotation,
                "order": index,
            }
        )
    return resolved


def install_builtin_spreads(session: Session) -> dict[str, int]:
    created = updated = 0
    for definition in BUILTIN_SPREADS:
        spread = session.scalar(
            select(models.SpreadDefinition)
            .where(models.SpreadDefinition.slug == definition.key)
            .options(selectinload(models.SpreadDefinition.positions))
        )
        if spread is None:
            spread = models.SpreadDefinition(id=stable_id(definition.key), slug=definition.key)
            session.add(spread)
            created += 1
        else:
            updated += 1
        spread.name = definition.name
        spread.description = definition.description
        spread.origin = "builtin"
        spread.classification = BUILTIN_CLASSIFICATION
        spread.system_types = list(definition.system_types)
        spread.source_label = BUILTIN_SOURCE
        by_key = {position.key: position for position in spread.positions}
        for order, position_definition in enumerate(definition.positions, 1):
            position = by_key.get(position_definition.key)
            if position is None:
                position = models.SpreadPosition(
                    id=stable_id(f"{definition.key}/{position_definition.key}"),
                    spread_id=spread.id,
                    key=position_definition.key,
                )
                spread.positions.append(position)
            position.label = position_definition.label
            position.description = position_definition.description
            position.x = position_definition.x
            position.y = position_definition.y
            position.rotation = 0
            position.order = order
    session.commit()
    return {"created": created, "updated": updated}
