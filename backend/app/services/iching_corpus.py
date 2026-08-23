from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.importer import ImportBundle

EXTRACTION_AID_REVISION = "4cecd53bb53aa10fc9a4c92ac30ce541724cd1ff"
UPSTREAM = (
    f"https://raw.githubusercontent.com/88-degrees/Book-of-Changes/{EXTRACTION_AID_REVISION}/"
)
TREE_API = (
    "https://api.github.com/repos/88-degrees/Book-of-Changes/git/trees/"
    f"{EXTRACTION_AID_REVISION}?recursive=1"
)
ZH_API = "https://zh.wikisource.org/w/api.php"
EN_API = "https://en.wikisource.org/w/api.php"
PATTERNS = [
    "111111",
    "000000",
    "100010",
    "010001",
    "111010",
    "010111",
    "010000",
    "000010",
    "111011",
    "110111",
    "111000",
    "000111",
    "101111",
    "111101",
    "001000",
    "000100",
    "100110",
    "011001",
    "110000",
    "000011",
    "100101",
    "101001",
    "000001",
    "100000",
    "100111",
    "111001",
    "100001",
    "011110",
    "010010",
    "101101",
    "001110",
    "011100",
    "001111",
    "111100",
    "000101",
    "101000",
    "101011",
    "110101",
    "001010",
    "010100",
    "110001",
    "100011",
    "111110",
    "011111",
    "000110",
    "011000",
    "010110",
    "011010",
    "101110",
    "011101",
    "100100",
    "001001",
    "001011",
    "110100",
    "101100",
    "001101",
    "011011",
    "110110",
    "010011",
    "110010",
    "110011",
    "001100",
    "101010",
    "010101",
]
TRIGRAMS = (
    ("qian", "乾", "Qián", "☰", "111"),
    ("dui", "兌", "Duì", "☱", "110"),
    ("li", "離", "Lí", "☲", "101"),
    ("zhen", "震", "Zhèn", "☳", "100"),
    ("xun", "巽", "Xùn", "☴", "011"),
    ("kan", "坎", "Kǎn", "☵", "010"),
    ("gen", "艮", "Gèn", "☶", "001"),
    ("kun", "坤", "Kūn", "☷", "000"),
)
APPENDICES = {
    "xici-upper": ("xici-zhuan", "繫辭上", ("appendix03s1.md",)),
    "xici-lower": ("xici-zhuan", "繫辭下", ("appendix03s2.md",)),
    "shuo-gua": ("shuo-gua-zhuan", "說卦", ("appendix05s1.md",)),
    "xu-gua": ("xu-gua-zhuan", "序卦", ("appendix06s1.md",)),
    "za-gua": ("za-gua-zhuan", "雜卦", ("appendix07s1.md",)),
}


_FETCH_CACHE: dict[str, str] = {}


