from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import shutil
import os
import json
import asyncio
import tempfile
from typing import Dict, Any
from uuid import uuid4
from dotenv import load_dotenv
import db_utils

# Load environment variables from .env file
load_dotenv()

# OCR provider (GLM only)
OCR_PROVIDER = "glm"
GLM_OCR_API_KEY = os.environ.get("GLM_OCR_API_KEY")
if not GLM_OCR_API_KEY:
    print("[API] Warning: GLM_OCR_API_KEY is missing.")

import extract_glm as extractor
print("[API] Using GLM-OCR API for extraction")

app = FastAPI()
EXTRACT_TIMEOUT_SECONDS = float(os.environ.get("EXTRACT_TIMEOUT_SECONDS", "90"))
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4174,http://localhost:4174,http://127.0.0.1:4173,http://localhost:4173"
    ).split(",")
    if origin.strip()
]
FRONTEND_ORIGIN_REGEX = os.environ.get("FRONTEND_ORIGIN_REGEX")
AUTO_WARMUP_ON_STARTUP = os.environ.get("AUTO_WARMUP_ON_STARTUP", "1").strip() not in {"0", "false", "False"}

_WARMUP_STATE = {
    "attempted": False,
    "ok": False,
    "error": None,
}

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
    return {
        "status": "ready",
        "message": "Irys API is live",
        "ocr_provider": OCR_PROVIDER,
        "warmup": _WARMUP_STATE,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "ocr_provider": OCR_PROVIDER, "warmup": _WARMUP_STATE}


def _run_extractor_warmup():
    extractor.warmup()


async def _warmup_extractor():
    _WARMUP_STATE["attempted"] = True
    try:
        await run_in_threadpool(_run_extractor_warmup)
        _WARMUP_STATE["ok"] = True
        _WARMUP_STATE["error"] = None
        return {"ok": True, "ocr_provider": OCR_PROVIDER}
    except Exception as e:
        _WARMUP_STATE["ok"] = False
        _WARMUP_STATE["error"] = str(e)
        return {"ok": False, "ocr_provider": OCR_PROVIDER, "error": str(e)}


@app.post("/warmup")
async def warmup():
    return await _warmup_extractor()


@app.on_event("startup")
async def startup_warmup():
    if AUTO_WARMUP_ON_STARTUP:
        result = await _warmup_extractor()
        print(f"[API] Warmup result: {result}")

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

        extraction_fn = lambda: extractor.extract_table_glm(
            temp_filename,
            columns=column_list,
            mime_type=file.content_type
        )

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
        export_id = (payload.get("exportId") or "").strip() or str(uuid4())
        
        if not event_name or not isinstance(rows, list) or len(rows) == 0:
            raise HTTPException(status_code=400, detail="Missing eventName or rows in payload")
            
        print(f"[API] Exporting {len(rows)} rows for event '{event_name}' to DB")
        result = await run_in_threadpool(lambda: db_utils.save_to_db(event_name, rows, export_id=export_id))
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Export Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/exports/{event_name}")
async def list_exports(event_name: str):
    try:
        exports = await run_in_threadpool(lambda: db_utils.list_exports(event_name))
        return {"eventName": event_name, "exports": exports}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"List exports error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/exports/{event_name}/{export_id}")
async def get_export_rows(event_name: str, export_id: str):
    try:
        rows = await run_in_threadpool(lambda: db_utils.get_export_rows(event_name, export_id))
        return {"eventName": event_name, "exportId": export_id, "rowCount": len(rows), "rows": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Get export rows error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
