from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.services.importer import (
    ImportBundle,
    ImportCollection,
    ImportCorrespondence,
    ImportInterpretation,
    ImportSource,
)

RANKS = (
    "ace",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "page",
    "knight",
    "queen",
    "king",
)
SUITS = ("wands", "cups", "swords", "pentacles")


class CorpusManifest(BaseModel):
    format_version: Literal["1"] = "1"
    slug: str
    name: str
    description: str
    system_type: Literal["tarot"] = "tarot"
    supports_reversals: bool = True
    authoritative_text_source: str


class CorpusImage(BaseModel):
    key: str
    card: str
    card_name: str
    source_repository: str
    collection: str
    file_page_url: str
    direct_download_url: str
    filename: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    format: Literal["image/jpeg"]
    artist: str
    scanner_credit: str
    original_year: int
    rights_status: Literal["public_domain"]
    license: str
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class CorpusCard(BaseModel):
    slug: str
    name: str
    sequence: int
    arcana: Literal["major", "minor"]
    major_number: int | None = None
    suit: str | None = None
    rank: str | None = None
    rank_index: int | None = None
    interpretations: list[ImportInterpretation]
    correspondences: list[ImportCorrespondence]
    image_key: str


class LoadedCorpus(BaseModel):
    root: Path
    manifest: CorpusManifest
    sources: list[ImportSource]
    traditions: list[dict[str, Any]]
    cards: list[CorpusCard]
    images: list[CorpusImage]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_corpus(root: Path) -> LoadedCorpus:
    card_paths = sorted((root / "cards").glob("*.json"))
    return LoadedCorpus(
        root=root,
        manifest=CorpusManifest.model_validate(_read_json(root / "manifest.json")),
        sources=[ImportSource.model_validate(row) for row in _read_json(root / "sources.json")],
        traditions=_read_json(root / "traditions.json"),
        cards=[CorpusCard.model_validate(_read_json(path)) for path in card_paths],
        images=[
            CorpusImage.model_validate(row) for row in _read_json(root / "images" / "manifest.json")
        ],
    )


