"""
AI DDR Builder — Main Application
===================================
CLI entry-point that orchestrates the full pipeline:

    1. Load documents  (document_loader)
    2. Extract data    (extractor)
    3. Merge findings  (merger)
    4. Reason / draft  (reasoning_engine)
    5. Validate        (validator)
    6. Format & output (ddr_generator)

Usage:
    python app.py --inspection data/sample_inspection_report.txt \
                  --thermal    data/sample_thermal_report.txt \
                  --output     data/output_ddr.txt

    python app.py --demo   # runs with bundled sample files
"""

import json
import logging
import os
import sys
from pathlib import Path

import click
import google.generativeai as genai
from dotenv import load_dotenv

# ── Local imports ──────────────────────────────────────────────────────
from src.document_loader import load_document
from src.extractor import extract_structured_data
from src.merger import merge_extractions
from src.reasoning_engine import generate_ddr_reasoning
from src.ddr_generator import generate_final_report
from src.validator import validate_ddr

# ── Setup ──────────────────────────────────────────────────────────────
load_dotenv()

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ai_ddr_builder")

# Default paths for demo mode
_PROJECT_DIR = Path(__file__).resolve().parent
_DEFAULT_INSPECTION = _PROJECT_DIR / "data" / "sample_inspection_report.txt"
_DEFAULT_THERMAL = _PROJECT_DIR / "data" / "sample_thermal_report.txt"
_DEFAULT_OUTPUT = _PROJECT_DIR / "data" / "output_ddr.txt"

_SEP = "=" * 70


def _step(number: int, msg: str) -> None:
    """Print a pipeline step header."""
    print(f"\n  [{number}/6] {msg}")


def _done(msg: str) -> None:
    """Print a completion message."""
    print(f"        -> {msg}")


# ── Pipeline ───────────────────────────────────────────────────────────

def run_pipeline(
    inspection_path: str,
    thermal_path: str,
    output_path: str,
    model: str = "gemini-2.0-flash-lite",
) -> str:
    """
    Execute the full DDR pipeline and return the final report text.

    Steps:
        1. Load both documents.
        2. Extract structured data from each.
        3. Merge the two extractions.
        4. Generate narrative DDR via reasoning engine.
        5. Validate the DDR against source data.
        6. Format and (optionally) save the final report.
    """
    # Configure Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set.")
        print("Create a .env file (see .env.example) or export the variable.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    genai.configure(api_key=api_key)

    # ── Step 1: Load documents ────────────────────────────────────
    _step(1, "Loading documents...")
    inspection_text = load_document(inspection_path)
    thermal_text = load_document(thermal_path)
    _done(
        f"Inspection: {len(inspection_text):,} chars | "
        f"Thermal: {len(thermal_text):,} chars"
    )

    # ── Step 2: Extract structured data ───────────────────────────
    _step(2, "Extracting structured data from inspection report...")
    inspection_data = extract_structured_data(
        inspection_text, "inspection_report", model
    )
    _done(f"Inspection: {len(inspection_data.areas)} areas extracted.")

    print(f"  [2/6] Extracting structured data from thermal report...")
    thermal_data = extract_structured_data(
        thermal_text, "thermal_report", model
    )
    _done(f"Thermal: {len(thermal_data.areas)} areas extracted.")

    # ── Step 3: Merge extractions ─────────────────────────────────
    _step(3, "Merging findings...")
    merged = merge_extractions(inspection_data, thermal_data)
    _done(
        f"Merged areas: {len(merged.areas)} | "
        f"Duplicate warnings: {len(merged.duplicate_warnings)} | "
        f"Conflicts: {sum(1 for a in merged.areas if a.conflict_detected)}"
    )

    # Save intermediate merged JSON for transparency
    merged_json_path = Path(output_path).parent / "merged_data.json"
    merged_json_path.write_text(
        json.dumps(merged.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _done(f"Merged data saved to: {merged_json_path}")

    # ── Step 4: Generate DDR reasoning ────────────────────────────
    _step(4, "Generating DDR narrative (this may take a moment)...")
    ddr_text = generate_ddr_reasoning(merged, model)
    _done(f"DDR narrative generated ({len(ddr_text):,} chars).")

    # ── Step 5: Validate ──────────────────────────────────────────
    _step(5, "Validating report against source data...")
    validation = validate_ddr(ddr_text, merged)

    if validation.warnings:
        _done(f"Validation: {len(validation.warnings)} warning(s)")
        for w in validation.warnings:
            print(f"           [{w.severity}] {w.category}: {w.detail}")
    else:
        _done("Validation: PASSED -- no issues detected.")

    # ── Step 6: Format final report ───────────────────────────────
    _step(6, "Formatting final report...")
    final_report = generate_final_report(
        ddr_text=ddr_text,
        merged_data=merged,
        inspection_file=inspection_path,
        thermal_file=thermal_path,
        output_path=output_path,
    )
    _done("Report ready.")

    # ── Display ───────────────────────────────────────────────────
    print(f"\n{_SEP}")
    print(final_report)
    print(_SEP)
    print(f"\nReport saved to: {output_path}")

    return final_report


# ── CLI ────────────────────────────────────────────────────────────────

@click.command()
@click.option(
    "--inspection", "-i",
    type=click.Path(exists=False),
    default=None,
    help="Path to the inspection report (PDF or TXT).",
)
@click.option(
    "--thermal", "-t",
    type=click.Path(exists=False),
    default=None,
    help="Path to the thermal report (PDF or TXT).",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output path for the generated DDR.",
)
@click.option(
    "--model", "-m",
    type=str,
    default=None,
    help="Gemini model to use (default: gemini-2.0-flash-lite).",
)
@click.option(
    "--demo",
    is_flag=True,
    default=False,
    help="Run with bundled sample documents.",
)
def main(
    inspection: str | None,
    thermal: str | None,
    output: str | None,
    model: str | None,
    demo: bool,
):
    """
    AI DDR Builder -- Convert inspection & thermal reports into a
    structured Detailed Diagnostic Report (powered by Google Gemini).
    """
    print(_SEP)
    print("  AI DDR Builder")
    print("  Automated Detailed Diagnostic Report Generator")
    print("  Powered by Google Gemini")
    print(_SEP)

    # Resolve paths
    if demo:
        inspection = str(_DEFAULT_INSPECTION)
        thermal = str(_DEFAULT_THERMAL)
        output = output or str(_DEFAULT_OUTPUT)
        print("\n  [DEMO MODE] Running with sample data.\n")
    else:
        if not inspection or not thermal:
            print("ERROR: Provide --inspection and --thermal paths, or use --demo.")
            sys.exit(1)
        output = output or str(_DEFAULT_OUTPUT)

    # Resolve model
    model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    print(f"  Inspection : {inspection}")
    print(f"  Thermal    : {thermal}")
    print(f"  Output     : {output}")
    print(f"  Model      : {model}")

    try:
        run_pipeline(inspection, thermal, output, model)
    except FileNotFoundError as exc:
        print(f"\nFile Error: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"\nValue Error: {exc}")
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error")
        print(f"\nUnexpected Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
