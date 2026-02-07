"""
Google Document AI extraction module for Irys.
Replaces PaddleOCR with Document AI Form Parser for better table extraction.
"""

import os
import json
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions


def extract_table_docai(
    image_path: str,
    columns: list = None,
    project_id: str = None,
    location: str = "us",  # or "eu"
    processor_id: str = None,
):
    """
    Extract table data from an image using Google Document AI Form Parser.
    
    Args:
        image_path: Path to the image file
        columns: List of expected column names (used for output formatting)
        project_id: GCP project ID
        location: Processor location (us or eu)
        processor_id: Document AI processor ID
    
    Returns:
        dict with table data
    """
    # Get config from environment if not provided
    project_id = project_id or os.environ.get("GCP_PROJECT_ID")
    processor_id = processor_id or os.environ.get("DOCAI_PROCESSOR_ID")
    
    if not project_id or not processor_id:
        raise ValueError(
            "Missing GCP_PROJECT_ID or DOCAI_PROCESSOR_ID. "
            "Set these environment variables or pass them as arguments."
        )
    
    # Set up the client
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    
    # Build the processor name
    processor_name = client.processor_path(project_id, location, processor_id)
    
    # Read the image file
    with open(image_path, "rb") as f:
        image_content = f.read()
    
    # Determine MIME type
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    mime_type = mime_types.get(ext, "image/jpeg")
    
    # Create the document
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    
    # Process the document
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
    result = client.process_document(request=request)
    document = result.document
    
    # Extract tables from the document
    tables = []
    for page in document.pages:
        for table in page.tables:
            extracted_table = extract_table_from_page(document, table)
            tables.append(extracted_table)
    
    # If no tables found, try to extract text and organize it
    if not tables:
        # Fallback: extract all text blocks
        all_text = document.text
        return {
            "table": {
                "headers": columns or [],
                "rows": [],
            },
            "raw_text": all_text,
            "row_count": 0,
            "column_count": len(columns) if columns else 0,
            "error": "No tables detected in the document"
        }
    
    # Use the first (main) table
    main_table = tables[0]
    
    # Intelligent column mapping using LLM (if columns specified)
    if columns:
        from llm_mapper import map_columns_with_llm, filter_table_by_columns
        
        extracted_headers = main_table.get("headers", [])
        print(f"[DocAI] Extracted headers: {extracted_headers}")
        print(f"[DocAI] User wants: {columns}")
        
        # Use LLM to find best matches
        column_mapping = map_columns_with_llm(extracted_headers, columns)
        print(f"[DocAI] Column mapping: {column_mapping}")
        
        # Filter table to only include desired columns
        main_table = filter_table_by_columns(main_table, column_mapping)
        
    # Unzip rows that were merged by DocAI
    main_table = unzip_rows(main_table)
    
    return {
        "table": main_table,
        "row_count": len(main_table.get("rows", [])),
        "column_count": len(main_table.get("headers", [])),
    }


def extract_table_from_page(document, table):
    """Extract table data from a Document AI table object."""
    headers = []
    rows = []
    
    # Extract header row
    if table.header_rows:
        for cell in table.header_rows[0].cells:
            header_text = get_cell_text(document, cell)
            headers.append(header_text.strip())
    
    # Extract body rows
    for row in table.body_rows:
        row_data = {}
        for i, cell in enumerate(row.cells):
            cell_text = get_cell_text(document, cell)
            # Use header name if available, otherwise use index
            col_name = headers[i] if i < len(headers) else f"col_{i}"
            row_data[col_name] = cell_text.strip()
        rows.append(row_data)
    
    return {
        "headers": headers,
        "rows": rows,
    }


def get_cell_text(document, cell):
    """Get text content from a table cell."""
    text = ""
    for segment in cell.layout.text_anchor.text_segments:
        start = int(segment.start_index) if segment.start_index else 0
        end = int(segment.end_index)
        text += document.text[start:end]
    return text


