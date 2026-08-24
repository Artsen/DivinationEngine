import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
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
    __table_args__ = (UniqueConstraint("key", name="uq_source_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str | None] = mapped_column(String(160))
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
    __table_args__ = (UniqueConstraint("key", name="uq_interpretation_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str | None] = mapped_column(String(200))
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


class RunePoem(Base, TimestampMixin):
    __tablename__ = "rune_poems"
    __table_args__ = (UniqueConstraint("key", name="uq_rune_poem_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(200))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    tradition_id: Mapped[str] = mapped_column(ForeignKey("traditions.id", ondelete="RESTRICT"))
    poem: Mapped[str] = mapped_column(String(40))
    sequence: Mapped[int] = mapped_column(Integer)
    rune_character: Mapped[str] = mapped_column(String(40))
    normalized_name: Mapped[str] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(40))
    original_text: Mapped[str] = mapped_column(Text)
    latin_tag: Mapped[str | None] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(500))
    mapping_status: Mapped[str] = mapped_column(String(40))
    mapping_justification: Mapped[str] = mapped_column(Text)
    editorial_translation: Mapped[str] = mapped_column(Text)
    editorial_latin_gloss: Mapped[str | None] = mapped_column(Text)
    translation_language: Mapped[str] = mapped_column(String(12), default="en")
    translation_type: Mapped[str] = mapped_column(String(40))
    translation_status: Mapped[str] = mapped_column(String(40))
    translator: Mapped[str] = mapped_column(String(200))
    machine_assisted: Mapped[bool] = mapped_column(default=True)
    translation_source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    translation_notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()
    tradition: Mapped[Tradition] = relationship()


class Correspondence(Base, TimestampMixin):
    __tablename__ = "correspondences"
    __table_args__ = (
        UniqueConstraint("key", name="uq_correspondence_key"),
        CheckConstraint(
            "status IN ('attested','reconstructed','disputed','tradition_specific','derived','not_applicable','not_attested','unknown')",  # noqa: E501
            name="ck_correspondence_status",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str | None] = mapped_column(String(200))
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


class Trigram(Base, TimestampMixin):
    __tablename__ = "trigrams"
    __table_args__ = (
        CheckConstraint("length(binary_pattern) = 3", name="ck_trigram_pattern_length"),
        CheckConstraint(
            "replace(replace(binary_pattern, '0', ''), '1', '') = ''",
            name="ck_trigram_pattern_binary",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    chinese_name: Mapped[str] = mapped_column(String(20))
    pinyin: Mapped[str] = mapped_column(String(40))
    glyph: Mapped[str] = mapped_column(String(8), unique=True)
    binary_pattern: Mapped[str] = mapped_column(String(3), unique=True)


class Hexagram(Base, TimestampMixin):
    """Mechanical identifier; textual claims live in HexagramText with provenance."""

    __tablename__ = "hexagrams"
    __table_args__ = (
        CheckConstraint("canonical_number BETWEEN 1 AND 64", name="ck_hexagram_number"),
        CheckConstraint("length(binary_pattern) = 6", name="ck_hexagram_pattern_length"),
        CheckConstraint(
            "replace(replace(binary_pattern, '0', ''), '1', '') = ''",
            name="ck_hexagram_pattern_binary",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str | None] = mapped_column(String(40), unique=True)
    canonical_number: Mapped[int] = mapped_column(Integer, unique=True)
    binary_pattern: Mapped[str] = mapped_column(String(6), unique=True)
    chinese_name: Mapped[str | None] = mapped_column(String(120))
    pinyin: Mapped[str | None] = mapped_column(String(120))
    legge_title: Mapped[str | None] = mapped_column(String(200))
    glyph: Mapped[str | None] = mapped_column(String(16))
    lower_trigram: Mapped[str | None] = mapped_column(String(120))
    upper_trigram: Mapped[str | None] = mapped_column(String(120))
    lower_trigram_id: Mapped[str | None] = mapped_column(
        ForeignKey("trigrams.id", ondelete="RESTRICT")
    )
    upper_trigram_id: Mapped[str | None] = mapped_column(
        ForeignKey("trigrams.id", ondelete="RESTRICT")
    )


class HexagramLine(Base):
    __tablename__ = "hexagram_lines"
    __table_args__ = (
        UniqueConstraint("hexagram_id", "position", name="uq_hexagram_line_position"),
        UniqueConstraint("key", name="uq_hexagram_line_key"),
        CheckConstraint("position BETWEEN 1 AND 6", name="ck_hexagram_line_position"),
        CheckConstraint("polarity IN ('yin','yang')", name="ck_hexagram_line_polarity"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(80))
    hexagram_id: Mapped[str] = mapped_column(ForeignKey("hexagrams.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    polarity: Mapped[str] = mapped_column(String(8))


class IChingText(Base, TimestampMixin):
    __tablename__ = "iching_texts"
    __table_args__ = (
        UniqueConstraint("key", name="uq_iching_text_key"),
        CheckConstraint(
            "line_position IS NULL OR line_position BETWEEN 1 AND 6",
            name="ck_iching_text_line_position",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(220))
    layer: Mapped[str] = mapped_column(String(80))
    unit_type: Mapped[str] = mapped_column(String(80))
    hexagram_id: Mapped[str | None] = mapped_column(ForeignKey("hexagrams.id", ondelete="CASCADE"))
    trigram_id: Mapped[str | None] = mapped_column(ForeignKey("trigrams.id", ondelete="CASCADE"))
    line_position: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    tradition_id: Mapped[str | None] = mapped_column(
        ForeignKey("traditions.id", ondelete="SET NULL")
    )
    exact_text: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(500))
    sequence: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()
    tradition: Mapped[Tradition | None] = relationship()


class IChingRelationship(Base):
    __tablename__ = "iching_relationships"
    __table_args__ = (UniqueConstraint("key", name="uq_iching_relationship_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(120))
    source_hexagram_id: Mapped[str] = mapped_column(ForeignKey("hexagrams.id", ondelete="CASCADE"))
    target_hexagram_id: Mapped[str] = mapped_column(ForeignKey("hexagrams.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(40))
    line_position: Mapped[int | None] = mapped_column(Integer)


class IChingMethod(Base, TimestampMixin):
    __tablename__ = "iching_methods"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    probabilities: Mapped[dict] = mapped_column(JSON)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    locator: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[Source] = relationship()


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
        UniqueConstraint("id", "spread_id", name="uq_spread_position_identity"),
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
    deck_sessions: Mapped[list["DeckSession"]] = relationship(
        back_populates="reading", cascade="all, delete-orphan"
    )

    @property
    def cast_count(self) -> int:
        return len(self.casts)

    @property
    def cast_types(self) -> list[str]:
        return list(dict.fromkeys(cast.cast_type for cast in self.casts))


class DeckSession(Base):
    __tablename__ = "deck_sessions"
    __table_args__ = (UniqueConstraint("id", "reading_id", "collection_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    reading_id: Mapped[str] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    reading: Mapped[Reading] = relationship(back_populates="deck_sessions")
    collection: Mapped[Collection] = relationship()


class ReadingCast(Base):
    __tablename__ = "reading_casts"
    __table_args__ = (
        UniqueConstraint("reading_id", "cast_order", name="uq_reading_cast_order"),
        UniqueConstraint("id", "deck_session_id", name="uq_cast_deck_session_identity"),
        ForeignKeyConstraint(
            ["deck_session_id", "reading_id", "collection_id"],
            ["deck_sessions.id", "deck_sessions.reading_id", "deck_sessions.collection_id"],
            name="fk_cast_deck_session_scope",
        ),
        CheckConstraint("cast_type IN ('collection','iching')", name="ck_cast_type"),
        CheckConstraint(
            "(cast_type = 'collection' AND collection_id IS NOT NULL "
            "AND primary_pattern IS NULL AND relating_pattern IS NULL) OR "
            "(cast_type = 'iching' AND collection_id IS NULL "
            "AND deck_session_id IS NULL AND primary_pattern IS NOT NULL "
            "AND relating_pattern IS NOT NULL)",
            name="ck_cast_consistency",
        ),
        CheckConstraint(
            "primary_pattern IS NULL OR (length(primary_pattern) = 6 AND "
            "replace(replace(primary_pattern, '0', ''), '1', '') = '')",
            name="ck_cast_primary_pattern",
        ),
        CheckConstraint(
            "relating_pattern IS NULL OR (length(relating_pattern) = 6 AND "
            "replace(replace(relating_pattern, '0', ''), '1', '') = '')",
            name="ck_cast_relating_pattern",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    reading_id: Mapped[str] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    cast_type: Mapped[str] = mapped_column(String(32))
    collection_id: Mapped[str | None] = mapped_column(
        ForeignKey("collections.id", ondelete="RESTRICT")
    )
    deck_session_id: Mapped[str | None] = mapped_column(String(36))
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    cast_order: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    primary_pattern: Mapped[str | None] = mapped_column(String(6))
    relating_pattern: Mapped[str | None] = mapped_column(String(6))
    changing_lines: Mapped[list] = mapped_column(JSON, default=list)
    reading: Mapped[Reading] = relationship(back_populates="casts")
    results: Mapped[list["DrawResult"]] = relationship(
        back_populates="cast",
        cascade="all, delete-orphan",
        order_by="DrawResult.draw_order",
        foreign_keys="DrawResult.cast_id",
    )
    throws: Mapped[list["IChingThrow"]] = relationship(
        back_populates="cast", cascade="all, delete-orphan", order_by="IChingThrow.line_number"
    )


class DrawResult(Base):
    __tablename__ = "draw_results"
    __table_args__ = (
        UniqueConstraint("cast_id", "draw_order", name="uq_draw_order"),
        UniqueConstraint("cast_id", "item_id", name="uq_cast_item"),
        UniqueConstraint("id", "cast_id", name="uq_draw_result_identity"),
        UniqueConstraint("deck_session_id", "item_id", name="uq_deck_session_item"),
        ForeignKeyConstraint(
            ["cast_id", "deck_session_id"],
            ["reading_casts.id", "reading_casts.deck_session_id"],
            name="fk_result_cast_deck_session",
        ),
        CheckConstraint("orientation IN ('upright','reversed','none')", name="ck_orientation"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    cast_id: Mapped[str] = mapped_column(ForeignKey("reading_casts.id", ondelete="CASCADE"))
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"))
    deck_session_id: Mapped[str | None] = mapped_column(String(36))
    draw_order: Mapped[int] = mapped_column(Integer)
    orientation: Mapped[str] = mapped_column(String(20))
    cast: Mapped[ReadingCast] = relationship(back_populates="results", foreign_keys=[cast_id])
    item: Mapped[Item] = relationship()
    placement: Mapped["Placement | None"] = relationship(
        back_populates="draw_result", uselist=False, foreign_keys="Placement.draw_result_id"
    )


class Placement(Base):
    __tablename__ = "placements"
    __table_args__ = (
        UniqueConstraint("cast_id", "spread_position_id", name="uq_cast_position"),
        ForeignKeyConstraint(
            ["draw_result_id", "cast_id"],
            ["draw_results.id", "draw_results.cast_id"],
            ondelete="CASCADE",
            name="fk_placement_draw_cast",
        ),
        ForeignKeyConstraint(
            ["spread_position_id", "spread_id"],
            ["spread_positions.id", "spread_positions.spread_id"],
            ondelete="RESTRICT",
            name="fk_placement_spread_position",
        ),
        CheckConstraint(
            "(spread_id IS NULL AND spread_position_id IS NULL "
            "AND x IS NOT NULL AND y IS NOT NULL) "
            "OR (spread_id IS NOT NULL AND spread_position_id IS NOT NULL)",
            name="ck_placement_location",
        ),
    )
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
    draw_result: Mapped[DrawResult] = relationship(
        back_populates="placement", foreign_keys=[draw_result_id]
    )
    spread_position: Mapped[SpreadPosition | None] = relationship(foreign_keys=[spread_position_id])


class IChingThrow(Base):
    __tablename__ = "iching_throws"
    __table_args__ = (
        UniqueConstraint("cast_id", "line_number", name="uq_iching_line"),
        CheckConstraint("line_number BETWEEN 1 AND 6", name="ck_line_number"),
        CheckConstraint("line_value IN (6,7,8,9)", name="ck_line_value"),
        CheckConstraint("coin_1 IS NULL OR coin_1 IN (2,3)", name="ck_coin_1"),
        CheckConstraint("coin_2 IS NULL OR coin_2 IN (2,3)", name="ck_coin_2"),
        CheckConstraint("coin_3 IS NULL OR coin_3 IN (2,3)", name="ck_coin_3"),
        CheckConstraint(
            "(coin_1 IS NULL AND coin_2 IS NULL AND coin_3 IS NULL) OR "
            "(coin_1 IS NOT NULL AND coin_2 IS NOT NULL AND coin_3 IS NOT NULL)",
            name="ck_coin_presence",
        ),
        CheckConstraint(
            "(coin_1 IS NULL AND coin_2 IS NULL AND coin_3 IS NULL) OR "
            "line_value = coin_1 + coin_2 + coin_3",
            name="ck_line_value_coin_sum",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    cast_id: Mapped[str] = mapped_column(ForeignKey("reading_casts.id", ondelete="CASCADE"))
    line_number: Mapped[int] = mapped_column(Integer)
    coin_1: Mapped[int | None] = mapped_column(Integer)
    coin_2: Mapped[int | None] = mapped_column(Integer)
    coin_3: Mapped[int | None] = mapped_column(Integer)
    line_value: Mapped[int] = mapped_column(Integer)
    procedure: Mapped[dict | None] = mapped_column(JSON)
    cast: Mapped[ReadingCast] = relationship(back_populates="throws")


class ReadingNote(Base, TimestampMixin):
    __tablename__ = "reading_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    reading_id: Mapped[str] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    reading: Mapped[Reading] = relationship(back_populates="notes")
