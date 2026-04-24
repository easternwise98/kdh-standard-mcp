import re
from collections import Counter
from typing import Any

import pdfplumber


MIN_SECTION_CHARS = 200
MAX_SECTIONS = 30
MAX_HEADING_CHARS = 60
COMPACT_MAX_CHARS = 2800
COMPACT_MAX_LINES = 80
BODY_LINE_MIN_CHARS = 80

_HEADING_RE = re.compile(
    r"""^\s*(
        \d+(?:\.\d+){0,3}\s*[\.)]?\s+\S
        |\uc81c\s*\d+\s*[\uc7a5\uc808\ud3b8\ud56d\uc870]\s*\S
        |[IVX]+\.\s+\S
    )""",
    re.VERBOSE | re.IGNORECASE,
)
_LIST_ITEM_RE = re.compile(r"^\s*\d+\)\s")
_PAREN_ITEM_RE = re.compile(r"^\s*[\(\uff08]\s*\d+\s*[\)\uff09]")
_WHITESPACE_RE = re.compile(r"\s+")
_KEYWORD_RE = re.compile(
    r"(\ucf58\ud06c\ub9ac\ud2b8|\ucca0\uadfc|\ud1a0\uc555|\ud751\ub9c9\uc774|"
    r"\ud558\uc911|\uac15\ub3c4|\ub2e8\uba74|\uc751\ub825|\ucc98\uc9d0|"
    r"\uade0\uc5f4|\uae30\uc900|\uaddc\uaca9|\uc801\uc6a9|\uac80\ud1a0|"
    r"\uacb0\uacfc|\uc124\uacc4|fck|fy|MPa|kN|KDS|KCS)",
    re.IGNORECASE,
)


def _heading_level(text: str) -> int:
    stripped = text.strip()
    if not stripped or len(stripped) > MAX_HEADING_CHARS:
        return 0
    if _LIST_ITEM_RE.match(stripped) or _PAREN_ITEM_RE.match(stripped):
        return 0
    if not _HEADING_RE.match(stripped):
        return 0

    numeric = re.match(r"^\s*(\d+(?:\.\d+){0,3})", stripped)
    if numeric:
        return numeric.group(1).count(".") + 1
    return 1


def _resolve(obj: Any) -> Any:
    try:
        return obj.resolve()
    except Exception:
        return obj


