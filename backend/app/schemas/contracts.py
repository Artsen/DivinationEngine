import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CorpusStatus(BaseModel):
    rws_ready: bool
    rws_item_count: int
    iching_ready: bool
    hexagram_count: int
    iching_method_count: int
    runes_ready: bool
    elder_futhark_item_count: int
    rune_poem_count: int


class CollectionCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    system_type: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    supports_reversals: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    supports_reversals: bool | None = None
    metadata: dict[str, Any] | None = None


class CollectionOut(CollectionCreate):
    id: str
    item_count: int
    created_at: datetime
    updated_at: datetime


class ItemCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=200)
    display_name: str | None = None
    sequence: int | None = None
    symbol: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ItemOut(ItemCreate):
    id: str
    collection_id: str
    created_at: datetime
    updated_at: datetime


class SourceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=300)
    author: str | None = None
    edition: str | None = None
    publisher: str | None = None
    publication_year: int | None = Field(default=None, ge=1)
    language: str | None = None
    citation: str | None = None
    source_url: HttpUrl | None = None
    rights_status: str | None = None
    notes: str | None = None


class SourceOut(SourceCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class TraditionCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    description: str | None = None


class TraditionOut(TraditionCreate):
    id: str
    created_at: datetime
    updated_at: datetime


InterpretationType = str


class InterpretationCreate(BaseModel):
    key: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    item_id: str
    source_id: str
    tradition_id: str | None = None
    interpretation_type: str = Field(
        min_length=1, max_length=40, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    exact_text: str = Field(min_length=1)
    locator: str | None = None
    sequence: int | None = None
    notes: str | None = None


class InterpretationOut(InterpretationCreate):
    id: str
    created_at: datetime
    updated_at: datetime


CorrespondenceStatus = Literal[
    "attested",
    "reconstructed",
    "disputed",
    "tradition_specific",
    "derived",
    "not_applicable",
    "not_attested",
    "unknown",
]


class CorrespondenceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    item_id: str
    type: str = Field(min_length=1)
    value: str | None = None
    tradition_id: str | None = None
    source_id: str
    status: CorrespondenceStatus
    locator: str | None = None
    notes: str | None = None


class CorrespondenceOut(CorrespondenceCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class PositionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str = Field(min_length=1)
    description: str | None = None
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    rotation: float = Field(default=0, ge=-360, le=360)
    order: int = Field(ge=1)


class PositionOut(BaseModel):
    id: str
    key: str
    label: str
    description: str | None
    x: float
    y: float
    rotation: float
    order: int


class SpreadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    description: str | None = None
    system_types: list[str] = Field(min_length=1)
    positions: list[PositionCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_positions(self) -> "SpreadCreate":
        if len({p.order for p in self.positions}) != len(self.positions):
            raise ValueError("spread position order values must be unique")
        keys = [p.key for p in self.positions if p.key is not None]
        if len(set(keys)) != len(keys):
            raise ValueError("spread position keys must be unique")
        if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) for value in self.system_types):
            raise ValueError("system types must be slug-like values")
        return self


class SpreadPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    positions: list[PositionCreate] | None = None

    @model_validator(mode="after")
    def validate_positions(self) -> "SpreadPatch":
        if self.positions is not None and len({p.order for p in self.positions}) != len(
            self.positions
        ):
            raise ValueError("spread position order values must be unique")
        if self.positions is not None:
            keys = [p.key for p in self.positions if p.key is not None]
            if len(set(keys)) != len(keys):
                raise ValueError("spread position keys must be unique")
        return self


class SpreadOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None
    origin: Literal["builtin", "custom", "legacy"]
    classification: str
    system_types: list[str]
    source_label: str | None
    positions: list[PositionOut]
    created_at: datetime
    updated_at: datetime


class ReadingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    question: str | None = None


class ReadingPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    question: str | None = None


class ReadingSummary(ReadingCreate):
    id: str
    cast_count: int
    cast_types: list[Literal["collection", "iching"]]
    created_at: datetime
    updated_at: datetime


class DrawRequest(BaseModel):
    collection_id: str
    count: int = Field(ge=1)
    reversals_enabled: bool = False
    deck_session_id: str | None = None
    spread_id: str | None = None


class PlacementCreate(BaseModel):
    draw_result_id: str
    spread_id: str | None = None
    spread_position_id: str | None = None
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    rotation: float | None = Field(default=None, ge=-360, le=360)

    @model_validator(mode="after")
    def has_location(self) -> "PlacementCreate":
        if (self.spread_id is None) != (self.spread_position_id is None):
            raise ValueError("spread_id and spread_position_id must be provided together")
        if self.spread_position_id is None and (self.x is None or self.y is None):
            raise ValueError("provide a spread position or both custom x and y")
        return self


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)


class NoteOut(NoteCreate):
    id: str
    reading_id: str
    created_at: datetime
    updated_at: datetime
