import os
import time
import threading
import requests
import html
import re
from re import sub
from dotenv import load_dotenv

load_dotenv()

# 코드 목록 모듈 레벨 캐시 (TTL: 1시간)
_cache_lock = threading.Lock()
_code_list_cache: list[dict] | None = None
_code_list_ts: float = 0.0
_CODE_LIST_TTL = 3600


class KCSCClient:
    """국가건설기준센터(KCSC) API 클라이언트"""

    BASE_URL = "https://kcsc.re.kr/OpenApi"
    _tls = threading.local()

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("KCSC API Key가 없습니다. UI에서 키를 입력하세요 (필수).")

    # ── 내부 유틸 ────────────────────────────────────────────────

    def _session(self) -> requests.Session:
        """스레드별 독립 Session (thread-safe)"""
        if not hasattr(self._tls, "session"):
            self._tls.session = requests.Session()
        return self._tls.session

    def _clean_html(self, raw: str) -> str:
        """HTML 태그 제거 및 텍스트 정제"""
        if not raw:
            return ""
        text = str(raw)

        def _strip_tags(fragment: str) -> str:
            cleaned = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
            cleaned = sub(r"<.*?>", "", cleaned)
            cleaned = html.unescape(cleaned).replace("\xa0", " ")
            cleaned = sub(r"[ \t]+", " ", cleaned)
            return cleaned.strip()

        def _table_repl(match):
            table_html = match.group(0)
            rows = []
            for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL):
                cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.IGNORECASE | re.DOTALL)
                row = [_strip_tags(cell) for cell in cells]
                if any(row):
                    rows.append(row)
            if not rows:
                return "\n"

            max_cols = max(len(row) for row in rows)
            padded = [row + [""] * (max_cols - len(row)) for row in rows]
            lines = ["[표]"]
            for idx, row in enumerate(padded):
                line = " | ".join(cell or "-" for cell in row)
                lines.append(line)
                if idx == 0 and len(padded) > 1:
                    lines.append(" | ".join("---" for _ in range(max_cols)))
            return "\n" + "\n".join(lines) + "\n"

        # Formulas are sometimes embedded as images; preserve available alt/title text
        # before removing tags so equation labels are not the only visible remains.
        def _img_repl(match):
            tag = match.group(0)
            attr_match = sub(r"\s+", " ", tag)
            for attr in ("alt", "title"):
                m = re.search(rf'{attr}\s*=\s*["\']([^"\']+)["\']', attr_match, flags=re.IGNORECASE)
                if m and m.group(1).strip():
                    return f" {m.group(1).strip()} "
            return " "

        text = re.sub(r"<table\b[^>]*>.*?</table>", _table_repl, text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<img\b[^>]*>", _img_repl, text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(?:p|div|li|tr|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
        text = sub(r"<.*?>", "", text)
        text = html.unescape(text)
        text = text.replace("\xa0", " ")
        text = sub(r"[ \t]+", " ", text)
        text = sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _get(self, path: str, params: dict = None) -> dict | list:
        """공통 GET 요청"""
        url = f"{self.BASE_URL}/{path}"
        p = {"key": self.api_key}
        if params:
            p.update(params)
        resp = self._session().get(url, params=p, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── 공개 API ─────────────────────────────────────────────────

    def get_code_list(self) -> list[dict]:
        """
        전체 건설기준 목록 조회 (KDS, KCS 요약 정보) — 결과를 1시간 캐시
        반환: [{"codeType": "KCS", "codeNo": "114010", "name": "..."}]
        """
        global _code_list_cache, _code_list_ts
        with _cache_lock:
            if _code_list_cache is not None and time.time() - _code_list_ts < _CODE_LIST_TTL:
                return _code_list_cache
        data = self._get("CodeList")
        result = data if isinstance(data, list) else []
        with _cache_lock:
            _code_list_cache = result
            _code_list_ts = time.time()
        return result

    def get_code_detail(self, code_type: str, code_no: str) -> dict | None:
        """
        특정 코드 상세 내용 조회
        :param code_type: "KDS" 또는 "KCS"
        :param code_no:   코드 번호 (예: "114010")
        반환: {"name": "...", "version": "...", "list": [{"title": ..., "contents": ...}]}
        """
        data = self._get(f"CodeViewer/{code_type}/{code_no}")
        if not data:
            return None
        item = data[0] if isinstance(data, list) else data
        # contents의 HTML 태그 정제
        for section in item.get("list", []):
            section["contents"] = self._clean_html(section.get("contents", ""))
        return item