def _get_key(mapping: Any, *names: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key, value in mapping.items():
        key_name = getattr(key, "name", key)
        if key_name in names:
            return value
    return None


def _decode_pdf_title(title: Any) -> str:
    if isinstance(title, bytes):
        if title.startswith(b"\xfe\xff"):
            return title[2:].decode("utf-16-be", "ignore").strip()
        for encoding in ("utf-8", "cp949", "latin-1"):
            try:
                return title.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return title.decode("latin-1", "ignore").strip()
    return str(title or "").strip()


def _read_outline(pdf) -> list[dict]:
    """Read PDF bookmarks/outline and return page-based section starts."""
    try:
        doc = pdf.doc
        catalog = _resolve(doc.catalog)
        outlines = _resolve(_get_key(catalog, "Outlines"))
        if not isinstance(outlines, dict):
            return []

        page_index_by_id: dict[int, int] = {}
        for index, page in enumerate(pdf.pages, start=1):
            try:
                page_index_by_id[page.page_obj.objid] = index
            except Exception:
                pass

        def dest_to_page(dest: Any) -> int | None:
            try:
                resolved = _resolve(dest)
                if isinstance(resolved, list) and resolved:
                    page_ref = _resolve(resolved[0])
                    objid = getattr(resolved[0], "objid", None) or getattr(page_ref, "objid", None)
                    if objid:
                        return page_index_by_id.get(objid)
                if isinstance(resolved, (bytes, str)):
                    name = resolved.decode("utf-8", "ignore") if isinstance(resolved, bytes) else resolved
                    dests = _resolve(_get_key(catalog, "Dests"))
                    if isinstance(dests, dict):
                        return dest_to_page(_get_key(dests, name) or dests.get(name))
                if isinstance(resolved, dict):
                    nested = _get_key(resolved, "D")
                    if nested is not None:
                        return dest_to_page(nested)
            except Exception:
                return None
            return None

        results: list[dict] = []

        def walk(node: Any, level: int) -> None:
            resolved = _resolve(node)
            if not isinstance(resolved, dict):
                return

            title = _decode_pdf_title(_get_key(resolved, "Title"))
            page_no = None
            dest = _get_key(resolved, "Dest")
            if dest is not None:
                page_no = dest_to_page(dest)
            else:
                action = _resolve(_get_key(resolved, "A"))
                action_dest = _get_key(action, "D")
                if action_dest is not None:
                    page_no = dest_to_page(action_dest)

            if title and page_no:
                results.append({"title": title, "page": page_no, "level": level})

            first = _get_key(resolved, "First")
            if first is not None:
                walk(first, level + 1)
            next_node = _get_key(resolved, "Next")
            if next_node is not None:
                walk(next_node, level)

        first = _get_key(outlines, "First")
        if first is not None:
            walk(first, 1)

        deduped: list[dict] = []
        seen: set[tuple[int, str]] = set()
        for item in sorted(results, key=lambda x: (x["page"], x["level"], x["title"])):
            key = (item["page"], _WHITESPACE_RE.sub("", item["title"]))
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped
    except Exception:
        return []


def _is_inside_any_bbox(x0: float, top: float, x1: float, bottom: float, bboxes: list[tuple]) -> bool:
    line_mid_x = (x0 + x1) / 2
    line_mid_y = (top + bottom) / 2
    return any(
        bbox[0] - 1 <= line_mid_x <= bbox[2] + 1 and bbox[1] - 1 <= line_mid_y <= bbox[3] + 1
        for bbox in bboxes
    )


def _extract_lines(pdf) -> list[dict]:
    """Flatten pages into line records and mark lines inside detected tables."""
    all_lines: list[dict] = []

    for page_number, page in enumerate(pdf.pages, start=1):
        table_bboxes: list[tuple] = []
        try:
            table_bboxes = [table.bbox for table in page.find_tables() or [] if table.bbox]
        except Exception:
            table_bboxes = []

        char_groups: list[list[dict]] = []
        try:
            chars = sorted(page.chars or [], key=lambda c: (round(float(c.get("top", 0)), 1), float(c.get("x0", 0))))
            current: list[dict] = []
            current_top: float | None = None
            for char in chars:
                top = round(float(char.get("top", 0)), 1)
                if current_top is None or abs(top - current_top) <= 2.5:
                    current.append(char)
                    current_top = top if current_top is None else current_top
                else:
                    char_groups.append(current)
                    current = [char]
                    current_top = top
            if current:
                char_groups.append(current)
        except Exception:
            char_groups = []

        if char_groups:
            for line_number, group in enumerate(char_groups, start=1):
                ordered = sorted(group, key=lambda c: float(c.get("x0", 0)))
                text = "".join(str(c.get("text", "")) for c in ordered).strip()
                if not text:
                    continue
                x0 = min(float(c.get("x0", 0)) for c in ordered)
                x1 = max(float(c.get("x1", x0)) for c in ordered)
                top = min(float(c.get("top", 0)) for c in ordered)
                bottom = max(float(c.get("bottom", top)) for c in ordered)
                all_lines.append(
                    {
                        "page": page_number,
                        "line": line_number,
                        "text": text,
                        "x0": x0,
                        "is_table": _is_inside_any_bbox(x0, top, x1, bottom, table_bboxes),
                    }
                )
            continue

        raw = page.extract_text() or ""
        for line_number, raw_line in enumerate(raw.splitlines(), start=1):
            text = raw_line.strip()
            if text:
                all_lines.append(
                    {"page": page_number, "line": line_number, "text": text, "x0": 0.0, "is_table": False}
                )

    return all_lines


def _page_margins(lines: list[dict]) -> dict[int, float]:
    x0s_by_page: dict[int, list[float]] = {}
    for line in lines:
        if line.get("is_table"):
            continue
        x0s_by_page.setdefault(int(line["page"]), []).append(round(float(line.get("x0", 0)), 0))
    return {
        page: Counter(values).most_common(1)[0][0]
        for page, values in x0s_by_page.items()
        if values
    }


def _detect_headings_strict(lines: list[dict]) -> list[int]:
    """Detect headings using only text pattern, left alignment, and following body lines."""
    margins = _page_margins(lines)
    candidates: list[int] = []

    for index, line in enumerate(lines):
        if line.get("is_table"):
            continue
        level = _heading_level(str(line.get("text", "")))
        if not level:
            continue

        margin = margins.get(int(line["page"]), 0.0)
        if abs(float(line.get("x0", 0)) - margin) > 12:
            continue

        next_ok = False
        for next_index in range(index + 1, min(index + 5, len(lines))):
            next_line = lines[next_index]
            if next_line.get("is_table"):
                continue
            next_text = str(next_line.get("text", "")).strip()
            if len(next_text) >= BODY_LINE_MIN_CHARS:
                next_ok = True
                break
            next_level = _heading_level(next_text)
            if next_level > level:
                next_ok = True
                break
            if next_level:
                break

        if next_ok:
            candidates.append(index)

    return candidates


def _build_compact_text(lines: list[dict]) -> str:
    if not lines:
        return ""

    seen: Counter[str] = Counter()
    scored: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        seen[text] += 1
        if seen[text] > 2:
            continue

        score = 0
        if _KEYWORD_RE.search(text):
            score += 5
        if line.get("is_table"):
            score += 2
        if 5 <= len(text) <= 200:
            score += 1
        if score:
            scored.append((index, score, text))

    if not scored:
        scored = [(index, 1, str(line.get("text", ""))) for index, line in enumerate(lines[:COMPACT_MAX_LINES])]

    selected = sorted(sorted(scored, key=lambda x: (-x[1], x[0]))[:COMPACT_MAX_LINES], key=lambda x: x[0])
    output: list[str] = []
    total = 0
    for _, _, text in selected:
        clipped = text[:240]
        if total + len(clipped) + 1 > COMPACT_MAX_CHARS:
            break
        output.append(clipped)
        total += len(clipped) + 1
    return "\n".join(output)


def _public_lines(lines: list[dict]) -> list[dict]:
    return [
        {"page": int(line["page"]), "line": int(line["line"]), "text": str(line["text"])}
        for line in lines
    ]


def _make_section(title: str, level: int, section_lines: list[dict]) -> dict | None:
    if not section_lines:
        return None
    body_text = "\n".join(str(line.get("text", "")).strip() for line in section_lines).strip()
    if not body_text:
        return None

    return {
        "sheet": title or f"Page {section_lines[0]['page']}",
        "level": level,
        "start_page": int(section_lines[0]["page"]),
        "end_page": int(section_lines[-1]["page"]),
        "text": body_text,
        "compact_text": _build_compact_text(section_lines),
        "lines": _public_lines(section_lines),
        "source_type": "pdf",
    }


def _split_by_indices(
    lines: list[dict],
    heading_indices: list[int],
    titles: list[tuple[str, int]] | None = None,
) -> list[dict]:
    if not heading_indices:
        return []

    sections: list[dict] = []
    boundaries = heading_indices + [len(lines)]
    for index, start in enumerate(heading_indices):
        end = boundaries[index + 1]
        heading_line = lines[start]
        if titles is None:
            title = str(heading_line.get("text", ""))[:MAX_HEADING_CHARS]
            level = _heading_level(title) or 1
        else:
            title, level = titles[index]
        section = _make_section(title, level, lines[start + 1:end])
        if section:
            sections.append(section)
    return sections


def _line_records(section: dict) -> list[dict]:
    return [
        {
            "page": int(line.get("page", section.get("start_page", 1))),
            "line": int(line.get("line", index)),
            "text": str(line.get("text", "")),
            "is_table": False,
        }
        for index, line in enumerate(section.get("lines") or [], start=1)
    ]


def _merge_sections(left: dict, right: dict) -> None:
    left["text"] = (str(left.get("text", "")).rstrip() + "\n" + str(right.get("text", "")).lstrip()).strip()
    left.setdefault("lines", []).extend(right.get("lines") or [])
    left["end_page"] = right.get("end_page", left.get("end_page"))
    left["compact_text"] = _build_compact_text(_line_records(left))


def _post_process(sections: list[dict]) -> list[dict]:
    if not sections:
        return []

    merged: list[dict] = []
    for section in sections:
        if merged and len(str(section.get("text", ""))) < MIN_SECTION_CHARS:
            _merge_sections(merged[-1], section)
        else:
            merged.append(section)

    while len(merged) > MAX_SECTIONS:
        shortest_index = min(range(1, len(merged)), key=lambda i: len(str(merged[i].get("text", ""))))
        section = merged.pop(shortest_index)
        _merge_sections(merged[shortest_index - 1], section)

    for section in merged:
        section["compact_text"] = _build_compact_text(_line_records(section))
    return merged


def _sections_from_outline(lines: list[dict], outline: list[dict]) -> list[dict]:
    page_first_index: dict[int, int] = {}
    for index, line in enumerate(lines):
        page_first_index.setdefault(int(line["page"]), index)

    indices: list[int] = []
    titles: list[tuple[str, int]] = []
    for entry in outline:
        page = int(entry["page"])
        page_start = page_first_index.get(page)
        if page_start is None:
            continue

        target_index = None
        title_norm = _WHITESPACE_RE.sub("", str(entry.get("title", "")))
        for index in range(page_start, len(lines)):
            line = lines[index]
            if int(line["page"]) != page:
                break
            if title_norm and title_norm in _WHITESPACE_RE.sub("", str(line.get("text", ""))):
                target_index = index
                break
        if target_index is None:
            target_index = page_start
        if indices and target_index <= indices[-1]:
            continue

        indices.append(target_index)
        titles.append((str(entry.get("title", ""))[:MAX_HEADING_CHARS], int(entry.get("level") or 1)))

    return _split_by_indices(lines, indices, titles)


def _page_fallback(lines: list[dict]) -> list[dict]:
    pages: dict[int, list[dict]] = {}
    for line in lines:
        pages.setdefault(int(line["page"]), []).append(line)

    sections: list[dict] = []
    for page_number in sorted(pages):
        section = _make_section(f"Page {page_number}", 1, pages[page_number])
        if section:
            section["page"] = page_number
            sections.append(section)
    return sections


def parse_pdf(file) -> list[dict]:
    """Parse a PDF into deterministic sections.

    Priority:
    1. PDF outline/bookmarks.
    2. Strict heading regex with left-alignment and table exclusion.
    3. Page-by-page fallback.

    PDF sections intentionally expose ``lines`` instead of ``tables`` so the UI
    renders them as text, not as an Excel-like grid with guessed dimensions.
    """
    with pdfplumber.open(file) as pdf:
        lines = _extract_lines(pdf)
        if not lines:
            return []

        outline = _read_outline(pdf)
        if outline:
            outline_sections = _sections_from_outline(lines, outline)
            if outline_sections:
                return _post_process(outline_sections)

        heading_indices = _detect_headings_strict(lines)
        if heading_indices:
            regex_sections = _split_by_indices(lines, heading_indices)
            if regex_sections:
                return _post_process(regex_sections)

        return _page_fallback(lines)
