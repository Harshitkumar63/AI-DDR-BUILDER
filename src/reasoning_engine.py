"""
Reasoning Engine Module
========================
Takes the merged data and sends it to Google Gemini with the reasoning prompt
to generate the narrative DDR sections.

Responsibilities:
    - Serialise merged data to a clean string representation
    - Load the reasoning prompt template
    - Call the LLM for narrative generation
    - Return the raw DDR text for formatting
"""

import json
import logging
import time
from pathlib import Path

import google.generativeai as genai

from .merger import MergedData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_reasoning_prompt() -> str:
    """Load the reasoning prompt template from disk."""
    prompt_path = _PROMPT_DIR / "reasoning_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Reasoning prompt not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_ddr_reasoning(
    merged_data: MergedData,
    model_name: str = "gemini-2.0-flash",
) -> str:
    """
    Generate the narrative DDR text by sending *merged_data* through the
    reasoning prompt to Google Gemini.

    Parameters:
        merged_data: The fully merged and deduplicated data.
        model_name:  The Gemini model name to use for reasoning.

    Returns:
        The raw DDR text produced by the LLM.
    """
    # Serialise merged data to a readable JSON string
    merged_json = json.dumps(
        merged_data.model_dump(),
        indent=2,
        ensure_ascii=False,
    )

    # Build the prompt
    prompt_template = _load_reasoning_prompt()
    prompt = prompt_template.format(merged_data=merged_json)

    logger.info(
        "Sending reasoning request to %s (merged_data_len=%d chars)",
        model_name,
        len(merged_json),
    )

    try:
        # Create the Gemini model with a system instruction for DDR generation
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=(
                "You are a senior property diagnostics analyst. "
                "Produce a clear, client-friendly Detailed Diagnostic "
                "Report using ONLY the data provided. "
                "Never invent facts. If data is missing, say 'Not Available'."
            ),
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,  # low creativity — stick to the data
                max_output_tokens=8192,
            ),
        )

        # Retry logic for rate-limit (429) errors
        ddr_text = None
        for attempt in range(1, 4):
            try:
                response = model.generate_content(prompt)
                ddr_text = response.text.strip()
                break
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

        if ddr_text is None:
            raise RuntimeError("Failed to get response after retries.")

        logger.info(
            "Reasoning complete — DDR text length: %d chars.", len(ddr_text)
        )
        return ddr_text

    except Exception as exc:
        logger.error("Reasoning engine failed: %s", exc)
        raise
