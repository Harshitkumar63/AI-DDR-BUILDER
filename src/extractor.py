"""
Structured Extractor Module
============================
Sends raw document text to the LLM with a strict extraction prompt
and returns a validated Pydantic model of the extracted data.

Responsibilities:
    - Load the extraction prompt template
    - Call the LLM (Google Gemini) with the document text
    - Parse the JSON response into Pydantic models
    - Handle and log extraction errors gracefully
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas — these enforce the structure we expect from the LLM
# ---------------------------------------------------------------------------


class AreaExtraction(BaseModel):
    """Structured extraction for a single area / location."""

    area_name: str = Field(..., description="Name of the area or location")
    inspection_observations: Optional[list[str]] = Field(
        default=None,
        description="Visual inspection findings for this area",
    )
    thermal_findings: Optional[list[str]] = Field(
        default=None,
        description="Thermal imaging findings for this area",
    )
    temperature_readings: Optional[list[str]] = Field(
        default=None,
        description="Specific temperature values mentioned",
    )
    visible_damage: Optional[list[str]] = Field(
        default=None,
        description="Visible damage observations",
    )
    moisture_presence: Optional[str] = Field(
        default=None,
        description="Description of moisture detection",
    )
    other_notes: Optional[str] = Field(
        default=None,
        description="Any additional notes",
    )


class DocumentExtraction(BaseModel):
    """Top-level extraction result for a single document."""

    areas: Optional[list[AreaExtraction]] = Field(
        default_factory=list,
        description="Per-area extracted observations",
    )
    global_notes: Optional[list[str]] = Field(
        default_factory=list,
        description="Document-level notes not tied to a specific area",
    )

    def model_post_init(self, __context) -> None:
        """Coerce None values to empty lists after validation."""
        if self.areas is None:
            self.areas = []
        if self.global_notes is None:
            self.global_notes = []


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_extraction_prompt() -> str:
    """Load the extraction prompt template from disk."""
    prompt_path = _PROMPT_DIR / "extraction_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Extraction prompt not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_structured_data(
    document_text: str,
    document_type: str,
    model_name: str = "gemini-2.0-flash",
) -> DocumentExtraction:
    """
    Extract structured observations from *document_text* using Google Gemini.

    Parameters:
        document_text:  Raw text of the document.
        document_type:  Either ``"inspection_report"`` or ``"thermal_report"``.
        model_name:     The Gemini model name to use for extraction.

    Returns:
        A validated ``DocumentExtraction`` Pydantic model.
    """
    if not document_text.strip():
        logger.warning("Empty document text provided — returning empty extraction.")
        return DocumentExtraction(areas=[], global_notes=[])

    # Build the prompt by filling in placeholders
    prompt_template = _load_extraction_prompt()
    prompt = prompt_template.format(
        document_type=document_type,
        document_text=document_text,
    )

    logger.info(
        "Sending extraction request to %s (doc_type=%s, text_len=%d)",
        model_name,
        document_type,
        len(document_text),
    )

    try:
        raw_content = _call_gemini_extract(model_name, prompt)

        logger.debug("Raw LLM response (first 500 chars): %s", raw_content[:500])

        # Clean potential markdown fences the model may add despite instructions
        raw_content = _strip_json_fences(raw_content)

        # Attempt to repair truncated JSON before parsing
        raw_content = _repair_truncated_json(raw_content)

        # Parse JSON and validate with Pydantic
        data = json.loads(raw_content)
        extraction = DocumentExtraction.model_validate(data)

        logger.info(
            "Extraction complete — %d areas, %d global notes.",
            len(extraction.areas),
            len(extraction.global_notes),
        )
        return extraction

    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", exc)
        raise ValueError(f"Extraction failed — invalid JSON from LLM: {exc}") from exc
    except Exception as exc:
        logger.error("Extraction failed: %s", exc)
        raise


def _call_gemini_extract(model_name: str, prompt: str) -> str:
    """Call Gemini with retry logic for rate-limits and truncation."""
    max_tokens = 16384  # generous limit to avoid truncation

    for attempt in range(1, 4):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=(
                    "You are a precise data-extraction assistant. "
                    "Return ONLY valid JSON with no additional text. "
                    "Keep responses concise — use short descriptions."
                ),
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=max_tokens,
                ),
            )
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # Check if response looks truncated (no closing brace)
            cleaned = _strip_json_fences(raw)
            if cleaned and not cleaned.rstrip().endswith("}"):
                logger.warning(
                    "Response appears truncated (attempt %d/3). Retrying with higher limit...",
                    attempt,
                )
                max_tokens = min(max_tokens + 8192, 65536)
                time.sleep(5)
                continue

            return raw

        except Exception as retry_exc:
            if "429" in str(retry_exc) and attempt < 3:
                wait = 30 * attempt
                logger.warning(
                    "Rate limited (attempt %d/3). Waiting %ds...",
                    attempt, wait,
                )
                time.sleep(wait)
            else:
                raise

    # If all retries resulted in truncation, return the last response anyway
    return raw  # noqa: F821 — variable is set in the loop


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (may include language tag)
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[: -3]
    return text.strip()


def _repair_truncated_json(text: str) -> str:
    """
    Attempt to repair truncated JSON by closing unclosed brackets/braces.

    This handles the common case where the LLM output was cut off mid-response,
    leaving unterminated strings, arrays, or objects.
    """
    text = text.rstrip()

    # If it already parses, return as-is
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Strategy: find the last valid position and close everything after it
    # First, try to fix unterminated strings by adding a closing quote
    # Then close any open brackets/braces

    # Count open/close brackets
    in_string = False
    escape_next = False
    open_stack = []

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '{[':
            open_stack.append(ch)
        elif ch == '}' and open_stack and open_stack[-1] == '{':
            open_stack.pop()
        elif ch == ']' and open_stack and open_stack[-1] == '[':
            open_stack.pop()

    # Build repair suffix
    repair = ""

    # If we're inside a string, close it
    if in_string:
        repair += '"'

    # Close any open arrays/objects in reverse order
    for bracket in reversed(open_stack):
        if bracket == '{':
            repair += '}'
        elif bracket == '[':
            repair += ']'

    if repair:
        logger.warning("Repairing truncated JSON — appending: %s", repr(repair))
        text = text + repair

    return text
