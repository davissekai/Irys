"""
Database utilities for Irys.
Handles dynamic table creation and data insertion into Supabase PostgreSQL.
"""

import os
import re
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, Column, String, inspect, text
from dotenv import load_dotenv

load_dotenv(override=True)

SYSTEM_EXPORT_ID_COL = "_irys_export_id"
SYSTEM_EXPORTED_AT_COL = "_irys_exported_at"


def _normalize_database_url(raw_url: str) -> str:
    """
    Normalize common copy/paste mistakes in DATABASE_URL.
    Handles accidental wrapping quotes and quoted host fragments.
    """
    url = (raw_url or "").strip()
    if not url:
        return url

    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    # Example bad fragment: @\"db.project.supabase.co\" or @"db..."
    url = url.replace('@\\"', "@").replace('\\"', "")
    url = url.replace("@'", "@").replace("'", "")
    url = url.replace('@"', "@").replace('"', "")
    return url

def get_engine():
    database_url = _normalize_database_url(os.environ.get("DATABASE_URL"))
    if database_url and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables.")
    return create_engine(database_url)

def sanitize_name(name):
    """Sanitize names for PostgreSQL table/column names."""
    # Replace spaces and special chars with underscores, lower case
    s = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    # Remove leading numbers
    s = re.sub(r'^[0-9]+', '', s)
    # Remove consecutive underscores
    s = re.sub(r'_+', '_', s)
    return s.strip('_')


def _collect_headers(rows: list) -> list:
    seen = set()
    ordered_headers = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key == "__meta":
                continue
            sanitized = sanitize_name(str(key))
            if not sanitized or sanitized in seen:
                continue
            seen.add(sanitized)
            ordered_headers.append(sanitized)
    return ordered_headers

def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def save_to_db(event_name: str, rows: list, export_id: str = None):
    """
    Saves the provided rows to a table named after the event.
    Creates the table if it doesn't exist.
    """
    if not rows:
        return {"success": True, "message": "No rows to save."}

    table_name = sanitize_name(event_name)
    if not table_name:
        table_name = "unnamed_event"

    engine = get_engine()
    metadata = MetaData()

    headers = _collect_headers(rows)
    if not headers:
        return {"success": True, "message": "No usable data columns found in rows."}
    export_id = (export_id or "").strip() or None
    if not export_id:
        raise ValueError("export_id is required.")
    exported_at = datetime.now(timezone.utc).isoformat()

    # Check if table exists
    inspector = inspect(engine)
    system_columns = [SYSTEM_EXPORT_ID_COL, SYSTEM_EXPORTED_AT_COL]
    all_columns = headers + [c for c in system_columns if c not in headers]
    
    # Keep dynamic per-event tables for MVP.
    with engine.begin() as conn:
        if not inspector.has_table(table_name):
            print(f"[DB] Creating table: {table_name}")
            cols = [Column(h, String) for h in all_columns]
            Table(table_name, metadata, *cols)
            metadata.create_all(engine)
            existing_cols = set(all_columns)
        else:
            # Schema Evolution: Check for missing columns
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            for col_name in all_columns:
                if col_name not in existing_cols:
                    print(f"[DB] Adding missing column: {col_name} to {table_name}")
                    conn.execute(text(f'ALTER TABLE {_quote_ident(table_name)} ADD COLUMN {_quote_ident(col_name)} TEXT'))
                    existing_cols.add(col_name)

        # Prepare batch insert
        clean_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            clean_row = {}
            for col in all_columns:
                clean_row[col] = None
            for key, value in row.items():
                if key == "__meta":
                    continue
                sanitized_key = sanitize_name(str(key))
                if sanitized_key and sanitized_key in clean_row:
                    clean_row[sanitized_key] = None if value is None else str(value)
            clean_row[SYSTEM_EXPORT_ID_COL] = export_id
            clean_row[SYSTEM_EXPORTED_AT_COL] = exported_at
            clean_rows.append(clean_row)
            
        if clean_rows:
            cols_str = ", ".join([_quote_ident(c) for c in all_columns])
            vals_str = ", ".join([f":{c}" for c in all_columns])
            stmt = text(f"INSERT INTO {_quote_ident(table_name)} ({cols_str}) VALUES ({vals_str})")
            
            # SQLAlchemy handles list of dicts as a batch insert
            conn.execute(stmt, clean_rows)

    return {
        "success": True,
        "message": f"Successfully exported {len(rows)} rows to Supabase table '{table_name}'.",
        "table_name": table_name,
        "export_id": export_id,
        "rows_inserted": len(clean_rows),
    }


def list_exports(event_name: str):
    table_name = sanitize_name(event_name)
    if not table_name:
        raise ValueError("Invalid event name.")

    engine = get_engine()
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return []

    with engine.begin() as conn:
        stmt = text(
            f"""
            SELECT
                {_quote_ident(SYSTEM_EXPORT_ID_COL)} AS export_id,
                MIN({_quote_ident(SYSTEM_EXPORTED_AT_COL)}) AS exported_at,
                COUNT(*) AS row_count
            FROM {_quote_ident(table_name)}
            WHERE {_quote_ident(SYSTEM_EXPORT_ID_COL)} IS NOT NULL
            GROUP BY {_quote_ident(SYSTEM_EXPORT_ID_COL)}
            ORDER BY exported_at DESC
            """
        )
        result = conn.execute(stmt).mappings().all()

    return [
        {
            "export_id": row.get("export_id"),
            "exported_at": row.get("exported_at"),
            "row_count": int(row.get("row_count", 0)),
        }
        for row in result
        if row.get("export_id")
    ]


def get_export_rows(event_name: str, export_id: str):
    table_name = sanitize_name(event_name)
    if not table_name:
        raise ValueError("Invalid event name.")
    if not export_id or not str(export_id).strip():
        raise ValueError("Invalid export_id.")

    engine = get_engine()
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return []

    column_names = [c["name"] for c in inspector.get_columns(table_name)]
    visible_columns = [
        c for c in column_names
        if c not in {SYSTEM_EXPORT_ID_COL, SYSTEM_EXPORTED_AT_COL}
    ]
    if not visible_columns:
        return []

    cols_sql = ", ".join(_quote_ident(c) for c in visible_columns)
    stmt = text(
        f"""
        SELECT {cols_sql}
        FROM {_quote_ident(table_name)}
        WHERE {_quote_ident(SYSTEM_EXPORT_ID_COL)} = :export_id
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(stmt, {"export_id": export_id}).mappings().all()

    return [dict(row) for row in rows]

if __name__ == "__main__":
    # Test
    test_rows = [
        {"Name": "Test User", "Value": "123"},
        {"Name": "Another User", "Value": "456"}
    ]
    print(save_to_db("Test Event", test_rows))
