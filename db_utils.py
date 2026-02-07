"""
Database utilities for Irys.
Handles dynamic table creation and data insertion into Supabase PostgreSQL.
"""

import os
import re
from sqlalchemy import create_engine, MetaData, Table, Column, String, inspect, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in environment variables.")
    return create_engine(DATABASE_URL)

def sanitize_name(name):
    """Sanitize names for PostgreSQL table/column names."""
    # Replace spaces and special chars with underscores, lower case
    s = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    # Remove leading numbers
    s = re.sub(r'^[0-9]+', '', s)
    # Remove consecutive underscores
    s = re.sub(r'_+', '_', s)
    return s.strip('_')

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
    
    # Extract headers from the first row
    sample_row = rows[0]
    headers = [k for k in sample_row.keys() if k != '__meta']
    
    # Check if table exists
    inspector = inspect(engine)
    
    # Create column definitions
    columns = [
        Column('id', String, primary_key=True), # We'll generate a simple one or just omit pk if not needed
    ]
    
    # For MVP, we'll use a simple approach: 
    # If table doesn't exist, create it with String columns for all headers.
    
    with engine.begin() as conn:
        if not inspector.has_table(table_name):
            print(f"[DB] Creating table: {table_name}")
            cols = [Column(sanitize_name(h), String) for h in headers]
            dynamic_table = Table(table_name, metadata, *cols)
            metadata.create_all(engine)
        else:
            # Schema Evolution: Check for missing columns
            existing_cols = [c['name'] for c in inspector.get_columns(table_name)]
            for h in headers:
                sanitized_h = sanitize_name(h)
                if sanitized_h not in existing_cols:
                    print(f"[DB] Adding missing column: {sanitized_h} to {table_name}")
                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN "{sanitized_h}" TEXT'))
        
        # Prepare batch insert
        clean_rows = []
        for row in rows:
            clean_row = {sanitize_name(k): str(v) for k, v in row.items() if k != '__meta'}
            clean_rows.append(clean_row)
            
        if clean_rows:
            # Use the keys from the first row as the template for columns
            # In a batch insert, all rows must have the same keys (filled with None/empty if missing)
            all_cols = list(clean_rows[0].keys())
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
