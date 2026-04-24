"""
StandardChecker MCP server.

The MCP server does not call a separate LLM API. It exposes parsers, KCSC lookup,
and review-context builders so the Claude model that is using this MCP server can
perform the reasoning itself.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


APP_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = APP_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(APP_DIR / ".env")

try:
    from mcp.server import Server
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp import types
except ImportError:
    print("mcp package is required: pip install mcp", file=sys.stderr)
    sys.exit(1)

from standard_checker.clients.kcsc.kcsc import KCSCClient
from standard_checker.parsers.excel_parser import parse_excel
from standard_checker.parsers.pdf_parser import parse_pdf
from standard_checker.prompts import (
    SYSTEM_PROMPT_AUDITOR,
    SYSTEM_PROMPT_CROSS_AUDITOR,
    SYSTEM_PROMPT_DEEP_REVIEWER,
    SYSTEM_PROMPT_EXTRACTOR,
)

HTTP_HOST = os.getenv("HOST", os.getenv("MCP_SERVER_HOST", "0.0.0.0"))
HTTP_PORT = int(os.getenv("PORT", os.getenv("MCP_SERVER_PORT", "8000")))
HTTP_PATH = os.getenv("MCP_SERVER_PATH", "/mcp")

_kcsc: KCSCClient | None = None

SERVER_INSTRUCTIONS = """
StandardChecker exposes local tools for reviewing Korean construction calculation
sheets against KCSC/KDS/KCS standards.

Important: this MCP server never calls a separate LLM API. Claude should use the
returned review package and perform extraction, audit, standard comparison, and
final judgment in the current conversation model.
""".strip()

WORKFLOW_GUIDE = """
# StandardChecker MCP Workflow

Use this server as a context provider. The MCP tools parse files and fetch KCSC
standard text; Claude performs the reasoning.

Recommended order:
1. `parse_excel_sheets` if you need to inspect sheet names first.
2. `review_excel_by_sheet` to build a review package for one or more sheets.
3. Use the returned `claude_review_task` and `review_inputs` to extract checkpoints,
   audit internal consistency, compare against KCSC clauses, and produce judgments.
4. Use `kcsc_get_code_detail` for additional standard text if the package is not enough.

Judgment rules:
- Prefer exact source rows, KDS/KCS clauses, numeric comparisons, and explicit uncertainty.
- Use "검토필요" when evidence is insufficient.
- Do not claim professional certification; this is engineering review support.
""".strip()

REVIEW_SYSTEM_PROMPTS = {
    "extractor": SYSTEM_PROMPT_EXTRACTOR,
    "auditor": SYSTEM_PROMPT_AUDITOR,
    "cross_auditor": SYSTEM_PROMPT_CROSS_AUDITOR,
    "deep_reviewer": SYSTEM_PROMPT_DEEP_REVIEWER,
}

CLAUDE_REVIEW_TASK = """
You are Claude using the StandardChecker MCP context. Do not call any external LLM.
Perform the review yourself using the data in this package.

For each sheet:
1. Extract design inputs, formulas, calculation results, referenced standards, and check conditions.
2. Note missing formula result cells from `missing_formula_results`; these require review unless the value is inferable from nearby rows.
3. Compare extracted checkpoints against the included KCSC standard details.
4. Return concise findings with source row/cell, standard code/clause, judgment, reason, and suggestion.

Use this judgment set exactly: "적합", "부적합", "검토필요".
""".strip()

CLAUDE_REPORT_TASK = """
You are writing a detailed Korean structural review report from a StandardChecker MCP package.
Use the package as the primary evidence source and produce a report that can be used as a draft deliverable.

Core rules:
1. Write in Korean.
2. Use a formal technical report tone.
3. Prefer Markdown headings and tables.
4. Separate compliant items, noncompliant items, and uncertain items.
5. For every important conclusion, include evidence whenever available:
   - source sheet/page
   - source row/cell
   - standard code and clause
   - numeric comparison
6. Do not invent missing data. If the evidence is incomplete, mark the item as "검토필요".
7. If the source package contains conflicting values, treat that as a finding.

Required report sections:
1. Title
2. Review metadata
3. Structural overview
4. Applied code review
5. Material review
6. Load review
7. Member design review
8. Serviceability review
9. Connection / baseplate / anchor review
10. Foundation review
11. Summary of compliant items
12. Summary of correction-required items
13. Follow-up actions