def _unique(values: list[str], label: str, errors: list[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate {label}: {', '.join(duplicates)}")


def validate_corpus(corpus: LoadedCorpus, *, require_assets: bool = True) -> dict[str, int]:
    errors: list[str] = []
    cards = corpus.cards
    majors = [card for card in cards if card.arcana == "major"]
    minors = [card for card in cards if card.arcana == "minor"]
    if len(cards) != 78:
        errors.append(f"expected 78 cards, found {len(cards)}")
    if len(majors) != 22:
        errors.append(f"expected 22 majors, found {len(majors)}")
    if len(minors) != 56:
        errors.append(f"expected 56 minors, found {len(minors)}")
    if sorted(card.sequence for card in cards) != list(range(78)):
        errors.append("card sequences must be exactly 0-77")
    if sorted(card.major_number for card in majors if card.major_number is not None) != list(
        range(22)
    ):
        errors.append("major numbers must be exactly 0-21")
    for suit in SUITS:
        suit_cards = [card for card in minors if card.suit == suit]
        if len(suit_cards) != 14:
            errors.append(f"expected 14 {suit}, found {len(suit_cards)}")
        if sorted(card.rank for card in suit_cards if card.rank) != sorted(RANKS):
            errors.append(f"{suit} ranks do not match the canonical 14 ranks")

    _unique([card.slug for card in cards], "card slug", errors)
    _unique([source.key for source in corpus.sources], "source key", errors)
    interpretations = [row for card in cards for row in card.interpretations]
    correspondences = [row for card in cards for row in card.correspondences]
    _unique([row.key for row in interpretations], "interpretation key", errors)
    _unique([row.key for row in correspondences], "correspondence key", errors)
    _unique([image.key for image in corpus.images], "image key", errors)
    _unique([image.card for image in corpus.images], "image card mapping", errors)

    card_refs = {f"{corpus.manifest.slug}/{card.slug}" for card in cards}
    source_keys = {source.key for source in corpus.sources}
    tradition_slugs = {row["slug"] for row in corpus.traditions}
    image_keys = {image.key for image in corpus.images}
    if len(corpus.images) != 78:
        errors.append(f"expected 78 image records, found {len(corpus.images)}")
    if {image.card for image in corpus.images} != card_refs:
        errors.append("image-to-card mappings do not exactly cover the corpus")
    if {card.image_key for card in cards} != image_keys:
        errors.append("card image keys do not exactly cover the image manifest")
    for card in cards:
        kinds = {row.interpretation_type for row in card.interpretations}
        if not {"upright", "reversed"}.issubset(kinds):
            errors.append(f"{card.slug}: missing upright or reversed Waite text")
        if not {"description", "symbolism"}.intersection(kinds):
            errors.append(f"{card.slug}: missing description or symbolism")
    for row in interpretations:
        if row.item not in card_refs:
            errors.append(f"{row.key}: unknown item {row.item}")
        if row.source not in source_keys:
            errors.append(f"{row.key}: unknown source {row.source}")
        if row.tradition and row.tradition not in tradition_slugs:
            errors.append(f"{row.key}: unknown tradition {row.tradition}")
    for correspondence in correspondences:
        if correspondence.item not in card_refs:
            errors.append(f"{correspondence.key}: unknown item {correspondence.item}")
        if correspondence.source not in source_keys:
            errors.append(f"{correspondence.key}: unknown source {correspondence.source}")
        if correspondence.tradition and correspondence.tradition not in tradition_slugs:
            errors.append(f"{correspondence.key}: unknown tradition {correspondence.tradition}")
    if corpus.manifest.authoritative_text_source not in source_keys:
        errors.append("authoritative text source is not registered")

    for image in corpus.images:
        path = corpus.root / "images" / "originals" / image.filename
        if require_assets and not path.is_file():
            errors.append(f"missing image asset: {image.filename}")
            continue
        if require_assets:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if image.sha256 != digest:
                errors.append(f"SHA-256 mismatch: {image.filename}")
            width, height = _jpeg_dimensions(path)
            if (width, height) != (image.width, image.height):
                errors.append(f"dimension mismatch: {image.filename}")
    if errors:
        raise ValueError("Corpus validation failed:\n- " + "\n- ".join(errors))
    return {
        "cards": len(cards),
        "majors": len(majors),
        "minors": len(minors),
        **{suit: sum(card.suit == suit for card in minors) for suit in SUITS},
        "interpretations": len(interpretations),
        "correspondences": len(correspondences),
        "images": len(corpus.images),
        "image_hashes": sum(image.sha256 is not None for image in corpus.images),
    }


def build_bundle(corpus: LoadedCorpus) -> ImportBundle:
    validate_corpus(corpus)
    images = {image.key: image for image in corpus.images}
    items = []
    for card in sorted(corpus.cards, key=lambda row: row.sequence):
        image = images[card.image_key]
        items.append(
            {
                "slug": card.slug,
                "name": card.name,
                "display_name": card.name,
                "sequence": card.sequence,
                "metadata": {
                    "arcana": card.arcana,
                    "major_number": card.major_number,
                    "suit": card.suit,
                    "rank": card.rank,
                    "rank_index": card.rank_index,
                    "image": image.model_dump(),
                },
            }
        )
    bundle = ImportBundle(
        collections=[
            ImportCollection(
                slug=corpus.manifest.slug,
                name=corpus.manifest.name,
                description=corpus.manifest.description,
                system_type=corpus.manifest.system_type,
                supports_reversals=corpus.manifest.supports_reversals,
                metadata={
                    "authoritative_text_source": corpus.manifest.authoritative_text_source,
                    "corpus_format_version": corpus.manifest.format_version,
                },
                items=items,
            )
        ],
        sources=corpus.sources,
        traditions=corpus.traditions,
        interpretations=[row for card in corpus.cards for row in card.interpretations],
        correspondences=[row for card in corpus.cards for row in card.correspondences],
    )
    output = corpus.root / "build" / "rws-import.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return bundle


def download_assets(corpus: LoadedCorpus) -> dict[str, int]:
    destination = corpus.root / "images" / "originals"
    destination.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    total_bytes = 0
    updated: list[CorpusImage] = []
    for number, image in enumerate(corpus.images, 1):
        path = destination / image.filename
        if not path.is_file():
            redirect_url = (
                "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
                f"{urllib.parse.quote(image.filename)}?width=1024"
            )
            try:
                _download(redirect_url, path, attempts=1)
            except urllib.error.HTTPError as exc:
                if exc.code != 429:
                    raise
                print(f"Commons rate-limited {image.filename}; using verified byte mirror")
                _download(_mirror_url(image), path)
            downloaded += 1
            time.sleep(1.0)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        width, height = _jpeg_dimensions(path)
        if (width, height) != (image.width, image.height):
            raise ValueError(f"downloaded dimensions do not match metadata: {image.filename}")
        total_bytes += path.stat().st_size
        updated.append(image.model_copy(update={"sha256": digest}))
        print(f"[{number:02}/78] {image.filename}")
    manifest_path = corpus.root / "images" / "manifest.json"
    manifest_path.write_text(
        json.dumps([row.model_dump() for row in updated], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"downloaded": downloaded, "images": len(updated), "total_bytes": total_bytes}


def _mirror_url(image: CorpusImage) -> str:
    stem = image.filename.removeprefix("RWS1909 - ").removesuffix(".jpeg")
    first, remainder = stem.split(" ", 1)
    if first.isdigit():
        mirror_name = f"major_{first}_{remainder.lower().replace(' ', '_')}"
    else:
        rank_number = int(remainder)
        rank = RANKS[rank_number - 1]
        mirror_rank = f"{rank_number:02d}" if 2 <= rank_number <= 10 else rank
        mirror_name = f"{first.lower()}_{mirror_rank}"
    return f"https://raw.githubusercontent.com/gbox3d/talisman/main/public/cards/{mirror_name}.jpeg"


def _download(url: str, destination: Path, *, attempts: int = 6) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DivinationEngine corpus maintainer/0.1 (public-domain archival fetch)"
        },
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                destination.write_bytes(response.read())
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            retry_after = min(int(exc.headers.get("Retry-After", "0")), 60)
            time.sleep(max(retry_after, 2 ** (attempt + 1)))


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise ValueError(f"not a JPEG: {path.name}")
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(data[offset : offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            return (
                int.from_bytes(data[offset + 5 : offset + 7], "big"),
                int.from_bytes(data[offset + 3 : offset + 5], "big"),
            )
        offset += length
    raise ValueError(f"JPEG dimensions not found: {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate provenance-first corpora")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "build"):
        child = subparsers.add_parser(command)
        child.add_argument("root", type=Path)
    assets = subparsers.add_parser("assets")
    assets_subparsers = assets.add_subparsers(dest="assets_command", required=True)
    download = assets_subparsers.add_parser("download")
    download.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        corpus = load_corpus(args.root)
        result: dict[str, Any]
        if args.command == "validate":
            result = validate_corpus(corpus)
        elif args.command == "build":
            bundle = build_bundle(corpus)
            result = {
                "output": str(args.root / "build" / "rws-import.json"),
                "interpretations": len(bundle.interpretations),
                "correspondences": len(bundle.correspondences),
            }
        else:
            result = download_assets(corpus)
    except (OSError, ValueError, ValidationError, urllib.error.URLError) as exc:
        parser.exit(1, f"Corpus command failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
