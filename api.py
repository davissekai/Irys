from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import shutil
import os
import json
import asyncio
import tempfile
from typing import List, Dict, Any
from dotenv import load_dotenv
import db_utils

# Load environment variables from .env file
load_dotenv()

# OCR provider selection
# Supported: auto | docai | glm | paddle
OCR_PROVIDER = os.environ.get("OCR_PROVIDER", "auto").strip().lower()

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
DOCAI_PROCESSOR_ID = os.environ.get("DOCAI_PROCESSOR_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
HAS_DOCAI_CREDS = bool(
    GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS)
)

GLM_OCR_API_KEY = os.environ.get("GLM_OCR_API_KEY")
HAS_GLM = bool(GLM_OCR_API_KEY)

if OCR_PROVIDER == "auto":
    if GCP_PROJECT_ID and DOCAI_PROCESSOR_ID and HAS_DOCAI_CREDS:
        OCR_PROVIDER = "docai"
    elif HAS_GLM:
        OCR_PROVIDER = "glm"
    else:
        OCR_PROVIDER = "paddle"

extractor = None
if OCR_PROVIDER == "docai":
    import extract_docai as extractor
    print("[API] Using Google Document AI for extraction")
elif OCR_PROVIDER == "glm":
    import extract_glm as extractor
    print("[API] Using GLM-OCR API for extraction")
else:
    import extract as extractor
    print("[API] Using PaddleOCR for extraction")

app = FastAPI()
EXTRACT_TIMEOUT_SECONDS = float(os.environ.get("EXTRACT_TIMEOUT_SECONDS", "90"))
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:4174,http://localhost:4174,http://127.0.0.1:4173,http://localhost:4173"
    ).split(",")
    if origin.strip()
]
FRONTEND_ORIGIN_REGEX = os.environ.get("FRONTEND_ORIGIN_REGEX")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=FRONTEND_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ready", "message": "Irys API is live", "ocr_provider": OCR_PROVIDER}

@app.post("/extract")
async def extract_api(
    file: UploadFile = File(...),
    columns: str = Form(...) # Expecting JSON string of column names
):
    fd, temp_filename = tempfile.mkstemp(prefix="irys_", suffix=".upload")
    os.close(fd)
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

        if OCR_PROVIDER == "docai":
            extraction_fn = lambda: extractor.extract_table_docai(temp_filename, columns=column_list)
        elif OCR_PROVIDER == "glm":
            extraction_fn = lambda: extractor.extract_table_glm(
                temp_filename,
                columns=column_list,
                mime_type=file.content_type
            )
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

    except HTTPException:
        raise
    except Exception as e:
        print(f"Export Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