Severity rules:
- 높음: governing-code mismatch, missing basis, unsafe assumption, direct contradiction
- 중간: inconsistent notation, partial traceability, unexplained assumption
- 낮음: editorial cleanup, terminology cleanup, reference cleanup

Judgment rules:
- 적합: evidence supports compliance
- 부적합: evidence shows noncompliance or contradiction
- 검토필요: evidence is incomplete, conflicting, or not traceable enough

Write the report so that a reviewer can reuse it directly with minimal editing.
""".strip()

REPORT_TEMPLATE_MARKDOWN = """
# [프로젝트명]
## 구조계산서 KCSC 건설기준 검토 보고서

> **원본 파일:** [파일명]
> **검토일자:** [작성일]
> **검토목적:** KCSC/KDS/KCS 기준 적합성 검토 및 오류·미비사항 도출

---

## 1. 구조물 개요

| 항목 | 내용 | 근거 |
|------|------|------|
| 공사명 |  |  |
| 위치 |  |  |
| 용도 |  |  |
| 구조형식 |  |  |
| 기초형식 |  |  |
| 설계방법 |  |  |
| 해석 프로그램 |  |  |

## 2. 적용 기준 검토

| 코드번호 | 기준명 | 계산서 근거 | 적용 판단 | 비고 |
|----------|--------|------------|----------|------|

## 3. 사용재료 기준 검토

| 항목 | 계산서 내용 | 근거 | 적용 기준 | 검토 결과 |
|------|-----------|------|---------|---------|

## 4. 하중조건 검토

| 항목 | 계산서 내용 | 근거 | 적용 기준 | 검토 결과 |
|------|-----------|------|---------|---------|

## 5. 하중조합 검토

| 항목 | 계산서 내용 | 근거 | 적용 기준 | 검토 결과 |
|------|-----------|------|---------|---------|

## 6. 구조 부재 설계 검토

| 부재 | 검토 항목 | 계산값 | 기준값 | 판정 | 근거 |
|------|----------|-------|-------|------|------|

## 7. 처짐 및 사용성 검토

| 항목 | 계산값 | 허용값 | 판정 | 근거 |
|------|-------|-------|------|------|

## 8. 접합부 / 베이스플레이트 / 앵커 검토

| 항목 | 계산값 | 기준값 | 판정 | 근거 |
|------|-------|-------|------|------|

## 9. 기초 및 지반 검토

| 항목 | 계산서 내용 | 근거 | 적용 기준 | 검토 결과 |
|------|-----------|------|---------|---------|

## 10. 종합 검토의견

### 10-1. 적합 사항

| 번호 | 항목 | 근거 |
|------|------|------|

### 10-2. 수정·보완 필요 사항

| 번호 | 중요도 | 위치 | 항목 | 문제 내용 | 권고 조치 | 관련 기준 |
|------|--------|------|------|---------|---------|---------|

## 11. 후속 조치 제안

1. [조치 1]
2. [조치 2]
3. [조치 3]

## 12. 참조 기준 목록