def _fetch(url: str) -> str:
    if url in _FETCH_CACHE:
        return _FETCH_CACHE[url]
    request = urllib.request.Request(url, headers={"User-Agent": "DivinationEngine/0.1 corpus"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                value = response.read().decode("utf-8-sig")
                _FETCH_CACHE[url] = value
                return value
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _strip_markdown(value: str) -> str:
    value = re.sub(r"<a [^>]+/>", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"!\[[^]]*]\([^)]+\)", "", value)
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[<sub>.*?</sub>]", "", value)
    value = value.replace("**", "").replace("*", "").replace("`", "")
    return " ".join(value.split()).strip(" -")


def _page_anchor(value: str) -> str:
    pages = re.findall(r'<a id="p-(\d+)"/>', value)
    return pages[0] if pages else "unpaginated transcription"


def _text(
    *,
    key: str,
    layer: str,
    unit_type: str,
    language: str,
    source: str,
    exact_text: str,
    locator: str,
    sequence: int,
    hexagram: str | None = None,
    line_position: int | None = None,
    section: str | None = None,
    trigram: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "layer": layer,
        "unit_type": unit_type,
        "hexagram": hexagram,
        "trigram": trigram,
        "line_position": line_position,
        "section": section,
        "language": language,
        "source": source,
        "tradition": "received-yijing",
        "exact_text": exact_text.strip(),
        "locator": locator,
        "sequence": sequence,
        "notes": notes,
    }


def _english_hexagram(markdown: str, number: int, key: str) -> tuple[dict[str, Any], list[dict]]:
    title = re.search(r"^#\s+(䷀|䷁|[䷂-䷿])\s+(.+)$", markdown, re.MULTILINE)
    chinese = re.search(r">?\s*Chinese:.*?\s+([\u3400-\u9fff]+)\s+[䷀-䷿]", markdown)
    if not title or not chinese:
        raise ValueError(f"cannot parse English identity for hexagram {number}")
    glyph, pinyin = title.groups()
    body, _, notes = markdown.partition("## Notes")
    judgment_match = re.search(r"^\*\*(?:[䷀-䷿])\s+[^*]+\*\*\s+(.+)$", body, re.MULTILINE)
    if not judgment_match:
        judgment_match = re.search(r'(?m)^<img[^>]+>\s*(?:<a id="p-\d+"/>\s*)*(.+)$', body)
    line_matches = re.findall(r"(?m)^([1-7])\.(?:<a [^>]+/>)?\s*(.+)$", body)
    if not judgment_match or len(line_matches) not in {6, 7}:
        raise ValueError(f"cannot parse Legge text for hexagram {number}")
    base = f"SBE XVI, Hexagram {number}; scan-backed transcription p. {_page_anchor(body)}"
    rows = [
        _text(
            key=f"{key}-gua-ci-en-legge",
            layer="zhouyi-core",
            unit_type="gua-ci",
            language="en",
            source="legge-yi-king-1882",
            exact_text=_strip_markdown(judgment_match.group(1)),
            locator=f"{base}, hexagram statement",
            sequence=number * 100,
            hexagram=key,
        )
    ]
    for raw_position, raw_text in line_matches:
        position = int(raw_position)
        unit = "yao-ci" if position <= 6 else "special-use"
        rows.append(
            _text(
                key=f"{key}-{'line-' + str(position) if position <= 6 else 'special-use'}-en-legge",
                layer="zhouyi-core",
                unit_type=unit,
                language="en",
                source="legge-yi-king-1882",
                exact_text=_strip_markdown(raw_text),
                locator=f"{base}, {'line ' + str(position) if position <= 6 else 'use text'}",
                sequence=number * 100 + position,
                hexagram=key,
                line_position=position if position <= 6 else None,
            )
        )
    if notes.strip():
        rows.append(
            _text(
                key=f"{key}-commentary-en-legge",
                layer="legge-commentary",
                unit_type="hexagram-commentary",
                language="en",
                source="legge-yi-king-1882",
                exact_text=notes.strip(),
                locator=f"{base}, notes",
                sequence=number,
                hexagram=key,
                notes="Markdown transcription retained to preserve Legge's notes and links.",
            )
        )
    identity = {
        "chinese_name": chinese.group(1),
        "pinyin": pinyin,
        "legge_title": f"The {pinyin} Hexagram",
        "glyph": glyph,
    }
    return identity, rows


def _chinese_hexagram(markdown: str, number: int, key: str, chinese_name: str) -> list[dict]:
    preface = markdown.split("\n###", 1)[0]
    quoted = [line[1:].strip() for line in preface.splitlines() if line.startswith(">")]
    quoted = [line for line in quoted if line]
    core = [line for line in quoted if not line.startswith("《")]
    yao = [line for line in core if re.match(r"^(初[六九]|[六九][二三四五]|上[六九])[,，：]", line)]
    if len(yao) != 6:
        raise ValueError(f"expected six Chinese line texts for hexagram {number}, got {len(yao)}")
    judgment = next(
        line for line in core if line not in yao and not line.startswith(("用九", "用六"))
    )
    xiang = [line for line in quoted if line.startswith("《象》")]
    if len(xiang) < 7:
        raise ValueError(f"expected great and six line images for hexagram {number}")
    tuan = next(line for line in quoted if line.startswith("《彖》"))
    locator = (
        f"Chinese Wikisource 周易/{chinese_name}; cross-checked against CTP Book of Changes, "
        f"hexagram {number}"
    )
    rows = [
        _text(
            key=f"{key}-gua-ci-zh-received",
            layer="zhouyi-core",
            unit_type="gua-ci",
            language="zh-Hant",
            source="zhouyi-received-wikisource",
            exact_text=judgment,
            locator=f"{locator}, 易經卦辭",
            sequence=number * 100,
            hexagram=key,
        ),
        _text(
            key=f"{key}-tuan-zh-received",
            layer="tuan-zhuan",
            unit_type="tuan",
            language="zh-Hant",
            source="zhouyi-received-wikisource",
            exact_text=tuan.removeprefix("《彖》曰："),
            locator=f"{locator}, 彖",
            sequence=number,
            hexagram=key,
        ),
        _text(
            key=f"{key}-great-image-zh-received",
            layer="xiang-zhuan-great-image",
            unit_type="great-image",
            language="zh-Hant",
            source="zhouyi-received-wikisource",
            exact_text=xiang[0].removeprefix("《象》曰：").split("。")[0] + "。",
            locator=f"{locator}, 大象",
            sequence=number,
            hexagram=key,
        ),
    ]
    for position, line in enumerate(yao, 1):
        rows.append(
            _text(
                key=f"{key}-line-{position}-zh-received",
                layer="zhouyi-core",
                unit_type="yao-ci",
                language="zh-Hant",
                source="zhouyi-received-wikisource",
                exact_text=line,
                locator=f"{locator}, 爻 {position}",
                sequence=number * 100 + position,
                hexagram=key,
                line_position=position,
            )
        )
        rows.append(
            _text(
                key=f"{key}-line-{position}-image-zh-received",
                layer="xiang-zhuan-line-image",
                unit_type="line-image",
                language="zh-Hant",
                source="zhouyi-received-wikisource",
                exact_text=xiang[position].removeprefix("《象》曰："),
                locator=f"{locator}, 小象 {position}",
                sequence=number * 100 + position,
                hexagram=key,
                line_position=position,
            )
        )
    special = next((line for line in core if line.startswith(("用九", "用六"))), None)
    if special:
        rows.append(
            _text(
                key=f"{key}-special-use-zh-received",
                layer="zhouyi-core",
                unit_type="special-use",
                language="zh-Hant",
                source="zhouyi-received-wikisource",
                exact_text=special,
                locator=f"{locator}, 用辭",
                sequence=number * 100 + 7,
                hexagram=key,
            )
        )
        rows.append(
            _text(
                key=f"{key}-special-image-zh-received",
                layer="xiang-zhuan-line-image",
                unit_type="special-image",
                language="zh-Hant",
                source="zhouyi-received-wikisource",
                exact_text=xiang[7].removeprefix("《象》曰："),
                locator=f"{locator}, 用辭象",
                sequence=number * 100 + 7,
                hexagram=key,
            )
        )
    return rows


def _appendix_blocks(markdown: str) -> list[str]:
    matches = list(re.finditer(r'(?m)^<a id="fr_\d+"/>\[[IVXLCDM]+\]', markdown))
    return [
        markdown[match.start() : matches[index + 1].start() if index + 1 < len(matches) else None]
        for index, match in enumerate(matches)
    ]


def _numbered_paragraphs(block: str) -> list[str]:
    return [
        _strip_markdown(match.group(1))
        for match in re.finditer(r"(?m)^(?:[1-9]|[1-9][0-9]|S)\.\s+(.+)$", block)
    ]


def _legge_wings(tuan_md: str, xiang_md: str) -> list[dict]:
    tuan_blocks = _appendix_blocks(tuan_md)
    xiang_blocks = _appendix_blocks(xiang_md)
    if len(tuan_blocks) != 64 or len(xiang_blocks) != 64:
        raise ValueError("Legge Tuan/Xiang appendices must contain 64 hexagram blocks")
    rows: list[dict] = []
    for number, (tuan, xiang) in enumerate(zip(tuan_blocks, xiang_blocks, strict=True), 1):
        key = f"hexagram-{number:02d}"
        tuan_parts = _numbered_paragraphs(tuan)
        tuan_heading = re.sub(
            r'^<a id="fr_\d+"/>\[[IVXLCDM]+\]\([^)]+\)\.\s*',
            "",
            tuan.splitlines()[0],
        )
        if tuan_heading.strip():
            tuan_parts.insert(0, _strip_markdown(tuan_heading))
        if not tuan_parts:
            raise ValueError(f"missing Legge Tuan for {key}")
        rows.append(
            _text(
                key=f"{key}-tuan-en-legge",
                layer="tuan-zhuan",
                unit_type="tuan",
                language="en",
                source="legge-yi-king-1882",
                exact_text="\n\n".join(tuan_parts),
                locator=f"SBE XVI, Appendix I, Hexagram {number}, p. {_page_anchor(tuan)}",
                sequence=number,
                hexagram=key,
            )
        )
        first_numbered = re.search(r"(?m)^(?:1|I)\.\s+", xiang)
        great_source = xiang[: first_numbered.start()] if first_numbered else xiang
        great_source = re.sub(
            r'^<a id="fr_\d+"/>\[[IVXLCDM]+\]\([^)]+\)\.\s*',
            "",
            great_source,
        )
        great = _strip_markdown(great_source)
        parts = _numbered_paragraphs(xiang)
        if len(parts) < 6:
            raise ValueError(f"missing Legge line images for {key}: {len(parts)}")
        rows.append(
            _text(
                key=f"{key}-great-image-en-legge",
                layer="xiang-zhuan-great-image",
                unit_type="great-image",
                language="en",
                source="legge-yi-king-1882",
                exact_text=great,
                locator=f"SBE XVI, Appendix II, Hexagram {number}, p. {_page_anchor(xiang)}",
                sequence=number,
                hexagram=key,
            )
        )
        for position, exact in enumerate(parts[:6], 1):
            rows.append(
                _text(
                    key=f"{key}-line-{position}-image-en-legge",
                    layer="xiang-zhuan-line-image",
                    unit_type="line-image",
                    language="en",
                    source="legge-yi-king-1882",
                    exact_text=exact,
                    locator=(
                        f"SBE XVI, Appendix II, Hexagram {number}, line {position}, "
                        f"p. {_page_anchor(xiang)}"
                    ),
                    sequence=number * 100 + position,
                    hexagram=key,
                    line_position=position,
                )
            )
        if len(parts) == 7:
            rows.append(
                _text(
                    key=f"{key}-special-image-en-legge",
                    layer="xiang-zhuan-line-image",
                    unit_type="special-image",
                    language="en",
                    source="legge-yi-king-1882",
                    exact_text=parts[6],
                    locator=f"SBE XVI, Appendix II, Hexagram {number}, use text image",
                    sequence=number * 100 + 7,
                    hexagram=key,
                )
            )
    return rows


def _wiki_wikitexts(titles: list[str]) -> dict[str, str]:
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "titles": "|".join(titles),
            "rvprop": "content",
            "rvslots": "main",
            "redirects": 1,
            "format": "json",
            "formatversion": 2,
        }
    )
    result = json.loads(_fetch(f"{ZH_API}?{query}"))["query"]
    by_title = {
        page["title"]: page["revisions"][0]["slots"]["main"]["content"] for page in result["pages"]
    }
    for redirect in result.get("redirects", []):
        by_title[redirect["from"]] = by_title[redirect["to"]]
    return by_title


