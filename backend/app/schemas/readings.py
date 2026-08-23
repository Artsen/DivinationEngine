from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.contracts import NoteOut


class PlacementOut(BaseModel):
    id: str
    spread_id: str | None
    spread_position_id: str | None
    x: float | None
    y: float | None
    rotation: float | None
    label: str | None


class DrawItemOut(BaseModel):
    id: str
    collection_id: str
    slug: str
    name: str
    display_name: str | None
    sequence: int | None
    symbol: str | None
    metadata: dict[str, Any]


class DrawResultOut(BaseModel):
    id: str
    draw_order: int
    orientation: Literal["upright", "reversed", "none"]
    item: DrawItemOut
    placement: PlacementOut | None


class IChingThrowOut(BaseModel):
    line_number: int
    coins: list[int]
    line_value: int


class IChingOut(BaseModel):
    method: Literal["three_coin"]
    pattern_order: Literal["bottom_to_top"]
    primary_pattern: str
    changing_lines: list[int]
    relating_pattern: str
    throws: list[IChingThrowOut]


class CastOut(BaseModel):
    id: str
    cast_type: Literal["collection", "iching"]
    collection_id: str | None
    deck_session_id: str | None
    cast_order: int
    configuration: dict[str, Any]
    created_at: datetime
    draw_results: list[DrawResultOut]
    iching: IChingOut | None


class ReadingDetail(BaseModel):
    id: str
    title: str
    question: str | None
    created_at: datetime
    updated_at: datetime
    casts: list[CastOut]
    notes: list[NoteOut]


class ContextInterpretation(BaseModel):
    id: str
    key: str | None
    item_id: str
    source_id: str
    tradition_id: str | None
    interpretation_type: str
    exact_text: str
    locator: str | None
    sequence: int | None
    notes: str | None


class ContextCorrespondence(BaseModel):
    id: str
    key: str | None
    item_id: str
    source_id: str
    tradition_id: str | None
    type: str
    value: str | None
    status: str
    locator: str | None
    notes: str | None


class ResultKnowledge(BaseModel):
    applicable_interpretations: list[ContextInterpretation]
    other_interpretations: list[ContextInterpretation]
    correspondences: list[ContextCorrespondence]


class ContextDrawResult(DrawResultOut):
    knowledge: ResultKnowledge


class ContextCast(BaseModel):
    id: str
    cast_type: Literal["collection", "iching"]
    collection_id: str | None
    deck_session_id: str | None
    cast_order: int
    configuration: dict[str, Any]
    created_at: datetime
    draw_results: list[ContextDrawResult]
    iching: IChingOut | None


class ContextSource(BaseModel):
    id: str
    key: str | None
    title: str
    author: str | None
    edition: str | None
    publisher: str | None
    publication_year: int | None
    language: str | None
    citation: str | None
    source_url: str | None
    rights_status: str | None
    notes: str | None


class ContextTradition(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None


class ReadingContext(BaseModel):
    id: str
    title: str
    question: str | None
    created_at: datetime
    updated_at: datetime
    casts: list[ContextCast]
    notes: list[NoteOut]
    sources: dict[str, ContextSource]
    traditions: dict[str, ContextTradition]
    notice: str
