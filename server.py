"""
AI DDR Builder — Backend API Server
=====================================
FastAPI server that exposes the DDR pipeline as a REST API.

Endpoints:
    POST /api/generate-ddr   — Upload two files, get a DDR report back.
    GET  /api/health         — Health check.

Usage:
    python server.py
    # or
    uvicorn server:app --reload --port 8000
"""

import json
import logging
import os
import sys
import tempfile
import shutil
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Local imports ──────────────────────────────────────────────────────
from src.document_loader import load_document
from src.extractor import extract_structured_data
from src.merger import merge_extractions
from src.reasoning_engine import generate_ddr_reasoning
from src.ddr_generator import generate_final_report
from src.validator import validate_ddr

# ── Setup ──────────────────────────────────────────────────────────────
load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ai_ddr_builder.server")

# ── FastAPI App ────────────────────────────────────────────────────────
app = FastAPI(
    title="AI DDR Builder API",
    description="Convert inspection & thermal reports into Detailed Diagnostic Reports.",
    version="1.0.0",
)

# CORS — allow the Vite dev server (port 5173) and any localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend build (if it exists) ───────────────────────────────
_FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(_FRONTEND_DIST / "index.html"))


# ── Response schema ────────────────────────────────────────────────────

class DDRResponse(BaseModel):
    ddr_report: str
    extracted_data: dict
    conflicts: list
    validation_warnings: list


# ── API Endpoints ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Simple health check."""
    api_key = os.getenv("GEMINI_API_KEY")
    return {
        "status": "ok",
        "api_key_set": bool(api_key),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    }


@app.post("/api/generate-ddr", response_model=DDRResponse)
async def generate_ddr(
    inspection_file: UploadFile = File(..., description="Inspection Report (PDF or TXT)"),
    thermal_file: UploadFile = File(..., description="Thermal Report (PDF or TXT)"),
):
    """
    Accept two uploaded files (inspection + thermal), run the full
    DDR pipeline, and return the structured result.
    """
    # ── Validate API key ──────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured on the server. Add it to .env",
        )

    genai.configure(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ── Validate file extensions ──────────────────────────────────
    allowed_exts = {".pdf", ".txt"}
    for upload, label in [(inspection_file, "Inspection"), (thermal_file, "Thermal")]:
        ext = Path(upload.filename).suffix.lower()
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"{label} file must be PDF or TXT (got '{ext}').",
            )

    # ── Save uploads to temp files ────────────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="ddr_")
    try:
        inspection_path = _save_upload(inspection_file, tmp_dir)
        thermal_path = _save_upload(thermal_file, tmp_dir)

        logger.info(
            "Received files: %s (%s), %s (%s)",
            inspection_file.filename, _fmt_size(inspection_file.size),
            thermal_file.filename, _fmt_size(thermal_file.size),
        )

        # ── Step 1: Load documents ────────────────────────────────
        logger.info("[1/6] Loading documents...")
        inspection_text = load_document(inspection_path)
        thermal_text = load_document(thermal_path)

        if not inspection_text.strip():
            raise HTTPException(status_code=400, detail="Inspection file is empty or unreadable.")
        if not thermal_text.strip():
            raise HTTPException(status_code=400, detail="Thermal file is empty or unreadable.")

        # ── Step 2: Extract structured data ───────────────────────
        logger.info("[2/6] Extracting from inspection report...")
        inspection_data = extract_structured_data(
            inspection_text, "inspection_report", model
        )

        logger.info("[2/6] Extracting from thermal report...")
        thermal_data = extract_structured_data(
            thermal_text, "thermal_report", model
        )

        # ── Step 3: Merge ─────────────────────────────────────────
        logger.info("[3/6] Merging findings...")
        merged = merge_extractions(inspection_data, thermal_data)

        # ── Step 4: Reasoning ─────────────────────────────────────
        logger.info("[4/6] Generating DDR narrative...")
        ddr_text = generate_ddr_reasoning(merged, model)

        # ── Step 5: Validate ──────────────────────────────────────
        logger.info("[5/6] Validating report...")
        validation = validate_ddr(ddr_text, merged)

        # ── Step 6: Format ────────────────────────────────────────
        logger.info("[6/6] Formatting final report...")
        final_report = generate_final_report(
            ddr_text=ddr_text,
            merged_data=merged,
            inspection_file=inspection_file.filename,
            thermal_file=thermal_file.filename,
        )

        # ── Build response ────────────────────────────────────────
        # Collect conflicts from merged areas
        conflicts = []
        for area in merged.areas:
            if area.conflict_detected:
                conflicts.append({
                    "area": area.area_name,
                    "description": area.conflict_description,
                })

        # Build extracted data summary
        extracted_data = {
            "inspection": inspection_data.model_dump(),
            "thermal": thermal_data.model_dump(),
            "merged": merged.model_dump(),
        }

        # Validation warnings as list of dicts
        validation_warnings = [
            {"category": w.category, "detail": w.detail, "severity": w.severity}
            for w in validation.warnings
        ]

        logger.info("Pipeline complete. Report: %d chars.", len(final_report))

        return DDRResponse(
            ddr_report=final_report,
            extracted_data=extracted_data,
            conflicts=conflicts,
            validation_warnings=validation_warnings,
        )

    except HTTPException:
        raise  # re-raise HTTP errors as-is
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Clean up temp files
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Helpers ────────────────────────────────────────────────────────────

def _save_upload(upload: UploadFile, directory: str) -> str:
    """Save an uploaded file to the temp directory and return its path."""
    filename = Path(upload.filename).name  # sanitize
    dest = os.path.join(directory, filename)
    with open(dest, "wb") as f:
        content = upload.file.read()
        f.write(content)
    # Reset file pointer in case it's needed again
    upload.file.seek(0)
    return dest


def _fmt_size(size) -> str:
    """Format file size nicely."""
    if size is None:
        return "unknown size"
    if size < 1024:
        return f"{size} B"
    if size < 1048576:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1048576:.1f} MB"


# ── Run with uvicorn ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print(f"\n  AI DDR Builder API Server")
    print(f"  Starting on http://localhost:{port}")
    print(f"  Docs at    http://localhost:{port}/docs\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
