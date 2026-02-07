from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import shutil
import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
import db_utils

# Load environment variables from .env file
load_dotenv()

# Use Document AI for extraction (falls back to PaddleOCR if not configured)
USE_DOCAI = os.environ.get("GCP_PROJECT_ID") and os.environ.get("DOCAI_PROCESSOR_ID")

if USE_DOCAI:
    import extract_docai as extractor
    print("[API] Using Google Document AI for extraction")
else:
    import extract as extractor
    print("[API] Using PaddleOCR for extraction (Document AI not configured)")

app = FastAPI()
EXTRACT_TIMEOUT_SECONDS = float(os.environ.get("EXTRACT_TIMEOUT_SECONDS", "90"))

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ready", "message": "Irys API is live"}

@app.post("/extract")
async def extract_api(
    file: UploadFile = File(...),
    columns: str = Form(...) # Expecting JSON string of column names
):
    temp_filename = f"temp_{file.filename}"
    try:
        # 1. Parse columns
        column_list = json.loads(columns)
        if not isinstance(column_list, list):
            raise HTTPException(status_code=400, detail="columns must be a JSON array of column names")
        
        # 2. Save temp file
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Run Extraction
        print(f"Processing {temp_filename} with columns: {column_list}")

        if USE_DOCAI:
            extraction_fn = lambda: extractor.extract_table_docai(temp_filename, columns=column_list)
        else:
            extraction_fn = lambda: extractor.extract_table(temp_filename, columns=column_list)

        try:
            result = await asyncio.wait_for(
                run_in_threadpool(extraction_fn),
                timeout=EXTRACT_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"Extraction timed out after {EXTRACT_TIMEOUT_SECONDS:.0f}s"
            )
        
        if not result:
             raise HTTPException(status_code=500, detail="Extraction failed to return data")

        # Debug: Print full result
        print("=== EXTRACTION RESULT ===")
        print(f"Row count: {result.get('row_count')}")
        print(f"Headers: {result.get('table', {}).get('headers')}")
        if result.get('table', {}).get('rows'):
            print(f"First row: {result['table']['rows'][0]}")
        else:
            print("No rows extracted!")
        print("=========================")

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception as cleanup_error:
                print(f"Cleanup warning: {cleanup_error}")

@app.post("/export-db")
async def export_db(payload: Dict[str, Any]):
    """
    Expects { "eventName": "...", "rows": [...] }
    Saves data to Supabase PostgreSQL.
    """
    try:
        event_name = payload.get("eventName")
        rows = payload.get("rows")
        
        if not event_name or not rows:
            raise HTTPException(status_code=400, detail="Missing eventName or rows in payload")
            
        print(f"[API] Exporting {len(rows)} rows for event '{event_name}' to DB")
        result = await run_in_threadpool(lambda: db_utils.save_to_db(event_name, rows))
        
        return result
        
    except Exception as e:
        print(f"Export Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
