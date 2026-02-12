"""
DDR Generator Module
====================
Wraps the raw DDR text from the reasoning engine in a clean, formatted
final report structure.

Responsibilities:
    - Add report header and footer
    - Inject metadata (generation timestamp, source files, etc.)
    - Append merge-level warnings (conflicts, duplicates)
    - Return the final formatted string
    - Optionally write to a file
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .merger import MergedData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEPARATOR = "=" * 60
_THIN_SEP = "-" * 60


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_final_report(
    ddr_text: str,
    merged_data: MergedData,
    inspection_file: str = "N/A",
    thermal_file: str = "N/A",
    output_path: Optional[str] = None,
) -> str:
    """
    Produce the final formatted DDR report.

    Parameters:
        ddr_text:        Raw narrative text from the reasoning engine.
        merged_data:     The merged data (used for conflict / duplicate appendix).
        inspection_file: Name or path of the inspection source file.
        thermal_file:    Name or path of the thermal source file.
        output_path:     If provided, also write the report to this file.

    Returns:
        The complete DDR report as a formatted string.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    parts: list[str] = []

    # --- Header ---
    parts.append(_SEPARATOR)
    parts.append("       DETAILED DIAGNOSTIC REPORT (DDR)")
    parts.append(_SEPARATOR)
    parts.append("")
    parts.append(f"Generated : {now}")
    parts.append(f"Source 1  : {inspection_file}")
    parts.append(f"Source 2  : {thermal_file}")
    parts.append("")
    parts.append(_SEPARATOR)
    parts.append("")

    # --- Main DDR body ---
    parts.append(ddr_text)
    parts.append("")

    # --- Appendix: Conflict Summary ---
    conflicts = [
        area for area in merged_data.areas if area.conflict_detected
    ]
    if conflicts:
        parts.append(_THIN_SEP)
        parts.append("APPENDIX A: CONFLICT SUMMARY")
        parts.append(_THIN_SEP)
        for area in conflicts:
            parts.append(f"  Area: {area.area_name}")
            parts.append(f"    {area.conflict_description}")
            parts.append("")

    # --- Appendix: Duplicate Warnings ---
    if merged_data.duplicate_warnings:
        parts.append(_THIN_SEP)
        parts.append("APPENDIX B: DUPLICATE DATA WARNINGS")
        parts.append(_THIN_SEP)
        for warning in merged_data.duplicate_warnings:
            parts.append(f"  - {warning}")
        parts.append("")

    # --- Footer ---
    parts.append(_SEPARATOR)
    parts.append("                 END OF REPORT")
    parts.append(_SEPARATOR)

    report = "\n".join(parts)

    # Optionally persist to file
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        logger.info("Report written to %s", out)

    logger.info("Final DDR report generated (%d chars).", len(report))
    return report
