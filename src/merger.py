"""
Merger Module
=============
Merges the structured extractions from the Inspection Report and the
Thermal Report into a single unified data structure.

Responsibilities:
    - Match areas across both reports (fuzzy / semantic matching)
    - Combine observations per area
    - Detect and flag duplicate information
    - Detect and flag conflicting information
    - Insert "Not Available" for missing data
"""

import logging
from difflib import SequenceMatcher
from typing import Optional

from pydantic import BaseModel, Field

from .extractor import AreaExtraction, DocumentExtraction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas for merged output
# ---------------------------------------------------------------------------


class MergedArea(BaseModel):
    """A single area after merging inspection + thermal data."""

    area_name: str
    inspection_observations: list[str] = Field(default_factory=list)
    thermal_findings: list[str] = Field(default_factory=list)
    temperature_readings: list[str] = Field(default_factory=list)
    visible_damage: list[str] = Field(default_factory=list)
    moisture_presence: str = "Not Available"
    other_notes: str = "Not Available"

    # Conflict tracking
    conflict_detected: bool = False
    conflict_description: Optional[str] = None

    # Source tracking — which report contributed
    sources: list[str] = Field(default_factory=list)


class MergedData(BaseModel):
    """Top-level merged data from both reports."""

    areas: list[MergedArea] = Field(default_factory=list)
    global_notes: list[str] = Field(default_factory=list)
    duplicate_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def merge_extractions(
    inspection: DocumentExtraction,
    thermal: DocumentExtraction,
    similarity_threshold: float = 0.65,
) -> MergedData:
    """
    Merge *inspection* and *thermal* extractions into a single ``MergedData``.

    Area matching is performed using fuzzy string similarity on area names.
    The *similarity_threshold* (0–1) controls how close two names must be
    to be considered the same area.
    """
    logger.info(
        "Merging extractions: %d inspection areas, %d thermal areas.",
        len(inspection.areas),
        len(thermal.areas),
    )

    merged_areas: list[MergedArea] = []
    duplicate_warnings: list[str] = []

    # Track which thermal areas have been matched
    matched_thermal_indices: set[int] = set()

    # --- Step 1: For each inspection area, find the best thermal match ---
    for insp_area in inspection.areas:
        best_idx, best_score = _find_best_match(
            insp_area.area_name, thermal.areas, similarity_threshold
        )

        if best_idx is not None:
            therm_area = thermal.areas[best_idx]
            matched_thermal_indices.add(best_idx)
            logger.info(
                "Matched '%s' ↔ '%s' (score=%.2f)",
                insp_area.area_name,
                therm_area.area_name,
                best_score,
            )
            merged = _merge_two_areas(insp_area, therm_area, duplicate_warnings)
        else:
            # No thermal match — inspection-only area
            merged = _area_from_single(insp_area, source="inspection_report")

        merged_areas.append(merged)

    # --- Step 2: Add unmatched thermal areas ---
    for idx, therm_area in enumerate(thermal.areas):
        if idx not in matched_thermal_indices:
            logger.info(
                "Thermal area '%s' has no inspection match — adding standalone.",
                therm_area.area_name,
            )
            merged_areas.append(
                _area_from_single(therm_area, source="thermal_report")
            )

    # --- Step 3: Merge global notes ---
    global_notes = _deduplicate_strings(
        inspection.global_notes + thermal.global_notes, duplicate_warnings
    )

    result = MergedData(
        areas=merged_areas,
        global_notes=global_notes,
        duplicate_warnings=duplicate_warnings,
    )
    logger.info(
        "Merge complete — %d areas, %d duplicate warnings.",
        len(result.areas),
        len(result.duplicate_warnings),
    )
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_best_match(
    name: str,
    candidates: list[AreaExtraction],
    threshold: float,
) -> tuple[Optional[int], float]:
    """Return the index and score of the best matching candidate, or (None, 0)."""
    best_idx: Optional[int] = None
    best_score: float = 0.0
    name_lower = name.lower().strip()

    for idx, cand in enumerate(candidates):
        score = SequenceMatcher(
            None, name_lower, cand.area_name.lower().strip()
        ).ratio()
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_score >= threshold:
        return best_idx, best_score
    return None, 0.0