| 코드번호 | 기준명 | 비고 |
|----------|--------|------|
""".strip()

server = Server("standardchecker", version="3.0.0", instructions=SERVER_INSTRUCTIONS)


class RemoteMCPASGIApp:
    def __init__(self, session_manager: StreamableHTTPSessionManager):
        self.session_manager = session_manager

    async def __call__(self, scope, receive, send) -> None:
        await self.session_manager.handle_request(scope, receive, send)


def _json_text(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _kcsc_client() -> KCSCClient:
    global _kcsc
    if _kcsc is None:
        _kcsc = KCSCClient()
    return _kcsc

def _parse_file(file_path: str) -> list[dict]:
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = APP_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return parse_excel(str(path))
    if ext == ".pdf":
        return parse_pdf(str(path))
    raise ValueError(f"Unsupported file type: {ext}. Use xlsx, xls, or pdf.")


def _sheet_label(sheet: dict) -> str:
    return sheet.get("sheet") or f"page {sheet.get('page', '')}"


def _filter_sheets(sheets: list[dict], sheet_names: list[str] | None) -> list[dict]:
    if not sheet_names:
        return sheets
    selected = [sheet for sheet in sheets if _sheet_label(sheet) in sheet_names]
    if not selected:
        raise ValueError(f"Cannot find requested sheets: {sheet_names}")
    return selected


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _section_text(section: dict, max_chars: int | None = None) -> str:
    text = (
        section.get("compact_text")
        or section.get("summary_text")
        or section.get("text")
        or ""
    ).strip()
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "..."
    return text


def _numbered_rows_text(section: dict, max_chars: int = 7000) -> str:
    rows = section.get("tables") or []
    if not rows and section.get("lines"):
        rows = [[line.get("text", "")] for line in section.get("lines") or []]
    if not rows:
        return _section_text(section, max_chars=max_chars)

    lines: list[str] = []
    total = 0
    for idx, row in enumerate(rows, start=1):
        cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
        if not cells:
            continue
        line = f"[R{idx}] " + " | ".join(cells)
        if total + len(line) + 1 > max_chars:
            lines.append(f"[R{idx}] ...truncated")
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def _extract_keywords(text: str, limit: int = 32) -> list[str]:
    preferred = [
        "콘크리트",
        "철근",
        "토압",
        "흙막이",
        "기초",
        "말뚝",
        "배근",
        "전단",
        "휨",
        "압축",
        "기둥",
        "벽체",
        "옹벽",
        "슬래브",
        "교량",
        "균열",
        "하중",
        "강도",
        "내진",
        "시공",
        "구조",
    ]
    keywords: list[str] = []
    seen: set[str] = set()
    for keyword in preferred:
        if keyword in text and keyword not in seen:
            keywords.append(keyword)
            seen.add(keyword)

    for token in re.findall(r"[A-Za-z가-힣][A-Za-z가-힣0-9_./-]{1,}", text):
        token = token.strip()
        if len(token) < 2 or token in seen:
            continue
        keywords.append(token)
        seen.add(token)
        if len(keywords) >= limit:
            break
    return keywords[:limit]


def _code_label(code: dict) -> str:
    return f"{code.get('codeType', '')} {code.get('codeNo', '')}".strip()


def _score_code(code: dict, keywords: list[str]) -> int:
    haystack = " ".join(
        str(code.get(key, ""))
        for key in ("name", "codeName", "title", "codeType", "codeNo")
    )
    score = 0
    for keyword in keywords:
        if keyword and keyword in haystack:
            score += max(2, min(len(keyword), 8))
    return score


def _recommend_codes_locally(text: str, limit: int = 8) -> list[dict]:
    try:
        code_list = _kcsc_client().get_code_list()
    except Exception as exc:
        return [{
            "error": f"KCSC code list unavailable: {type(exc).__name__}: {exc}",
            "next_action": "Provide KCSC_API_KEY or call kcsc_get_code_detail after KCSC access is configured.",
        }]
    keywords = _extract_keywords(text)
    scored: list[tuple[int, int, dict]] = []
    for index, code in enumerate(code_list):
        score = _score_code(code, keywords)
        if score > 0:
            scored.append((score, index, code))

    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        recommended = [item[2] for item in scored[:limit]]
    else:
        recommended = code_list[:limit]

    return [
        {
            "codeType": code.get("codeType", ""),
            "codeNo": code.get("codeNo", ""),
            "name": code.get("name") or code.get("codeName") or code.get("title") or "",
            "local_score": _score_code(code, keywords),
        }
        for code in recommended
    ]


def _format_detail(detail: dict, max_chars: int) -> dict:
    parts = []
    for section in detail.get("list", []) or []:
        title = section.get("title", "")
        contents = section.get("contents", "")
        if title or contents:
            parts.append(f"## {title}\n{contents}")
    text = "\n".join(parts).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return {
        "name": detail.get("name", ""),
        "text": text,
    }


def _sheet_progress_summary(sheet: dict, recommended_codes: list[dict], standards: list[dict]) -> dict:
    formula_cells = sheet.get("formula_cells", []) or []
    missing_formula_results = sheet.get("missing_formula_results", []) or []
    preview = _section_text(sheet, max_chars=220)
    top_codes = []
    for code in recommended_codes[:3]:
        if code.get("codeNo"):
            top_codes.append(_code_label(code))

    status = "ready_for_review"
    if missing_formula_results:
        status = "review_attention_needed"
    elif not top_codes:
        status = "needs_manual_standard_selection"

    return {
        "status": status,
        "preview": preview,
        "formula_cell_count": len(formula_cells),
        "missing_formula_result_count": len(missing_formula_results),
        "recommended_code_count": len([code for code in recommended_codes if code.get("codeNo")]),
        "standard_detail_count": len([item for item in standards if item.get("text")]),
        "top_recommended_codes": top_codes,
        "next_actions": [
            "Extract key design inputs and calculation results from numbered_rows_text.",
            "Review missing_formula_results first if any are present.",
            "Compare the extracted checkpoints against standard_details.",
        ],
    }


def _build_progress_overview(file_label: str, review_inputs: list[dict]) -> dict:
    attention_sheets = [
        item["sheet"]
        for item in review_inputs
        if (item.get("progress") or {}).get("missing_formula_result_count", 0) > 0
    ]
    total_missing = sum((item.get("progress") or {}).get("missing_formula_result_count", 0) for item in review_inputs)
    total_codes = sum((item.get("progress") or {}).get("recommended_code_count", 0) for item in review_inputs)

    return {
        "file": file_label,
        "status": "package_ready",
        "step_sequence": [
            "1. Inspect per-sheet progress summaries.",
            "2. Review sheets with missing formula results first.",
            "3. Use numbered_rows_text and standard_details to produce findings.",
        ],
        "attention_sheet_count": len(attention_sheets),
        "attention_sheets": attention_sheets,
        "total_missing_formula_results": total_missing,
        "total_recommended_codes": total_codes,
        "next_prompt_hint": "Summarize the highest-risk sheets first, then produce findings with row/cell evidence and KDS/KCS clauses.",
    }


def _parse_summary(file_label: str, sheets: list[dict]) -> dict:
    total_missing = sum(len(sheet.get("missing_formula_results", []) or []) for sheet in sheets)
    total_formulas = sum(len(sheet.get("formula_cells", []) or []) for sheet in sheets)
    return {
        "file": file_label,
        "status": "parsed",
        "sheet_count": len(sheets),
        "total_formula_cells": total_formulas,
        "total_missing_formula_results": total_missing,
        "next_actions": [
            "Inspect the sheet previews and choose the sheets to review.",
            "Call review_excel_by_sheet for the key structural sheets.",
            "Prioritize sheets with missing formula results.",
        ],
    }


def _standard_details(codes: list[dict], per_code_chars: int) -> list[dict]:
    details = []
    for code in codes:
        code_type = code.get("codeType") or "KCS"
        code_no = code.get("codeNo") or ""
        if not code_no:
            continue
        try:
            detail = _kcsc_client().get_code_detail(code_type, code_no)
        except Exception as exc:
            details.append({
                "code": _code_label(code),
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        formatted = _format_detail(detail or {}, max_chars=per_code_chars)
        details.append({
            "code": _code_label(code),
            "name": formatted["name"] or code.get("name", ""),
            "text": formatted["text"],
        })
    return details


def _build_review_package(
    file_label: str,
    sheets: list[dict],
    max_codes: int = 6,
    include_standard_details: bool = True,
    per_code_chars: int = 1800,
) -> dict:
    review_inputs = []
    for sheet in sheets:
        sheet_name = _sheet_label(sheet)
        numbered_text = _numbered_rows_text(sheet)
        source_text = _section_text(sheet, max_chars=4000)
        recommended_codes = _recommend_codes_locally(numbered_text or source_text, limit=max_codes)
        standards = _standard_details(recommended_codes, per_code_chars) if include_standard_details else []
        progress = _sheet_progress_summary(sheet, recommended_codes, standards)
        review_inputs.append({
            "sheet": sheet_name,
            "source_text": source_text,
            "numbered_rows_text": numbered_text,
            "formula_cells": sheet.get("formula_cells", []),
            "missing_formula_results": sheet.get("missing_formula_results", []),
            "recommended_codes": recommended_codes,
            "standard_details": standards,
            "progress": progress,
        })

    return {
        "mode": "claude_host_model_review",
        "external_llm_called": False,
        "file": file_label,
        "sheet_count": len(review_inputs),
        "progress_overview": _build_progress_overview(file_label, review_inputs),
        "claude_review_task": CLAUDE_REVIEW_TASK,
        "claude_report_task": CLAUDE_REPORT_TASK,
        "report_template_markdown": REPORT_TEMPLATE_MARKDOWN,
        "output_schema": {
            "sheets": [
                {
                    "sheet": "sheet name",
                    "extracted_checkpoints": {
                        "design_inputs": [],
                        "applied_formulas": [],
                        "calculation_results": [],
                        "referenced_standards": [],
                        "check_conditions": [],
                    },
                    "findings": [
                        {
                            "source_row_or_cell": "R12 or B18",
                            "standard_code": "KDS/KCS code",
                            "standard_clause": "clause",
                            "judgment": "적합 | 부적합 | 검토필요",
                            "reason": "numeric and textual basis",
                            "suggestion": "next action",
                        }
                    ],
                }
            ],
            "cross_sheet_audit": {
                "issues": [],
                "summary": "only when multiple sheets are reviewed",
            },
        },
        "review_inputs": review_inputs,
    }


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="standardchecker_workflow",
            description="How Claude should use StandardChecker MCP without external LLM calls",
            arguments=[
                types.PromptArgument(
                    name="file_path",
                    description="Excel/PDF file path to review",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="standardchecker_review_principles",
            description="Review principles and internal prompt references",
        ),
        types.Prompt(
            name="standardchecker_detailed_report",
            description="Detailed Korean report-writing prompt for structural calculation review",
            arguments=[
                types.PromptArgument(
                    name="file_path",
                    description="Excel/PDF file path to review",
                    required=False,
                )
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    arguments = arguments or {}
    if name == "standardchecker_workflow":
        text = WORKFLOW_GUIDE
        file_hint = arguments.get("file_path", "").strip()
        if file_hint:
            text += f"\n\nTarget file: {file_hint}\nCall review_excel_by_sheet, then perform the review yourself."
        return types.GetPromptResult(
            description="StandardChecker no-external-LLM workflow",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=text),
                )
            ],
        )
    if name == "standardchecker_review_principles":
        text = (
            WORKFLOW_GUIDE
            + "\n\n# Host-model review task\n"
            + CLAUDE_REVIEW_TASK
            + "\n\n# Detailed report task\n"
            + CLAUDE_REPORT_TASK
            + "\n\n# Reference prompts used by the app workflow\n"
            + json.dumps(REVIEW_SYSTEM_PROMPTS, ensure_ascii=False, indent=2)
        )
        return types.GetPromptResult(
            description="StandardChecker review principles",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=text),
                )
            ],
        )
    if name == "standardchecker_detailed_report":
        text = "# StandardChecker detailed report prompt\n\n" + CLAUDE_REPORT_TASK
        file_hint = arguments.get("file_path", "").strip()
        if file_hint:
            text += f"\n\nTarget file: {file_hint}"
        text += "\n\n# Report template\n" + REPORT_TEMPLATE_MARKDOWN
        text += (
            "\n\n# Writing note\n"
            "Use progress_overview, each sheet's progress, recommended_codes, standard_details, "
            "and row/cell evidence to produce the report."
        )
        return types.GetPromptResult(
            description="Detailed Korean structural review report prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=text),
                )
            ],
        )
    raise ValueError(f"Unknown prompt: {name}")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri="standardchecker://workflow",
            name="StandardChecker workflow guide",
            description="No-external-LLM MCP workflow for Claude",
            mimeType="text/markdown",
        ),
        types.Resource(
            uri="standardchecker://system-prompts",
            name="StandardChecker prompt references",
            description="Prompt references for extraction, audit, cross-audit, and deep review",
            mimeType="application/json",
        ),
        types.Resource(
            uri="standardchecker://report-template",
            name="StandardChecker report template",
            description="Detailed Korean report-writing prompt and template",
            mimeType="text/markdown",
        ),
    ]


@server.read_resource()
async def read_resource(uri) -> str:
    uri_text = str(uri)
    if uri_text == "standardchecker://workflow":
        return WORKFLOW_GUIDE
    if uri_text == "standardchecker://system-prompts":
        return json.dumps(REVIEW_SYSTEM_PROMPTS, ensure_ascii=False, indent=2)
    if uri_text == "standardchecker://report-template":
        return CLAUDE_REPORT_TASK + "\n\n" + REPORT_TEMPLATE_MARKDOWN
    raise ValueError(f"Unknown resource: {uri_text}")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    sheet_names_property = {
        "type": "array",
        "items": {"type": "string"},
        "description": "Sheet names to include. Omit for all sheets.",
    }
    max_codes_property = {
        "type": "integer",
        "description": "Maximum locally recommended KCSC codes per sheet.",
        "default": 6,
        "minimum": 1,
        "maximum": 12,
    }
    include_standard_details_property = {
        "type": "boolean",
        "description": "Fetch KCSC standard body text for recommended codes.",
        "default": True,
    }

    return [
        types.Tool(
            name="parse_excel_sheets",
            description="Parse Excel/PDF into sheet/page text. No LLM is called.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to .xlsx/.xls/.pdf file"},
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="review_excel_by_sheet",
            description=(
                "Build a Claude review package for an Excel/PDF file. "
                "This does not call any external LLM; Claude should perform the review using the returned package."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to Excel/PDF file"},
                    "sheet_names": sheet_names_property,
                    "max_codes": max_codes_property,
                    "include_standard_details": include_standard_details_property,
                    "per_code_chars": {
                        "type": "integer",
                        "description": "Maximum standard text characters per code.",
                        "default": 1800,
                        "minimum": 500,
                        "maximum": 6000,
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="analyze_single_sheet",
            description="Build a Claude review package from direct sheet text. No external LLM is called.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sheet_text": {"type": "string", "description": "Sheet text to review"},
                    "sheet_name": {"type": "string", "description": "Display sheet name", "default": "시트"},
                    "max_codes": max_codes_property,
                    "include_standard_details": include_standard_details_property,
                    "per_code_chars": {
                        "type": "integer",
                        "description": "Maximum standard text characters per code.",
                        "default": 1800,
                        "minimum": 500,
                        "maximum": 6000,
                    },
                },
                "required": ["sheet_text"],
            },
        ),
        types.Tool(
            name="kcsc_get_code_list",
            description="Return KCSC code list. No LLM is called.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="kcsc_get_code_detail",
            description="Return standard text for a specific KDS/KCS code. No LLM is called.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code_type": {"type": "string", "description": "KDS or KCS", "enum": ["KDS", "KCS"]},
                    "code_no": {"type": "string", "description": "Code number, e.g. 14 20 10 or 142010"},
                },
                "required": ["code_type", "code_no"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}

    if name == "parse_excel_sheets":
        sheets = _parse_file(arguments["file_path"])
        return _json_text({
            "external_llm_called": False,
            "file": Path(arguments["file_path"]).name,
            "progress_overview": _parse_summary(Path(arguments["file_path"]).name, sheets),
            "sheet_count": len(sheets),
            "sheets": [
                {
                    "sheet": _sheet_label(sheet),
                    "char_count": len(sheet.get("text", "")),
                    "preview": sheet.get("text", "")[:800],
                    "text": sheet.get("text", ""),
                    "formula_cells": sheet.get("formula_cells", []),
                    "missing_formula_results": sheet.get("missing_formula_results", []),
                }
                for sheet in sheets
            ],
        })

    if name == "review_excel_by_sheet":
        file_path = arguments["file_path"]
        sheets = _filter_sheets(_parse_file(file_path), arguments.get("sheet_names"))
        package = _build_review_package(
            file_label=Path(file_path).name,
            sheets=sheets,
            max_codes=int(arguments.get("max_codes", 6)),
            include_standard_details=arguments.get("include_standard_details", True),
            per_code_chars=int(arguments.get("per_code_chars", 1800)),
        )
        return _json_text(package)

    if name == "analyze_single_sheet":
        sheet_name = arguments.get("sheet_name", "시트")
        sheet = {"sheet": sheet_name, "text": arguments["sheet_text"], "tables": []}
        package = _build_review_package(
            file_label="direct_input",
            sheets=[sheet],
            max_codes=int(arguments.get("max_codes", 6)),
            include_standard_details=arguments.get("include_standard_details", True),
            per_code_chars=int(arguments.get("per_code_chars", 1800)),
        )
        return _json_text(package)

    if name == "kcsc_get_code_list":
        return _json_text({"external_llm_called": False, "codes": _kcsc_client().get_code_list()})

    if name == "kcsc_get_code_detail":
        detail = _kcsc_client().get_code_detail(arguments["code_type"], arguments["code_no"])
        return _json_text({"external_llm_called": False, "detail": detail})

    raise ValueError(f"Unknown tool: {name}")


def create_app() -> Starlette:
    session_manager = StreamableHTTPSessionManager(app=server)
    mcp_app = RemoteMCPASGIApp(session_manager)

    async def index(_) -> JSONResponse:
        return JSONResponse(
            {
                "name": "KCSC Standard MCP",
                "transport": "streamable_http",
                "mcp_path": HTTP_PATH,
                "health_path": "/healthz",
            }
        )

    async def health(_) -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "name": "KCSC Standard MCP",
                "transport": "streamable_http",
            }
        )

    return Starlette(
        routes=[
            Route("/", endpoint=index, methods=["GET"]),
            Route("/healthz", endpoint=health, methods=["GET"]),
            Route(HTTP_PATH, endpoint=mcp_app, methods=["GET", "POST", "DELETE"]),
        ],
        lifespan=lambda _: session_manager.run(),
    )


def serve() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=HTTP_HOST, port=HTTP_PORT)


def cli() -> None:
    serve()


if __name__ == "__main__":
    cli()
