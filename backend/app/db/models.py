import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid4_str() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Collection(Base, TimestampMixin):
    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint("system_type IN ('tarot','oracle','runes')", name="ck_collection_system"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    system_type: Mapped[str] = mapped_column(String(32))
    supports_reversals: Mapped[bool] = mapped_column(default=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    items: Mapped[list["Item"]] = relationship(back_populates="collection", cascade="all, delete")

    @property
    def item_count(self) -> int:
        return len(self.items)


class Item(Base, TimestampMixin):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("collection_id", "slug", name="uq_item_collection_slug"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str | None] = mapped_column(String(200))
    sequence: Mapped[int | None] = mapped_column(Integer)
    symbol: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    collection: Mapped[Collection] = relationship(back_populates="items")


class Tradition(Base, TimestampMixin):
    __tablename__ = "traditions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str | None] = mapped_column(String(200))
    edition: Mapped[str | None] = mapped_column(String(120))
    publisher: Mapped[str | None] = mapped_column(String(200))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(40))
    citation: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500))
    rights_status: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)


class Interpretation(Base, TimestampMixin):
    __tablename__ = "interpretations"
    __table_args__ = (
        CheckConstraint(
            "interpretation_type IN ('upright','reversed','divinatory','symbolism','description','commentary')",  # noqa: E501
            name="ck_interpretation_type",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    tradition_id: Mapped[str | None] = mapped_column(
        ForeignKey("traditions.id", ondelete="SET NULL")
    )
    interpretation_type: Mapped[str] = mapped_column(String(40))
    exact_text: Mapped[str] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(String(200))
    sequence: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()
    tradition: Mapped[Tradition | None] = relationship()


class Correspondence(Base, TimestampMixin):
    __tablename__ = "correspondences"
    __table_args__ = (
        CheckConstraint(
            "status IN ('attested','disputed','tradition_specific','not_applicable','not_attested','unknown')",  # noqa: E501
            name="ck_correspondence_status",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(Text)
    tradition_id: Mapped[str | None] = mapped_column(
        ForeignKey("traditions.id", ondelete="SET NULL")
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(40))
    locator: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()
    tradition: Mapped[Tradition | None] = relationship()


class Hexagram(Base, TimestampMixin):
    """Mechanical identifier; textual claims live in HexagramText with provenance."""

    __tablename__ = "hexagrams"
    __table_args__ = (
        CheckConstraint("canonical_number BETWEEN 1 AND 64", name="ck_hexagram_number"),
        CheckConstraint("length(binary_pattern) = 6", name="ck_hexagram_pattern_length"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    canonical_number: Mapped[int] = mapped_column(Integer, unique=True)
    binary_pattern: Mapped[str] = mapped_column(String(6), unique=True)
    chinese_name: Mapped[str | None] = mapped_column(String(120))
    glyph: Mapped[str | None] = mapped_column(String(16))
    lower_trigram: Mapped[str | None] = mapped_column(String(120))
    upper_trigram: Mapped[str | None] = mapped_column(String(120))


class HexagramText(Base, TimestampMixin):
    __tablename__ = "hexagram_texts"
    __table_args__ = (
        CheckConstraint(
            "text_type IN ('original','translation','judgment','image','line','commentary')",
            name="ck_hexagram_text_type",
        ),
        CheckConstraint(
            "line_number IS NULL OR line_number BETWEEN 1 AND 6",
            name="ck_hexagram_text_line",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    hexagram_id: Mapped[str] = mapped_column(ForeignKey("hexagrams.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    tradition_id: Mapped[str | None] = mapped_column(
        ForeignKey("traditions.id", ondelete="SET NULL")
    )
    text_type: Mapped[str] = mapped_column(String(40))
    line_number: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(40))
    exact_text: Mapped[str] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(String(200))
    sequence: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()
    tradition: Mapped[Tradition | None] = relationship()


class SpreadDefinition(Base, TimestampMixin):
    __tablename__ = "spreads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    positions: Mapped[list["SpreadPosition"]] = relationship(
        back_populates="spread", cascade="all, delete-orphan", order_by="SpreadPosition.order"
    )


class SpreadPosition(Base):
    __tablename__ = "spread_positions"
    __table_args__ = (
        UniqueConstraint("spread_id", "order", name="uq_spread_position_order"),
        CheckConstraint('"order" >= 1', name="ck_spread_position_order"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    spread_id: Mapped[str] = mapped_column(ForeignKey("spreads.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    rotation: Mapped[float] = mapped_column(Float, default=0)
    order: Mapped[int] = mapped_column(Integer)
    spread: Mapped[SpreadDefinition] = relationship(back_populates="positions")


class Reading(Base, TimestampMixin):
    __tablename__ = "readings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    title: Mapped[str] = mapped_column(String(200))
    question: Mapped[str | None] = mapped_column(Text)
    casts: Mapped[list["ReadingCast"]] = relationship(
        back_populates="reading", cascade="all, delete-orphan", order_by="ReadingCast.cast_order"
    )
    notes: Mapped[list["ReadingNote"]] = relationship(
        back_populates="reading", cascade="all, delete-orphan", order_by="ReadingNote.created_at"
    )


class ReadingCast(Base):
    __tablename__ = "reading_casts"
    __table_args__ = (
        UniqueConstraint("reading_id", "cast_order", name="uq_reading_cast_order"),
        CheckConstraint("cast_type IN ('collection','iching')", name="ck_cast_type"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    reading_id: Mapped[str] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    cast_type: Mapped[str] = mapped_column(String(32))
    collection_id: Mapped[str | None] = mapped_column(
        ForeignKey("collections.id", ondelete="RESTRICT")
    )
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    cast_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    primary_pattern: Mapped[str | None] = mapped_column(String(6))
    relating_pattern: Mapped[str | None] = mapped_column(String(6))
    changing_lines: Mapped[list] = mapped_column(JSON, default=list)
    reading: Mapped[Reading] = relationship(back_populates="casts")
    results: Mapped[list["DrawResult"]] = relationship(
        back_populates="cast", cascade="all, delete-orphan", order_by="DrawResult.draw_order"
    )
    throws: Mapped[list["IChingThrow"]] = relationship(
        back_populates="cast", cascade="all, delete-orphan", order_by="IChingThrow.line_number"
    )


class DrawResult(Base):
    __tablename__ = "draw_results"
    __table_args__ = (
        UniqueConstraint("cast_id", "draw_order", name="uq_draw_order"),
        UniqueConstraint("cast_id", "item_id", name="uq_cast_item"),
        CheckConstraint("orientation IN ('upright','reversed','none')", name="ck_orientation"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    cast_id: Mapped[str] = mapped_column(ForeignKey("reading_casts.id", ondelete="CASCADE"))
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"))
    draw_order: Mapped[int] = mapped_column(Integer)
    orientation: Mapped[str] = mapped_column(String(20))
    cast: Mapped[ReadingCast] = relationship(back_populates="results")
    item: Mapped[Item] = relationship()
    placement: Mapped["Placement | None"] = relationship(
        back_populates="draw_result", uselist=False
    )


class Placement(Base):
    __tablename__ = "placements"
    __table_args__ = (UniqueConstraint("cast_id", "spread_position_id", name="uq_cast_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    cast_id: Mapped[str] = mapped_column(ForeignKey("reading_casts.id", ondelete="CASCADE"))
    draw_result_id: Mapped[str] = mapped_column(
        ForeignKey("draw_results.id", ondelete="CASCADE"), unique=True
    )
    spread_id: Mapped[str | None] = mapped_column(ForeignKey("spreads.id", ondelete="RESTRICT"))
    spread_position_id: Mapped[str | None] = mapped_column(
        ForeignKey("spread_positions.id", ondelete="RESTRICT")
    )
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    rotation: Mapped[float | None] = mapped_column(Float)
    draw_result: Mapped[DrawResult] = relationship(back_populates="placement")
    spread_position: Mapped[SpreadPosition | None] = relationship()


class IChingThrow(Base):
    __tablename__ = "iching_throws"
    __table_args__ = (
        UniqueConstraint("cast_id", "line_number", name="uq_iching_line"),
        CheckConstraint("line_number BETWEEN 1 AND 6", name="ck_line_number"),
        CheckConstraint("line_value IN (6,7,8,9)", name="ck_line_value"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    cast_id: Mapped[str] = mapped_column(ForeignKey("reading_casts.id", ondelete="CASCADE"))
    line_number: Mapped[int] = mapped_column(Integer)
    coin_1: Mapped[int] = mapped_column(Integer)
    coin_2: Mapped[int] = mapped_column(Integer)
    coin_3: Mapped[int] = mapped_column(Integer)
    line_value: Mapped[int] = mapped_column(Integer)
    cast: Mapped[ReadingCast] = relationship(back_populates="throws")


class ReadingNote(Base, TimestampMixin):
    __tablename__ = "reading_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    reading_id: Mapped[str] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    reading: Mapped[Reading] = relationship(back_populates="notes")