def _legge_titles() -> dict[int, str]:
    # The scan's contents pages cover all 64 titles. Individual Wikisource
    # subpages currently stop at 31, so they are not a complete acquisition API.
    titles = [f"Page:Sacred Books of the East - Volume 16.djvu/{page}" for page in (12, 13)]
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "titles": "|".join(titles),
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "formatversion": 2,
        }
    )
    pages = json.loads(_fetch(f"{EN_API}?{query}"))["query"]["pages"]
    rows: list[str] = []
    for page in pages:
        wikitext = page["revisions"][0]["slots"]["main"]["content"]
        rows.extend(re.findall(r"(?m)^\{\{TOC row 1-dot-1\|(.+)$", wikitext))
    result: dict[int, str] = {}
    for row in rows:
        number_match = re.match(r"\s*([IVXLCDM]+)\.\|(.+?)\|\{\{DJVU", row)
        if not number_match:
            continue
        roman, raw_title = number_match.groups()
        number = _roman_to_int(roman)
        link = re.search(r"\[\[[^]]+\|(.+)]]", raw_title)
        if link:
            raw_title = link.group(1)
        raw_title = re.sub(r"\{\{bl/il\|([^}]+)}}", r"\1", raw_title)
        result[number] = raw_title.replace("''", "").strip()
    if len(result) != 64:
        raise ValueError("expected 64 Legge titles from scan-backed Wikisource")
    return result


