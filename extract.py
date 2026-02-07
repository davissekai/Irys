import os
import sys
import json
import re

# Disable MKL-DNN to avoid oneDNN compatibility issues on Windows
os.environ['FLAGS_use_mkldnn'] = '0'

from paddleocr import PPStructure


def parse_text_regions(raw_text):
    """
    Parse the raw text output from PPStructure to extract individual text items
    with their coordinates and content.
    """
    # Pattern to match each text region dict
    pattern = r"\{'text':\s*'([^']*)',\s*'confidence':\s*([\d.]+),\s*'text_region':\s*\[\[([^\]]+)\]"
    
    items = []
    for match in re.finditer(pattern, raw_text):
        text = match.group(1)
        confidence = float(match.group(2))
        coords_str = match.group(3)
        
        # Parse first coordinate pair (top-left corner)
        coords = [float(x.strip()) for x in coords_str.split(',')]
        x, y = coords[0], coords[1]
        
        items.append({
            'text': text,
            'confidence': confidence,
            'x': x,
            'y': y
        })
    
    return items


def group_into_rows(items, y_tolerance=25):
    """
    Group text items into rows based on their Y coordinate.
    Items within y_tolerance pixels are considered same row.
    Uses average Y of current row for comparison (handles slanted handwriting).
    """
    if not items:
        return []
    
    # Sort by Y coordinate
    sorted_items = sorted(items, key=lambda x: x['y'])
    
    rows = []
    current_row = [sorted_items[0]]
    
    for item in sorted_items[1:]:
        # Compare to average Y of current row (handles slanted handwriting)
        avg_y = sum(i['y'] for i in current_row) / len(current_row)
        if abs(item['y'] - avg_y) <= y_tolerance:
            current_row.append(item)
        else:
            # Sort row by X coordinate and add
            rows.append(sorted(current_row, key=lambda x: x['x']))
            current_row = [item]
    
    # Don't forget the last row
    rows.append(sorted(current_row, key=lambda x: x['x']))
    
    return rows


def rows_to_table(rows, columns=None):
    """
    Convert grouped rows to a table structure.
    Uses header X positions to create column zones for proper cell mapping.
    """
    if not rows:
        return {'headers': [], 'rows': []}
    
    # If columns are specified, find the first row with enough items to be a header
    # This skips title rows like "STUDENT WALK-INS" that appear above the table
    header_row_idx = 0
    expected_cols = len(columns) if columns else 3
    
    if columns:
        for i, row in enumerate(rows):
            # Valid header row should have items close to expected column count
            if len(row) >= expected_cols - 1:
                header_row_idx = i
                break
            # Also check if row contains column header text
            row_text = ' '.join([item['text'].upper() for item in row])
            if any(col.upper() in row_text for col in columns[:2]):
                header_row_idx = i
                break
    
    header_items = rows[header_row_idx]
    if columns:
        headers = columns
    else:
        headers = [item['text'] for item in header_items]
    
    # Create column zones based on header X positions
    # First zone starts at x=0, each subsequent zone starts at midpoint between headers
    column_zones = []
    num_headers = len(header_items)
    for i, item in enumerate(header_items):
        # First column starts at 0
        if i == 0:
            start_x = 0
        else:
            # Midpoint between this header and previous
            prev_x = header_items[i - 1]['x']
            start_x = (prev_x + item['x']) / 2
        
        # End at midpoint to next header, or infinity for last column
        if i + 1 < num_headers:
            end_x = (item['x'] + header_items[i + 1]['x']) / 2
        else:
            end_x = 99999  # Large number instead of infinity (JSON compatible)
        
        column_zones.append({
            'header': headers[i] if i < len(headers) else f'col_{i}',
            'start_x': start_x,
            'end_x': end_x
        })
    
    # Build table rows using column zones (skip title rows and header row)
    data_rows = rows[header_row_idx + 1:]
    table_rows = []
    
    for row in data_rows:
        row_data = {zone['header']: '' for zone in column_zones}
        
        for item in row:
            # Find which column zone this item belongs to
            for zone in column_zones:
                if zone['start_x'] <= item['x'] < zone['end_x']:
                    # Append with separator if already has content
                    if row_data[zone['header']]:
                        row_data[zone['header']] += ' ' + item['text']
                    else:
                        row_data[zone['header']] = item['text']
                    break
        
        table_rows.append(row_data)
    
    return {
        'headers': headers,
        'rows': table_rows,
        'column_zones': column_zones
    }


def extract_table(image_path, columns=None):
    """
    Extracts table data from the given image using PaddleOCR PPStructure.
    Falls back to basic OCR if PPStructure returns no results.
    Returns structured JSON with parsed table.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return None

    print(f"Processing {image_path}...")
    
    all_items = []
    
    # Try PPStructure first (for complex documents)
    try:
        engine = PPStructure(
            show_log=False,
            use_gpu=False
        )
        result = engine(image_path)
        
        for region in result:
            res = region.get('res', [])
            if isinstance(res, list):
                for r in res:
                    if isinstance(r, dict):
                        raw_text = str(r)
                        items = parse_text_regions(raw_text)
                        all_items.extend(items)
            elif isinstance(res, str):
                items = parse_text_regions(res)
                all_items.extend(items)
            
            text_field = region.get('text', '')
            if text_field:
                items = parse_text_regions(text_field)
                all_items.extend(items)
    except Exception as e:
        print(f"PPStructure failed: {e}")
    
    # Fallback: If PPStructure found nothing, try basic OCR
    if not all_items:
        print("PPStructure returned no items. Trying basic OCR fallback...")
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_gpu=False, show_log=False)
            ocr_result = ocr.ocr(image_path)
            
            for line in ocr_result:
                if line:
                    for item in line:
                        bbox, (text, confidence) = item
                        # Use top-left corner for x, y
                        x = bbox[0][0]
                        y = bbox[0][1]
                        all_items.append({
                            'text': text,
                            'confidence': confidence,
                            'x': x,
                            'y': y
                        })
        except Exception as e:
            print(f"Basic OCR fallback failed: {e}")
    
    # Group into rows and convert to table
    rows = group_into_rows(all_items)
    table = rows_to_table(rows, columns)
    
    return {
        'table': table,
        'raw_items': all_items,
        'row_count': len(table['rows']),
        'column_count': len(table['headers'])
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <image_path> [col1,col2,col3,...]")
        sys.exit(1)

    image_path = sys.argv[1]
    
    # Optional: custom column names
    columns = None
    if len(sys.argv) >= 3:
        columns = [c.strip() for c in sys.argv[2].split(',')]
    
    data = extract_table(image_path, columns)
    
    if data and data['row_count'] > 0:
        # Save to file
        basename = os.path.splitext(os.path.basename(image_path))[0]
        output_file = f"{basename}_output.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"[OK] Extraction complete. Found {data['row_count']} rows, {data['column_count']} columns.")
        print(f"Saved to {output_file}")
        
        # Preview
        print("\nHeaders:", data['table']['headers'])
        if data['table']['rows']:
            print("First row:", data['table']['rows'][0])
    else:
        print("[ERROR] No table data extracted.")
