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
    coins: list[int] | None
    line_value: int
    procedure: dict[str, Any] | None = None


class IChingCastRequest(BaseModel):
    method: Literal["three-coin", "yarrow-stalk", "three_coin"] = "three-coin"


class IChingTextContext(BaseModel):
    key: str
    layer: str
    unit_type: str
    line_position: int | None
    section: str | None
    language: str
    source_id: str
    tradition_id: str | None
    exact_text: str
    locator: str
    sequence: int
    notes: str | None


class HexagramContext(BaseModel):
    key: str | None
    canonical_number: int
    binary_pattern: str
    chinese_name: str | None
    pinyin: str | None
    legge_title: str | None
    glyph: str | None
    texts: list[IChingTextContext]


class IChingKnowledge(BaseModel):
    primary: HexagramContext | None
    relating: HexagramContext | None
    changing_lines: list[int]
    selection_notice: str


class IChingOut(BaseModel):
    method: Literal["three-coin", "yarrow-stalk"]
    pattern_order: Literal["bottom_to_top"]
    primary_pattern: str
    changing_lines: list[int]
    relating_pattern: str
    throws: list[IChingThrowOut]
    knowledge: IChingKnowledge | None = None


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


class ContextRunePoem(BaseModel):
    id: str
    key: str
    item_id: str | None
    source_id: str
    tradition_id: str
    poem: str
    sequence: int
    rune_character: str
    normalized_name: str
    language: str
    original_text: str
    latin_tag: str | None
    locator: str
    mapping_status: str
    mapping_justification: str
    editorial_translation: str
    editorial_latin_gloss: str | None
    translation_language: str
    translation_type: str
    translation_status: str
    translator: str
    machine_assisted: bool
    translation_source_ids: list[str]
    translation_notes: str | None


class ResultKnowledge(BaseModel):
    applicable_interpretations: list[ContextInterpretation]
    other_interpretations: list[ContextInterpretation]
    correspondences: list[ContextCorrespondence]
    rune_poems: list[ContextRunePoem]


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