def remap_columns(table, target_columns):
    """
    Try to remap extracted columns to target column names.
    Uses fuzzy matching to handle OCR variations.
    """
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    
    # Simple mapping: if header count matches, use target columns
    if len(headers) == len(target_columns):
        new_rows = []
        for row in rows:
            new_row = {}
            for i, col in enumerate(target_columns):
                old_key = headers[i] if i < len(headers) else f"col_{i}"
                new_row[col] = row.get(old_key, "")
            new_rows.append(new_row)
        return {
            "headers": target_columns,
            "rows": new_rows,
        }
    
    # otherwise return as-is
    return table


def unzip_rows(table):
    """
    Post-process table rows to split 'merged' rows.
    Document AI sometimes groups distinct rows into one if they are close,
    separating values with newlines.
    
    Logic: 
    1. Determine target row count (anchor on 'NO.' column or use majority vote).
    2. Split each column's value into parts.
    3. Distribute parts into new rows, handling mismatches gracefully.
    """
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    new_rows = []
    
    # Identify the 'Number' column to use as anchor
    # Common variations: "NO.", "No.", "No", "#"
    no_col_keys = [h for h in headers if h.upper().replace('.', '').strip() in ['NO', 'NR', '#']]
    anchor_col = no_col_keys[0] if no_col_keys else None
    
    for row in rows:
        # Split each cell by newline
        split_cells = {k: v.split('\n') if v else [''] for k, v in row.items()}
        
        # Determine target number of rows to unzip into
        counts = [len(parts) for k, parts in split_cells.items() if len(parts) > 1]
        
        if not counts:
            new_rows.append(row)
            continue
            
        target_count = 1
        
        # Strategy 1: Anchor on "NO." column if valid
        if anchor_col and anchor_col in split_cells and len(split_cells[anchor_col]) > 1:
            target_count = len(split_cells[anchor_col])
        else:
            # Strategy 2: Majority vote (mode) of splits
            from collections import Counter
            if counts:
                target_count = Counter(counts).most_common(1)[0][0]
        
        if target_count <= 1:
            new_rows.append(row)
            continue
            
        # Perform unzip
        current_expansion = []
        for i in range(target_count):
            new_row = {}
            for col, parts in split_cells.items():
                num_parts = len(parts)
                
                if num_parts == 1:
                    # Single value: apply to all (duplicate) - often accurate for shared data
                    # or it could be empty which is fine to duplicate
                    new_row[col] = parts[0].strip()
                    
                elif num_parts == target_count:
                    # Perfect match
                    new_row[col] = parts[i].strip()
                    
                elif num_parts > target_count:
                    # More values than rows (e.g. 3 lines for 2 rows).
                    # Strategy: Distribute 1:1 for first N-1 rows, then dump rest in last row
                    if i < target_count - 1:
                        new_row[col] = parts[i].strip()
                    else:
                        # Join all remaining parts
                        new_row[col] = " ".join(p.strip() for p in parts[i:])
                        
                else: 
                    # Fewer values than rows (but > 1)
                    # Strategy: Fill sequentially, then empty?
                    if i < num_parts:
                        new_row[col] = parts[i].strip()
                    else:
                        new_row[col] = ""
                        
            current_expansion.append(new_row)
        
        new_rows.extend(current_expansion)
            
    return {
        "headers": headers,
        "rows": new_rows
    }


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_docai.py <image_path> [columns]")
        print("Example: python extract_docai.py register.jpg 'Name,Level,Course,Contact'")
        print("\nRequired environment variables:")
        print("  GCP_PROJECT_ID: Your Google Cloud project ID")
        print("  DOCAI_PROCESSOR_ID: Your Document AI processor ID")
        print("  GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON")
        sys.exit(1)
    
    image_path = sys.argv[1]
    columns = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    
    print(f"Processing {image_path}...")
    
    try:
        result = extract_table_docai(image_path, columns)
        
        # Save output
        output_path = image_path.rsplit(".", 1)[0] + "_docai_output.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"[OK] Extraction complete. Found {result['row_count']} rows, {result['column_count']} columns.")
        print(f"Saved to {output_path}")
        
        if result.get("table", {}).get("rows"):
            print(f"\nHeaders: {result['table']['headers']}")
            print(f"First row: {result['table']['rows'][0]}")
        elif result.get("error"):
            print(f"\nWarning: {result['error']}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