def _merge_two_areas(
    insp: AreaExtraction,
    therm: AreaExtraction,
    dup_warnings: list[str],
) -> MergedArea:
    """Merge an inspection area and a thermal area into one ``MergedArea``."""
    # Prefer the inspection area name (it's typically the canonical one)
    area_name = insp.area_name

    # Combine list fields with deduplication
    inspection_obs = _deduplicate_strings(
        (insp.inspection_observations or []) + (therm.inspection_observations or []),
        dup_warnings,
    )
    thermal_findings = _deduplicate_strings(
        (insp.thermal_findings or []) + (therm.thermal_findings or []),
        dup_warnings,
    )
    temp_readings = _deduplicate_strings(
        (insp.temperature_readings or []) + (therm.temperature_readings or []),
        dup_warnings,
    )
    visible_damage = _deduplicate_strings(
        (insp.visible_damage or []) + (therm.visible_damage or []),
        dup_warnings,
    )

    # Moisture — merge with conflict detection
    moisture, conflict_moisture = _merge_optional_field(
        insp.moisture_presence, therm.moisture_presence, "moisture_presence", area_name
    )

    # Other notes — merge with conflict detection
    other, conflict_other = _merge_optional_field(
        insp.other_notes, therm.other_notes, "other_notes", area_name
    )

    # Aggregate conflicts
    conflict_detected = conflict_moisture or conflict_other
    conflict_parts: list[str] = []
    if conflict_moisture:
        conflict_parts.append(
            f"Moisture data conflict — Inspection: '{insp.moisture_presence}' vs Thermal: '{therm.moisture_presence}'"
        )
    if conflict_other:
        conflict_parts.append(
            f"Notes conflict — Inspection: '{insp.other_notes}' vs Thermal: '{therm.other_notes}'"
        )

    return MergedArea(
        area_name=area_name,
        inspection_observations=inspection_obs,
        thermal_findings=thermal_findings,
        temperature_readings=temp_readings,
        visible_damage=visible_damage,
        moisture_presence=moisture,
        other_notes=other,
        conflict_detected=conflict_detected,
        conflict_description="; ".join(conflict_parts) if conflict_parts else None,
        sources=["inspection_report", "thermal_report"],
    )


def _area_from_single(area: AreaExtraction, source: str) -> MergedArea:
    """Create a ``MergedArea`` from a single-source area."""
    return MergedArea(
        area_name=area.area_name,
        inspection_observations=area.inspection_observations or [],
        thermal_findings=area.thermal_findings or [],
        temperature_readings=area.temperature_readings or [],
        visible_damage=area.visible_damage or [],
        moisture_presence=area.moisture_presence or "Not Available",
        other_notes=area.other_notes or "Not Available",
        conflict_detected=False,
        conflict_description=None,
        sources=[source],
    )


def _merge_optional_field(
    val_a: Optional[str],
    val_b: Optional[str],
    field_name: str,
    area_name: str,
) -> tuple[str, bool]:
    """
    Merge two optional string fields.

    Returns:
        (merged_value, conflict_detected)
    """
    a = (val_a or "").strip()
    b = (val_b or "").strip()

    if not a and not b:
        return "Not Available", False
    if not a:
        return b, False
    if not b:
        return a, False

    # Both present — check for conflict
    similarity = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    if similarity > 0.75:
        # Similar enough — take the longer one
        return max(a, b, key=len), False

    # Genuine conflict
    logger.warning(
        "Conflict in '%s' for area '%s': '%s' vs '%s'",
        field_name,
        area_name,
        a,
        b,
    )
    combined = f"[CONFLICT] Inspection: {a} | Thermal: {b}"
    return combined, True


def _deduplicate_strings(
    items: list[str], dup_warnings: list[str], threshold: float = 0.85
) -> list[str]:
    """
    Remove near-duplicate strings from *items*.

    Uses fuzzy similarity; exact duplicates are always removed.
    Appends warnings to *dup_warnings* for any duplicates found.
    """
    if not items:
        return []

    unique: list[str] = []
    for item in items:
        item_stripped = item.strip()
        if not item_stripped:
            continue
        is_dup = False
        for existing in unique:
            sim = SequenceMatcher(
                None, item_stripped.lower(), existing.lower()
            ).ratio()
            if sim >= threshold:
                is_dup = True
                dup_warnings.append(
                    f"Duplicate removed (sim={sim:.2f}): '{item_stripped}' ≈ '{existing}'"
                )
                break
        if not is_dup:
            unique.append(item_stripped)

    return unique