def _roman_to_int(value: str) -> int:
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    previous = 0
    for character in reversed(value):
        current = numerals[character]
        total += -current if current < previous else current
        previous = max(previous, current)
    return total


def _clean_wikitext(value: str) -> str:
    value = re.sub(r"^-\{T\|.*?}-\s*", "", value)
    value = re.sub(r"\{\{header2.*?}}", "", value, flags=re.DOTALL)
    value = re.sub(r"\{\{\*\|([^}]+)}}", r"[\1]", value)
    value = re.sub(r"-\{([^}]+)}-", r"\1", value)
    value = re.sub(r"'''?", "", value)
    return value.strip()


def _general_texts() -> list[dict]:
    rows: list[dict] = []
    titles = [f"周易/{value[1]}" for value in APPENDICES.values()] + ["周易/乾", "周易/坤"]
    wiki = _wiki_wikitexts(titles)
    for sequence, (section, (layer, zh_title, files)) in enumerate(APPENDICES.items(), 1):
        english = "\n\n".join(_fetch(UPSTREAM + filename) for filename in files)
        chinese = _clean_wikitext(wiki[f"周易/{zh_title}"])
        for language, source, exact, locator in (
            (
                "en",
                "legge-yi-king-1882",
                english,
                f"SBE XVI, {layer}, scan pages {_page_anchor(english)} onward",
            ),
            (
                "zh-Hant",
                "zhouyi-received-wikisource",
                chinese,
                f"Chinese Wikisource 周易/{zh_title}; CTP witness {zh_title}",
            ),
        ):
            rows.append(
                _text(
                    key=f"{section}-{language.lower().replace('-', '')}",
                    layer=layer,
                    unit_type="appendix-section",
                    language=language,
                    source=source,
                    exact_text=exact,
                    locator=locator,
                    sequence=sequence,
                    section=section,
                    notes=(
                        "Section boundaries are preserved; internal paragraph numbering "
                        "remains in the text."
                    ),
                )
            )
        if section == "shuo-gua":
            for trigram_key, name, _pinyin, glyph, _pattern in TRIGRAMS:
                english_associations = [
                    _strip_markdown(line)
                    for line in english.splitlines()
                    if glyph in line and _strip_markdown(line)
                ]
                chinese_associations = [
                    _clean_wikitext(line.lstrip("*# "))
                    for line in chinese.splitlines()
                    if f"{name}為" in line
                ]
                if not english_associations or not chinese_associations:
                    raise ValueError(f"missing Shuo Gua associations for {trigram_key}")
                for language, source, passages, locator in (
                    (
                        "en",
                        "legge-yi-king-1882",
                        english_associations,
                        f"SBE XVI, Appendix V, {_pinyin}",
                    ),
                    (
                        "zh-Hant",
                        "zhouyi-received-wikisource",
                        chinese_associations,
                        f"Chinese Wikisource 周易/說卦, {name}",
                    ),
                ):
                    rows.append(
                        _text(
                            key=(
                                f"trigram-{trigram_key}-associations-"
                                f"{language.lower().replace('-', '')}"
                            ),
                            layer="shuo-gua-zhuan",
                            unit_type="trigram-association",
                            language=language,
                            source=source,
                            exact_text="\n\n".join(passages),
                            locator=locator,
                            sequence=sequence,
                            trigram=trigram_key,
                        )
                    )
        if section == "xici-upper":
            yarrow_en = re.search(r"(?m)^51\.\s+(.+)$", english)
            yarrow_zh = next(
                (line.lstrip("*# ") for line in chinese.splitlines() if "大衍之數五十" in line),
                None,
            )
            if not yarrow_en or not yarrow_zh:
                raise ValueError("missing bilingual yarrow-stalk source passage")
            rows.extend(
                [
                    _text(
                        key="yarrow-stalk-procedure-en-legge",
                        layer="yarrow-divination",
                        unit_type="method-source",
                        language="en",
                        source="legge-yi-king-1882",
                        exact_text=_strip_markdown(yarrow_en.group(1)),
                        locator="SBE XVI, Appendix III, Great Appendix I.IX.51, p. 367",
                        sequence=1,
                    ),
                    _text(
                        key="yarrow-stalk-procedure-zh-received",
                        layer="yarrow-divination",
                        unit_type="method-source",
                        language="zh-Hant",
                        source="zhouyi-received-wikisource",
                        exact_text=_clean_wikitext(yarrow_zh),
                        locator="Chinese Wikisource 周易/繫辭上, 大衍之數章",
                        sequence=1,
                    ),
                ]
            )
    wenyan_en = [
        _fetch(UPSTREAM + "appendix04s1.md"),
        _fetch(UPSTREAM + "appendix04s2.md"),
    ]
    for number, (name, english) in enumerate(zip(("乾", "坤"), wenyan_en, strict=True), 1):
        page = _clean_wikitext(wiki[f"周易/{name}"])
        marker = "*文言曰："
        chinese = page.split(marker, 1)[1] if marker in page else page.split("文言曰：", 1)[-1]
        for language, source, exact, locator in (
            ("en", "legge-yi-king-1882", english, f"SBE XVI, Appendix IV, section {number}"),
            (
                "zh-Hant",
                "zhouyi-received-wikisource",
                chinese,
                f"Chinese Wikisource 周易/{name}, 文言",
            ),
        ):
            rows.append(
                _text(
                    key=f"wenyan-{number}-{language.lower().replace('-', '')}",
                    layer="wenyan-zhuan",
                    unit_type="appendix-section",
                    language=language,
                    source=source,
                    exact_text=exact,
                    locator=locator,
                    sequence=number,
                    section=f"hexagram-{number:02d}",
                    hexagram=f"hexagram-{number:02d}",
                )
            )
    return rows


