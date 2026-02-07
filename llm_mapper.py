"""
LLM-based intelligent column mapping for Irys.
Uses OpenRouter API with StepFun 3.5 Flash for semantic column matching.
"""

import os
import json
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "stepfun/step-3.5-flash")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def map_columns_with_llm(extracted_headers: list, desired_columns: list) -> dict:
    """
    Uses LLM to intelligently map extracted column headers to user-desired columns.
    
    Args:
        extracted_headers: Column headers found in the document (e.g., ["DATE", "NAME", "ID", "TIME-IN"])
        desired_columns: Columns the user wants (e.g., ["Name", "ID"])
    
    Returns:
        A mapping dict: {desired_col: extracted_col} or {desired_col: None} if no match
    """
    if not OPENROUTER_API_KEY:
        print("[LLM Mapper] No API key found, falling back to exact matching")
        return _fallback_exact_match(extracted_headers, desired_columns)
    
    prompt = f"""You are a data extraction assistant. Your task is to match user-requested column names to columns found in a document.

Document contains these columns: {json.dumps(extracted_headers)}
User wants these columns: {json.dumps(desired_columns)}

For each column the user wants, find the best matching column from the document.
Consider semantic similarity (e.g., "Name" matches "NAME" or "STUDENT NAME" or "FULL NAME").
If there's no reasonable match, use null.

Return ONLY a valid JSON object mapping each desired column to its best match from the document.
CRITICAL: The keys in your JSON MUST match the user's columns EXACTLY as provided above (including case).
Example output: {{"Name": "NAME", "ID": "STUDENT_ID", "Phone": null}}

Your response (JSON only, no markdown, no explanation):"""

    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://irys.local",
                "X-Title": "Irys Column Mapper"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Clean up potential markdown formatting
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        mapping = json.loads(content)
        print(f"[LLM Mapper] Generated mapping: {mapping}")
        return mapping
        
    except Exception as e:
        print(f"[LLM Mapper] Error: {e}, falling back to exact matching")
        return _fallback_exact_match(extracted_headers, desired_columns)


def _fallback_exact_match(extracted_headers: list, desired_columns: list) -> dict:
    """Case-insensitive fallback matching with basic semantic hints."""

    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _score_semantic_match(desired: str, extracted: str) -> int:
        desired_n = _normalize(desired)
        extracted_n = _normalize(extracted)
        if not desired_n or not extracted_n:
            return 0

        aliases = {
            "name": {"name", "student", "attendee", "participant", "full name"},
            "id": {"id", "index", "student id", "matric", "number"},
            "contact": {"contact", "phone", "mobile", "tel", "telephone"},
            "level": {"level", "class", "year", "stage"},
            "course": {"course", "program", "programme", "major", "department"},
        }

        score = 0
        if desired_n == extracted_n:
            score += 100
        if desired_n in extracted_n or extracted_n in desired_n:
            score += 40

        for key, words in aliases.items():
            if key in desired_n:
                for word in words:
                    if word in extracted_n:
                        score += 25
        return score

    mapping = {}
    cleaned_headers = [h for h in extracted_headers if isinstance(h, str) and h.strip()]
    extracted_lookup = {_normalize(h): h for h in cleaned_headers if _normalize(h)}

    for col in desired_columns:
        col_norm = _normalize(col)
        if not col_norm:
            mapping[col] = None
            continue

        if col_norm in extracted_lookup:
            mapping[col] = extracted_lookup[col_norm]
            continue

        best_match = None
        best_score = 0
        for header in cleaned_headers:
            score = _score_semantic_match(col, header)
            if score > best_score:
                best_score = score
                best_match = header

        mapping[col] = best_match if best_score >= 25 else None

    return mapping


