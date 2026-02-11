"""
Database utilities for Irys.
Handles dynamic table creation and data insertion into Supabase PostgreSQL.
"""

import os
import re
from sqlalchemy import create_engine, MetaData, Table, Column, String, inspect, text
from dotenv import load_dotenv

load_dotenv(override=True)


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

def save_to_db(event_name: str, rows: list):
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
    
    # Check if table exists
    inspector = inspect(engine)
    
    # Keep dynamic per-event tables for MVP.
    with engine.begin() as conn:
        if not inspector.has_table(table_name):
            print(f"[DB] Creating table: {table_name}")
            cols = [Column(h, String) for h in headers]
            Table(table_name, metadata, *cols)
            metadata.create_all(engine)
            existing_cols = set(headers)
        else:
            # Schema Evolution: Check for missing columns
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            for header in headers:
                if header not in existing_cols:
                    print(f"[DB] Adding missing column: {header} to {table_name}")
                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN "{header}" TEXT'))
                    existing_cols.add(header)

        # Prepare batch insert
        clean_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            clean_row = {}
            for col in headers:
                clean_row[col] = None
            for key, value in row.items():
                if key == "__meta":
                    continue
                sanitized_key = sanitize_name(str(key))
                if sanitized_key and sanitized_key in clean_row:
                    clean_row[sanitized_key] = None if value is None else str(value)
            clean_rows.append(clean_row)
            
        if clean_rows:
            all_cols = headers
            cols_str = ", ".join([f'"{c}"' for c in all_cols])
            vals_str = ", ".join([f":{c}" for c in all_cols])
            stmt = text(f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str})")
            
            # SQLAlchemy handles list of dicts as a batch insert
            conn.execute(stmt, clean_rows)
            
    return {"success": True, "message": f"Successfully exported {len(rows)} rows to Supabase table '{table_name}'."}

if __name__ == "__main__":
    # Test
    test_rows = [
        {"Name": "Test User", "Value": "123"},
        {"Name": "Another User", "Value": "456"}
    ]
    print(save_to_db("Test Event", test_rows))