def acquire(root: Path) -> dict[str, int]:
    tree = json.loads(_fetch(TREE_API))["tree"]
    candidates = [
        row["path"]
        for row in tree
        if row["path"].endswith(".md")
        and not row["path"].endswith("_cn.md")
        and not row["path"].startswith(("appendix", "README"))
        and re.match(r"^e[0-9a-f]+.*\.md$", row["path"])
    ]
    legge_titles = _legge_titles()
    parsed: dict[int, tuple[str, str, dict[str, Any], list[dict], str]] = {}
    for filename in candidates:
        english = _fetch(UPSTREAM + filename)
        match = re.search(r"^#\s+([䷀-䷿])", english, re.MULTILINE)
        if not match:
            continue
        number = ord(match.group(1)) - 0x4DC0 + 1
        key = f"hexagram-{number:02d}"
        identity, english_rows = _english_hexagram(english, number, key)
        identity["legge_title"] = legge_titles[number]
        chinese_filename = filename.removesuffix(".md") + "_cn.md"
        chinese = _fetch(UPSTREAM + chinese_filename)
        parsed[number] = (filename, chinese_filename, identity, english_rows, chinese)
    if sorted(parsed) != list(range(1, 65)):
        raise ValueError(f"upstream transcription did not resolve 64 hexagrams: {sorted(parsed)}")

    trigrams = [
        {
            "key": key,
            "chinese_name": name,
            "pinyin": pinyin,
            "glyph": glyph,
            "binary_pattern": pattern,
        }
        for key, name, pinyin, glyph, pattern in TRIGRAMS
    ]
    trigram_by_pattern = {row["binary_pattern"]: row["key"] for row in trigrams}
    hexagrams = []
    lines: list[dict[str, Any]] = []
    texts: list[dict] = []
    for number, pattern in enumerate(PATTERNS, 1):
        _, _, identity, english_rows, chinese = parsed[number]
        key = f"hexagram-{number:02d}"
        hexagrams.append(
            {
                "key": key,
                "canonical_number": number,
                "binary_pattern": pattern,
                **identity,
                "lower_trigram": trigram_by_pattern[pattern[:3]],
                "upper_trigram": trigram_by_pattern[pattern[3:]],
            }
        )
        lines.extend(
            {
                "key": f"{key}-line-{position}",
                "hexagram": key,
                "position": position,
                "polarity": "yang" if bit == "1" else "yin",
            }
            for position, bit in enumerate(pattern, 1)
        )
        texts.extend(english_rows)
        texts.extend(_chinese_hexagram(chinese, number, key, identity["chinese_name"]))
    texts.extend(
        _legge_wings(
            _fetch(UPSTREAM + "appendix01s1.md") + _fetch(UPSTREAM + "appendix01s2.md"),
            _fetch(UPSTREAM + "appendix02s1.md") + _fetch(UPSTREAM + "appendix02s2.md"),
        )
    )
    texts.extend(_general_texts())
    texts.append(
        _text(
            key="three-coin-computational-specification-en",
            layer="three-coin-divination",
            unit_type="method-specification",
            language="en",
            source="three-coin-computational-convention",
            exact_text=(
                "Heads = 3 and tails = 2. TTT = 6, TTH = 7, THH = 8, HHH = 9. "
                "For three independent fair coins the probabilities are 1/8, 3/8, 3/8, "
                "and 1/8 respectively."
            ),
            locator="Computational convention; historical origin not asserted",
            sequence=1,
            notes="Computed specification, not a historical quotation.",
        )
    )

    by_pattern = {row["binary_pattern"]: row["key"] for row in hexagrams}
    relationships = []
    for row in hexagrams:
        pattern = row["binary_pattern"]
        for kind, target in (
            ("complement", "".join("0" if bit == "1" else "1" for bit in pattern)),
            ("inversion", pattern[::-1]),
            ("nuclear", pattern[1:4] + pattern[2:5]),
        ):
            relationships.append(
                {
                    "key": f"{row['key']}-{kind}",
                    "source_hexagram": row["key"],
                    "target_hexagram": by_pattern[target],
                    "relationship_type": kind,
                    "line_position": None,
                }
            )
        for position in range(1, 7):
            changed = list(pattern)
            changed[position - 1] = "0" if changed[position - 1] == "1" else "1"
            relationships.append(
                {
                    "key": f"{row['key']}-line-{position}-change",
                    "source_hexagram": row["key"],
                    "target_hexagram": by_pattern["".join(changed)],
                    "relationship_type": "single-line-change",
                    "line_position": position,
                }
            )

    payload = {
        "format_version": "2",
        "collections": [],
        "sources": [
            {
                "key": "legge-yi-king-1882",
                "title": "The Yî King",
                "author": "James Legge",
                "edition": "Sacred Books of the East, Volume XVI",
                "publisher": "Oxford: Clarendon Press",
                "publication_year": 1882,
                "language": "English",
                "citation": "James Legge, trans., The Yî King, SBE XVI (Oxford, 1882).",
                "source_url": "https://en.wikisource.org/wiki/Index:Sacred_Books_of_the_East_-_Volume_16.djvu",
                "rights_status": "public_domain",
                "notes": (
                    "Scan-backed Wikisource edition; Unlicense Markdown transcription "
                    f"at revision {EXTRACTION_AID_REVISION} used as an extraction aid."
                ),
            },
            {
                "key": "zhouyi-received-wikisource",
                "title": "周易 (received traditional Chinese text)",
                "language": "Classical Chinese",
                "citation": "周易, traditional Chinese transcription, Chinese Wikisource.",
                "source_url": "https://zh.wikisource.org/zh-hant/%E5%91%A8%E6%98%93",
                "rights_status": "public_domain",
                "notes": (
                    "Chinese Wikisource is the reproducible source; CTP is the named "
                    "manual collation witness."
                ),
            },
            {
                "key": "three-coin-computational-convention",
                "title": "Three-coin computational convention",
                "language": "English",
                "citation": (
                    "Documented computational convention; no claim of a single historical origin."
                ),
                "rights_status": "not_applicable",
                "notes": (
                    "Heads=3 and tails=2. Historical origin is intentionally recorded as uncertain."
                ),
            },
        ],
        "traditions": [
            {
                "slug": "received-yijing",
                "name": "Received Yijing",
                "description": (
                    "Received Zhouyi core and Ten Wings, with Legge's 1882 translation "
                    "kept as separate textual records."
                ),
            }
        ],
        "interpretations": [],
        "correspondences": [],
        "trigrams": trigrams,
        "hexagrams": hexagrams,
        "hexagram_lines": lines,
        "iching_texts": texts,
        "iching_relationships": relationships,
        "iching_methods": [
            {
                "key": "three-coin",
                "name": "Three-coin method",
                "probabilities": {"6": "1/8", "7": "3/8", "8": "3/8", "9": "1/8"},
                "source": "three-coin-computational-convention",
                "locator": "Heads=3, tails=2; TTT=6, TTH=7, THH=8, HHH=9",
                "notes": (
                    "Probabilities are computed from three independent fair coins; "
                    "historical origin is not asserted."
                ),
            },
            {
                "key": "yarrow-stalk",
                "name": "Yarrow-stalk method (49 working stalks)",
                "probabilities": {"6": "1/16", "7": "5/16", "8": "7/16", "9": "3/16"},
                "source": "legge-yi-king-1882",
                "locator": (
                    "SBE XVI, Appendix III, Great Appendix I.IX, paragraphs 51-58, pp. 367-370"
                ),
                "notes": (
                    "The distribution is a computational consequence of the implemented "
                    "equiprobable-remainder-class reconstruction, not a quotation from Legge."
                ),
            },
        ],
    }
    empty_keys = [row["key"] for row in texts if not row["exact_text"]]
    if empty_keys:
        raise ValueError(f"empty extracted texts: {', '.join(empty_keys)}")
    bundle = ImportBundle.model_validate(payload)
    root.mkdir(parents=True, exist_ok=True)
    _write_authoring(root, bundle.model_dump(mode="json"))
    (root / "corrections.json").write_text(
        json.dumps(
            {
                "corrections": [],
                "note": (
                    "No silent corrections. Future changes must identify source, locator, "
                    "before, after, and rationale."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return build(root)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_authoring(root: Path, payload: dict[str, Any]) -> None:
    """Materialize reviewable source records separately from generated output."""
    _write_json(
        root / "manifest.json",
        {
            "format_version": payload["format_version"],
            "extraction_aid_revision": EXTRACTION_AID_REVISION,
            "hexagram_files": 64,
            "generated_output": "build/iching-import.json",
        },
    )
    for filename, key in (
        ("sources.json", "sources"),
        ("traditions.json", "traditions"),
        ("trigrams.json", "trigrams"),
        ("relationships.json", "iching_relationships"),
        ("divination-methods.json", "iching_methods"),
    ):
        _write_json(root / filename, payload[key])

    texts_by_hexagram: dict[str, list[dict[str, Any]]] = {}
    general_texts: list[dict[str, Any]] = []
    for row in payload["iching_texts"]:
        if row["hexagram"] is None:
            general_texts.append(row)
        else:
            texts_by_hexagram.setdefault(row["hexagram"], []).append(row)
    lines_by_hexagram: dict[str, list[dict[str, Any]]] = {}
    for row in payload["hexagram_lines"]:
        lines_by_hexagram.setdefault(row["hexagram"], []).append(row)
    _write_json(root / "texts.json", general_texts)
    for hexagram in payload["hexagrams"]:
        key = hexagram["key"]
        _write_json(
            root / "hexagrams" / f"{key}.json",
            {
                "hexagram": hexagram,
                "lines": lines_by_hexagram[key],
                "texts": texts_by_hexagram.get(key, []),
            },
        )


def _load_authoring_bundle(root: Path) -> ImportBundle:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    payload: dict[str, Any] = {
        "format_version": manifest["format_version"],
        "collections": [],
        "interpretations": [],
        "correspondences": [],
        "sources": json.loads((root / "sources.json").read_text(encoding="utf-8")),
        "traditions": json.loads((root / "traditions.json").read_text(encoding="utf-8")),
        "trigrams": json.loads((root / "trigrams.json").read_text(encoding="utf-8")),
        "iching_relationships": json.loads(
            (root / "relationships.json").read_text(encoding="utf-8")
        ),
        "iching_methods": json.loads(
            (root / "divination-methods.json").read_text(encoding="utf-8")
        ),
        "hexagrams": [],
        "hexagram_lines": [],
        "iching_texts": json.loads((root / "texts.json").read_text(encoding="utf-8")),
    }
    hexagram_files = sorted((root / "hexagrams").glob("hexagram-*.json"))
    if len(hexagram_files) != manifest["hexagram_files"]:
        raise ValueError(f"expected {manifest['hexagram_files']} hexagram authoring files")
    for path in hexagram_files:
        record = json.loads(path.read_text(encoding="utf-8"))
        payload["hexagrams"].append(record["hexagram"])
        payload["hexagram_lines"].extend(record["lines"])
        payload["iching_texts"].extend(record["texts"])
    return ImportBundle.model_validate(payload)


def build(root: Path) -> dict[str, int]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bundle = _load_authoring_bundle(root)
    output = root / manifest["generated_output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return validate(root)


def validate(root: Path) -> dict[str, int]:
    bundle = _load_authoring_bundle(root)
    errors: list[str] = []
    if len(bundle.trigrams) != 8:
        errors.append("expected 8 trigrams")
    if len(bundle.hexagrams) != 64 or len(bundle.hexagram_lines) != 384:
        errors.append("expected 64 hexagrams and 384 ordinary lines")
    if [row.binary_pattern for row in bundle.hexagrams] != PATTERNS:
        errors.append("King Wen sequence/pattern mapping differs from the canonical fixture")
    counts = Counter((row.layer, row.language, row.unit_type) for row in bundle.iching_texts)
    expected = {
        ("zhouyi-core", "zh-Hant", "gua-ci"): 64,
        ("zhouyi-core", "en", "gua-ci"): 64,
        ("zhouyi-core", "zh-Hant", "yao-ci"): 384,
        ("zhouyi-core", "en", "yao-ci"): 384,
        ("tuan-zhuan", "zh-Hant", "tuan"): 64,
        ("tuan-zhuan", "en", "tuan"): 64,
        ("xiang-zhuan-great-image", "zh-Hant", "great-image"): 64,
        ("xiang-zhuan-great-image", "en", "great-image"): 64,
        ("xiang-zhuan-line-image", "zh-Hant", "line-image"): 384,
        ("xiang-zhuan-line-image", "en", "line-image"): 384,
    }
    for key, expected_count in expected.items():
        if counts[key] != expected_count:
            errors.append(f"expected {expected_count} {key}, found {counts[key]}")
    relationship_counts = Counter(row.relationship_type for row in bundle.iching_relationships)
    for kind in ("complement", "inversion", "nuclear"):
        if relationship_counts[kind] != 64:
            errors.append(f"expected 64 {kind} relationships")
    if relationship_counts["single-line-change"] != 384:
        errors.append("expected 384 single-line transformations")
    special = [row for row in bundle.iching_texts if row.unit_type == "special-use"]
    if len(special) != 4 or any(row.line_position is not None for row in special):
        errors.append("Qian/Kun special-use texts must be two bilingual non-line units")
    if errors:
        raise ValueError("I Ching corpus validation failed:\n- " + "\n- ".join(errors))
    return {
        "trigrams": len(bundle.trigrams),
        "hexagrams": len(bundle.hexagrams),
        "ordinary_lines": len(bundle.hexagram_lines),
        "texts": len(bundle.iching_texts),
        "relationships": len(bundle.iching_relationships),
        "single_line_transformations": relationship_counts["single-line-change"],
        "methods": len(bundle.iching_methods),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire and validate the Yijing corpus")
    parser.add_argument("command", choices=("acquire", "validate", "build"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "acquire":
        result = acquire(args.root)
    elif args.command == "build":
        result = build(args.root)
    else:
        result = validate(args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