def filter_table_by_columns(table: dict, column_mapping: dict) -> dict:
    """
    Filters a table to only include the mapped columns.
    
    Args:
        table: {"headers": [...], "rows": [...]}
        column_mapping: {desired_col: extracted_col}
    
    Returns:
        Filtered table with only the desired columns
    """
    desired_columns = list(column_mapping.keys())
    rows = table.get("rows", [])

    def _normalize_text(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _get_row_value(row: dict, key: str) -> str:
        if key in row:
            return str(row[key]).strip()
        key_lower = key.lower()
        for row_key, row_value in row.items():
            if isinstance(row_key, str) and row_key.lower() == key_lower:
                return str(row_value).strip()
        return ""

    def _column_values(header: str) -> list:
        return [_get_row_value(row, header) for row in rows]

    def _non_empty_ratio(header: str) -> float:
        values = _column_values(header)
        if not values:
            return 0.0
        non_empty = sum(1 for value in values if value)
        return non_empty / len(values)

    def _id_score(header: str) -> float:
        values = _column_values(header)
        if not values:
            return -999.0

        non_empty_values = [v for v in values if v]
        if not non_empty_values:
            return -999.0

        id_like = 0
        time_like = 0
        date_like = 0
        word_heavy = 0

        for value in non_empty_values:
            compact = re.sub(r"[\s\-_/]", "", value)
            if re.fullmatch(r"[A-Za-z]{0,3}\d{4,}", compact):
                id_like += 1
            if re.fullmatch(r"\d{1,2}:\d{2}([ap]m)?", value.lower()):
                time_like += 1
            if re.fullmatch(r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}", value):
                date_like += 1
            if re.search(r"[A-Za-z]{3,}", value):
                word_heavy += 1

        header_norm = _normalize_text(header)
        header_bonus = 0
        if any(tok in header_norm for tok in ["id", "index", "number", "no"]):
            header_bonus += 1.5
        if any(tok in header_norm for tok in ["date", "time", "name", "student"]):
            header_bonus -= 1.0

        total = len(non_empty_values)
        return (id_like * 2.5 - time_like * 2.0 - date_like * 2.0 - word_heavy * 1.0) / total + header_bonus

    available_headers = [
        header for header in table.get("headers", [])
        if isinstance(header, str) and header.strip()
    ]
    used_headers = {mapped for mapped in column_mapping.values() if isinstance(mapped, str) and mapped.strip()}

    # Refine mapping for ID-like columns when header text mapping is weak.
    for desired_col in desired_columns:
        desired_norm = _normalize_text(desired_col)
        is_id_target = desired_norm in {"id", "student id", "index", "number"}
        if not is_id_target:
            continue

        mapped_header = column_mapping.get(desired_col)
        mapping_is_weak = (
            not mapped_header
            or not isinstance(mapped_header, str)
            or _non_empty_ratio(mapped_header) < 0.4
        )
        if not mapping_is_weak:
            continue

        best_header = None
        best_score = -999.0
        for header in available_headers:
            if header in used_headers:
                continue
            score = _id_score(header)
            if score > best_score:
                best_score = score
                best_header = header

        if best_header and best_score > 0:
            column_mapping[desired_col] = best_header
            used_headers.add(best_header)
            print(f"[LLM Mapper] Inferred ID mapping: {desired_col} -> {best_header} (score={best_score:.2f})")
    
    filtered_rows = []
    for row in rows:
        # Create a case-insensitive lookup for the extracted row
        row_lower = {k.lower(): v for k, v in row.items()}
        
        filtered_row = {}
        for desired_col, extracted_col in column_mapping.items():
            if extracted_col:
                # Try exact match first, then case-insensitive
                if extracted_col in row:
                    filtered_row[desired_col] = row[extracted_col]
                elif extracted_col.lower() in row_lower:
                    filtered_row[desired_col] = row_lower[extracted_col.lower()]
                else:
                    filtered_row[desired_col] = ""
            else:
                filtered_row[desired_col] = ""
        filtered_rows.append(filtered_row)

    header_tokens = {
        "name", "student", "id", "index", "no", "number", "date",
        "time in", "time out", "signature", "level", "course", "contact",
        "phone", "experience", "space",
    }
    desired_tokens = {_normalize_text(c) for c in desired_columns if _normalize_text(c)}

    def _is_header_like_row(row: dict) -> bool:
        values = [str(v).strip() for v in row.values() if str(v).strip()]
        if not values:
            return False

        normalized_values = [_normalize_text(v) for v in values]
        if any(any(ch.isdigit() for ch in v) for v in values):
            return False

        header_hits = 0
        for token in normalized_values:
            if token in desired_tokens or token in header_tokens:
                header_hits += 1

        # Conservative heuristic: all populated cells look like headers.
        return header_hits == len(normalized_values)

    while filtered_rows and _is_header_like_row(filtered_rows[0]):
        print(f"[LLM Mapper] Dropping header-like leading row: {filtered_rows[0]}")
        filtered_rows.pop(0)
    
    return {
        "headers": desired_columns,
        "rows": filtered_rows
    }


# CLI for testing
if __name__ == "__main__":
    # Test the mapping
    extracted = ["DATE", "NAME", "ID", "TIME-IN", "SIGNATURE", "TIME-OUT"]
    desired = ["Name", "ID"]
    
    print(f"Extracted headers: {extracted}")
    print(f"Desired columns: {desired}")
    print()
    
    mapping = map_columns_with_llm(extracted, desired)
    print(f"\nFinal mapping: {mapping}")
    
    # Test filtering
    test_table = {
        "headers": extracted,
        "rows": [
            {"DATE": "04/02/26", "NAME": "John Doe", "ID": "12345", "TIME-IN": "9:00", "SIGNATURE": "JD", "TIME-OUT": ""},
            {"DATE": "04/02/26", "NAME": "Jane Smith", "ID": "67890", "TIME-IN": "9:15", "SIGNATURE": "JS", "TIME-OUT": ""},
        ]
    }
    
    filtered = filter_table_by_columns(test_table, mapping)
    print(f"\nFiltered table:")
    print(json.dumps(filtered, indent=2))
