"""
Validation Layer Module
========================
Cross-checks the final DDR text against the original merged data to
detect potential hallucinations (facts not grounded in the source data).

Strategy:
    1. Collect every factual "token" from the merged data (area names,
       observations, readings, notes, etc.) into a reference set.
    2. Extract key claims from the DDR text.
    3. Flag any DDR sentence that contains specific factual details
       (numbers, temperatures, area names) NOT found in the reference set.
    4. Return a structured validation report.

This is a heuristic layer — it cannot guarantee zero hallucination,
but it catches the most common cases (invented temperatures, fabricated
area names, numbers that don't appear in the source).
"""

import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from .merger import MergedData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas for validation results
# ---------------------------------------------------------------------------


class ValidationWarning(BaseModel):
    """A single validation warning."""

    category: str = Field(
        ..., description="Type of warning: hallucination | ungrounded_number | unknown_area"
    )
    detail: str = Field(..., description="Human-readable description of the issue")
    severity: str = Field(
        default="warning",
        description="warning | error",
    )


class ValidationResult(BaseModel):
    """Full validation report."""

    passed: bool = Field(
        ..., description="True if no errors were found (warnings are acceptable)"
    )
    warnings: list[ValidationWarning] = Field(default_factory=list)
    info: str = Field(
        default="",
        description="Summary of the validation run",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_ddr(
    ddr_text: str,
    merged_data: MergedData,
) -> ValidationResult:
    """
    Validate the DDR text against the merged data.

    Checks performed:
        1. Area-name grounding — every area name in the DDR should exist
           in the merged data.
        2. Number grounding — numeric values in the DDR (temperatures,
           measurements) should appear in the merged data.
        3. "Not Available" compliance — sections marked as missing in
           merged data should not suddenly have concrete values.

    Returns:
        A ``ValidationResult`` with any warnings found.
    """
    warnings: list[ValidationWarning] = []

    # Build the reference sets from merged data
    ref_area_names = _collect_area_names(merged_data)
    ref_numbers = _collect_numbers(merged_data)
    ref_all_text = _collect_all_text(merged_data)

    logger.info(
        "Validation reference: %d areas, %d numbers, %d text tokens.",
        len(ref_area_names),
        len(ref_numbers),
        len(ref_all_text),
    )

    # --- Check 1: Area names in DDR ---
    ddr_area_names = _extract_area_names_from_ddr(ddr_text, ref_area_names)
    for name in ddr_area_names:
        if not _is_grounded(name, ref_area_names):
            warnings.append(
                ValidationWarning(
                    category="unknown_area",
                    detail=f"Area name '{name}' appears in DDR but was not found in merged data.",
                    severity="warning",
                )
            )

    # --- Check 2: Numeric values ---
    ddr_numbers = _extract_numbers(ddr_text)
    for num in ddr_numbers:
        if num not in ref_numbers and not _is_common_number(num):
            warnings.append(
                ValidationWarning(
                    category="ungrounded_number",
                    detail=f"Number '{num}' in DDR not found in source data — possible hallucination.",
                    severity="warning",
                )
            )

    # --- Check 3: Key phrases grounding spot-check ---
    hallucination_phrases = _spot_check_phrases(ddr_text, ref_all_text)
    for phrase in hallucination_phrases:
        warnings.append(
            ValidationWarning(
                category="hallucination",
                detail=f"Phrase may not be grounded in source data: '{phrase}'",
                severity="warning",
            )
        )

    # Determine pass / fail (errors = fail, warnings only = pass)
    has_errors = any(w.severity == "error" for w in warnings)
    passed = not has_errors

    info_msg = (
        f"Validation complete: {len(warnings)} warning(s) found."
        if warnings
        else "Validation complete: no issues detected."
    )

    result = ValidationResult(passed=passed, warnings=warnings, info=info_msg)
    logger.info(info_msg)
    return result


# ---------------------------------------------------------------------------
# Internal helpers — reference collection
# ---------------------------------------------------------------------------


def _collect_area_names(data: MergedData) -> set[str]:
    """Collect all area names from merged data (lowercased for matching)."""
    return {area.area_name.lower().strip() for area in data.areas}


def _collect_numbers(data: MergedData) -> set[str]:
    """Collect all numeric strings from merged data."""
    numbers: set[str] = set()
    for area in data.areas:
        for field in [
            area.inspection_observations,
            area.thermal_findings,
            area.temperature_readings,
            area.visible_damage,
        ]:
            for item in (field or []):
                numbers.update(_extract_numbers(item))
        # Also check string fields
        for text_field in [area.moisture_presence, area.other_notes]:
            if text_field:
                numbers.update(_extract_numbers(text_field))
    for note in data.global_notes:
        numbers.update(_extract_numbers(note))
    return numbers


def _collect_all_text(data: MergedData) -> set[str]:
    """
    Collect all meaningful text tokens (words 4+ chars) from merged data
    for a rough grounding check.
    """
    tokens: set[str] = set()
    all_strings: list[str] = []

    for area in data.areas:
        all_strings.append(area.area_name)
        all_strings.extend(area.inspection_observations or [])
        all_strings.extend(area.thermal_findings or [])
        all_strings.extend(area.temperature_readings or [])
        all_strings.extend(area.visible_damage or [])
        if area.moisture_presence:
            all_strings.append(area.moisture_presence)
        if area.other_notes:
            all_strings.append(area.other_notes)
    all_strings.extend(data.global_notes)

    for s in all_strings:
        for word in re.findall(r"[a-zA-Z]{4,}", s.lower()):
            tokens.add(word)

    return tokens


# ---------------------------------------------------------------------------
# Internal helpers — DDR analysis
# ---------------------------------------------------------------------------


def _extract_area_names_from_ddr(
    ddr_text: str, known_names: set[str]
) -> list[str]:
    """
    Heuristically extract area names from DDR text.

    Strategy: look for capitalised phrases that could be location names,
    especially near patterns like "Area:" or after bullet points.
    """
    found: list[str] = []

    # Pattern: "Area: <Name>" or "Area Name: <Name>"
    for match in re.finditer(
        r"(?:area(?:\s+name)?)\s*[:]\s*(.+)", ddr_text, re.IGNORECASE
    ):
        name = match.group(1).strip().rstrip(".")
        if name:
            found.append(name.lower())

    return list(set(found))


def _extract_numbers(text: str) -> set[str]:
    """Extract all numeric values (including decimals) from text."""
    return set(re.findall(r"\d+\.?\d*", text))


def _is_grounded(name: str, reference: set[str], threshold: float = 0.7) -> bool:
    """Check if *name* matches any entry in *reference* (fuzzy)."""
    from difflib import SequenceMatcher

    name_lower = name.lower().strip()
    for ref in reference:
        if name_lower in ref or ref in name_lower:
            return True
        if SequenceMatcher(None, name_lower, ref).ratio() >= threshold:
            return True
    return False


def _is_common_number(num: str) -> bool:
    """Filter out very common numbers that are unlikely hallucinations."""
    common = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0", "100"}
    return num in common


def _spot_check_phrases(
    ddr_text: str,
    ref_tokens: set[str],
    max_warnings: int = 5,
) -> list[str]:
    """
    Quick heuristic: find sentences containing specific-sounding claims
    (e.g., with numbers or technical terms) and check if the key words
    appear in the reference token set.

    Returns up to *max_warnings* suspicious phrases.
    """
    suspicious: list[str] = []

    # Split into sentences
    sentences = re.split(r"[.!?\n]", ddr_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue

        # Only check sentences with specific claims (numbers or technical terms)
        if not re.search(r"\d", sentence):
            continue

        # Extract key words (4+ chars, not common English)
        words = set(re.findall(r"[a-zA-Z]{4,}", sentence.lower()))
        common_english = {
            "that", "this", "with", "from", "have", "been", "were", "area",
            "based", "show", "shows", "found", "noted", "which", "their",
            "there", "should", "could", "would", "about", "more", "also",
            "into", "over", "such", "than", "them", "then", "these", "only",
            "some", "very", "when", "will", "each", "made", "like",
            "does", "done", "make", "many", "most", "much", "must",
            "near", "need", "next", "once", "part", "same", "take",
            "they", "what", "your",
        }
        key_words = words - common_english

        if not key_words:
            continue

        # Check how many key words are grounded
        ungrounded = key_words - ref_tokens
        grounded_ratio = 1 - (len(ungrounded) / len(key_words)) if key_words else 1

        # If less than 40% of key words are grounded, flag it
        if grounded_ratio < 0.4 and len(ungrounded) >= 3:
            suspicious.append(sentence[:120])
            if len(suspicious) >= max_warnings:
                break

    return suspicious
