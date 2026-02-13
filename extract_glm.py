"""
GLM-OCR extraction module for Irys.
Calls Z.AI GLM-OCR layout parsing API and converts markdown table output
to Irys' standard table JSON format.
"""

import base64
import html
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional

import requests


DEFAULT_GLM_URL = "https://api.z.ai/api/paas/v4/layout_parsing"
DEFAULT_GLM_MODEL = "glm-ocr"


def warmup() -> Dict[str, Any]:
    """
    Validate config and readiness for GLM calls.
    """
    api_key = _clean_secret(os.environ.get("GLM_OCR_API_KEY"))
    if not api_key:
        raise ValueError("Missing GLM_OCR_API_KEY.")
    return {"ok": True, "provider": "glm"}


def _clean_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    # Remove accidental whitespace/newlines from copied API keys.
    return "".join(value.split())


def _to_data_uri(file_path: str, mime_type: Optional[str] = None) -> str:
    if not mime_type:
        guessed, _ = mimetypes.guess_type(file_path)
        mime_type = guessed
    mime_type = mime_type or "image/jpeg"
    with open(file_path, "rb") as f:
        raw = f.read()
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _is_separator_row(cells: List[str]) -> bool:
    if not cells:
        return False
    for cell in cells:
        compact = cell.replace(":", "").replace("-", "").strip()
        if compact:
            return False
    return True


def _split_md_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _parse_markdown_tables(markdown: str) -> List[Dict[str, Any]]:
    lines = [ln.rstrip() for ln in markdown.splitlines()]
    tables: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines) - 1:
        header_line = lines[i]
        sep_line = lines[i + 1]
        if "|" not in header_line or "|" not in sep_line:
            i += 1
            continue

        headers = _split_md_row(header_line)
        sep_cells = _split_md_row(sep_line)
        if len(headers) < 2 or not _is_separator_row(sep_cells):
            i += 1
            continue

        rows: List[Dict[str, str]] = []
        j = i + 2
        while j < len(lines):
            row_line = lines[j]
            if "|" not in row_line:
                break
            row_cells = _split_md_row(row_line)
            if len(row_cells) < 2:
                break
            if len(row_cells) < len(headers):
                row_cells += [""] * (len(headers) - len(row_cells))
            row_cells = row_cells[: len(headers)]
            row = {headers[k]: row_cells[k] for k in range(len(headers))}
            rows.append(row)
            j += 1

        if rows:
            tables.append({"headers": headers, "rows": rows})
        i = j
    return tables


def _clean_html_cell(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text, flags=re.IGNORECASE)
    return html.unescape(text).strip()


def _parse_html_tables(content: str) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for table_match in re.finditer(r"<table[^>]*>(.*?)</table>", content, flags=re.IGNORECASE | re.DOTALL):
        table_html = table_match.group(1)
        row_html_list = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL)
        if not row_html_list:
            continue

        headers: List[str] = []
        rows: List[Dict[str, str]] = []

        for idx, row_html in enumerate(row_html_list):
            th_cells = re.findall(r"<th[^>]*>(.*?)</th>", row_html, flags=re.IGNORECASE | re.DOTALL)
            td_cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)

            if idx == 0 and th_cells:
                headers = [_clean_html_cell(c) for c in th_cells]
                continue

            if td_cells:
                cells = [_clean_html_cell(c) for c in td_cells]
                if not headers:
                    headers = [f"col_{i}" for i in range(len(cells))]
                if len(cells) < len(headers):
                    cells += [""] * (len(headers) - len(cells))
                cells = cells[: len(headers)]
                row = {headers[i]: cells[i] for i in range(len(headers))}
                # Skip fully empty rows commonly appended at bottom of forms.
                if any(v.strip() for v in row.values()):
                    rows.append(row)

        if headers and rows:
            tables.append({"headers": headers, "rows": rows})

    return tables


def _collect_markdown_like_text(node: Any, out: List[str]) -> None:
    if isinstance(node, str):
        if (("|" in node and "\n" in node) or ("<table" in node.lower())):
            out.append(node)
        return
    if isinstance(node, list):
        for item in node:
            _collect_markdown_like_text(item, out)
        return
    if isinstance(node, dict):
        for value in node.values():
            _collect_markdown_like_text(value, out)


def _pick_best_table(tables: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not tables:
        return None
    return max(tables, key=lambda t: (len(t.get("rows", [])), len(t.get("headers", []))))


def extract_table_glm(
    image_path: str,
    columns: Optional[List[str]] = None,
    mime_type: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = _clean_secret(api_key or os.environ.get("GLM_OCR_API_KEY"))
    base_url = base_url or os.environ.get("GLM_OCR_BASE_URL", DEFAULT_GLM_URL)
    model = model or os.environ.get("GLM_OCR_MODEL", DEFAULT_GLM_MODEL)

    if not api_key:
        raise ValueError("Missing GLM_OCR_API_KEY.")
    if not os.path.exists(image_path):
        raise ValueError(f"Image not found: {image_path}")

    payload = {
        "model": model,
        "file": _to_data_uri(image_path, mime_type=mime_type),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(base_url, headers=headers, json=payload, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"{resp.status_code} {resp.text}")
    data = resp.json()

    markdown_candidates: List[str] = []
    _collect_markdown_like_text(data, markdown_candidates)

    parsed_tables: List[Dict[str, Any]] = []
    for md in markdown_candidates:
        parsed_tables.extend(_parse_markdown_tables(md))
        parsed_tables.extend(_parse_html_tables(md))

    table = _pick_best_table(parsed_tables)
    if not table:
        return {
            "table": {"headers": columns or [], "rows": []},
            "row_count": 0,
            "column_count": len(columns or []),
            "error": "No markdown table found in GLM response.",
            "raw_response": data,
        }

    if columns:
        from llm_mapper import map_columns_with_llm, filter_table_by_columns

        mapping = map_columns_with_llm(table.get("headers", []), columns)
        table = filter_table_by_columns(table, mapping)

    return {
        "table": table,
        "row_count": len(table.get("rows", [])),
        "column_count": len(table.get("headers", [])),
        "raw_response": data,
    }
