# AI DDR Builder

**Automated Detailed Diagnostic Report Generator**

Convert raw inspection and thermal reports into structured, client-ready
Detailed Diagnostic Reports (DDRs) using AI — with built-in hallucination
prevention, conflict detection, and validation.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [How It Works](#how-it-works)
5. [Usage](#usage)
6. [Hallucination Prevention Strategy](#hallucination-prevention-strategy)
7. [Conflict Handling Strategy](#conflict-handling-strategy)
8. [Limitations](#limitations)
9. [Future Improvements](#future-improvements)
10. [How to Explain This in 3–5 Minutes](#how-to-explain-this-in-35-minutes) 

---

## Project Overview

**Problem:** Property inspectors and diagnostics firms produce separate
inspection reports and thermal imaging reports. Manually merging these
into a single client-facing Detailed Diagnostic Report is time-consuming,
error-prone, and inconsistent.

**Solution:** AI DDR Builder automates this process through a modular
six-step pipeline that extracts, merges, reasons, validates, and formats
the data — ensuring no facts are invented and all conflicts are surfaced.

**Key Principles:**
- **No hallucination** — every fact in the DDR is traceable to source data
- **Conflict transparency** — disagreements between reports are flagged, not hidden
- **Missing data honesty** — gaps are labelled "Not Available", never guessed
- **Modularity** — each pipeline stage is independent and testable
- **Generalisability** — works on any inspection-style document pair

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AI DDR Builder                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │ Inspection   │    │  Thermal    │   INPUT DOCUMENTS       │
│  │ Report (PDF/ │    │  Report     │                         │
│  │ TXT)         │    │  (PDF/TXT)  │                         │
│  └──────┬───────┘    └──────┬──────┘                         │
│         │                   │                                │
│         ▼                   ▼                                │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 1: Document Loader       │   document_loader.py   │
│  │   (PDF/TXT → raw text)          │                         │
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 2: Structured Extractor  │   extractor.py         │
│  │   (LLM + Pydantic validation)   │   extraction_prompt.txt│
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 3: Merger                │   merger.py            │
│  │   (match areas, dedup, detect   │                         │
│  │    conflicts, fill gaps)        │                         │
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 4: Reasoning Engine      │   reasoning_engine.py  │
│  │   (LLM generates DDR narrative) │   reasoning_prompt.txt │
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 5: Validator             │   validator.py         │
│  │   (cross-check DDR vs source)   │                         │
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │   STEP 6: DDR Generator         │   ddr_generator.py     │
│  │   (format, header, appendices)  │                         │
│  └──────────────┬───────────────────┘                        │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────┐                        │
│  │        FINAL DDR REPORT          │   OUTPUT               │
│  │   (text file + console output)  │                         │
│  └──────────────────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### File Structure

```
ai_ddr_builder/
│
├── data/
│   ├── sample_inspection_report.txt   # Sample input
│   ├── sample_thermal_report.txt      # Sample input
│   ├── output_ddr.txt                 # Generated report (after run)
│   └── merged_data.json               # Intermediate merged data (after run)
│
├── src/
│   ├── __init__.py
│   ├── document_loader.py             # Step 1: Load PDF/TXT
│   ├── extractor.py                   # Step 2: LLM extraction → Pydantic
│   ├── merger.py                      # Step 3: Merge + dedup + conflict
│   ├── reasoning_engine.py            # Step 4: LLM reasoning → DDR text
│   ├── ddr_generator.py               # Step 6: Format final report
│   └── validator.py                   # Step 5: Anti-hallucination check
│
├── prompts/
│   ├── extraction_prompt.txt          # Extraction prompt template
│   └── reasoning_prompt.txt           # Reasoning prompt template
│
├── app.py                             # CLI entry point
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variable template
└── README.md                          # This file
```

---

## Installation

### Prerequisites
- Python 3.10+
- A Google Gemini API key (free tier available)

### Steps

```bash
# 1. Clone or navigate to the project
cd ai_ddr_builder

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
# Get a free key at: https://aistudio.google.com/apikey
```

---

## How It Works

### Step-by-Step Pipeline

| Step | Module | What It Does |
|------|--------|-------------|
| 1 | `document_loader.py` | Reads PDF or TXT files and returns clean text |
| 2 | `extractor.py` | Sends text to LLM with strict extraction prompt; parses response into Pydantic models |
| 3 | `merger.py` | Fuzzy-matches areas across reports, deduplicates observations, detects conflicts, fills "Not Available" |
| 4 | `reasoning_engine.py` | Sends merged data to LLM with reasoning prompt; generates DDR narrative sections |
| 5 | `validator.py` | Cross-checks final DDR against source data; flags ungrounded numbers, unknown areas, potential hallucinations |
| 6 | `ddr_generator.py` | Wraps DDR text in formatted report with header, metadata, and appendices |

### Data Flow

```
PDF/TXT → raw text → structured JSON → merged JSON → DDR narrative → validated → formatted report
```

### Intermediate Outputs

- `merged_data.json` — the merged structured data (saved for transparency)
- Console warnings — any validation issues are printed during the run

---

## Usage

### Demo Mode (sample data)

```bash
python app.py --demo
```

### Custom Reports

```bash
python app.py \
    --inspection path/to/inspection_report.pdf \
    --thermal path/to/thermal_report.txt \
    --output path/to/output_ddr.txt
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--inspection` | `-i` | Path to inspection report (PDF or TXT) |
| `--thermal` | `-t` | Path to thermal report (PDF or TXT) |
| `--output` | `-o` | Output path for DDR (default: `data/output_ddr.txt`) |
| `--model` | `-m` | Gemini model name (default: `gemini-2.0-flash`) |
| `--demo` | | Run with bundled sample files |

---

## Hallucination Prevention Strategy

Hallucination prevention is applied at **every stage** of the pipeline:

### 1. Extraction Prompt Constraints
- The extraction prompt explicitly forbids inventing facts
- Only data present in the document text may be extracted
- Missing fields must be set to `null`, not guessed

### 2. Structured Output Enforcement
- Pydantic models validate the extraction schema
- If the LLM returns malformed JSON, the pipeline fails cleanly rather than silently accepting bad data

### 3. Temperature = 0 for Extraction
- Extraction uses `temperature=0.0` for deterministic, faithful outputs
- Reasoning uses `temperature=0.2` — low creativity, high faithfulness

### 4. Reasoning Prompt Constraints
- The reasoning prompt forbids adding any fact not in the merged data
- Missing information must be labelled "Not Available"
- Root causes may only be suggested if directly supported by observations

### 5. Post-Generation Validation
- The validator cross-checks the final DDR against the merged source data:
  - **Area name grounding** — every area mentioned must exist in the source
  - **Numeric grounding** — numbers (temperatures, measurements) must appear in source data
  - **Phrase spot-checking** — sentences with specific claims are checked for source support
- Warnings are surfaced but do not block report generation (human review is expected)

### 6. Conflict Transparency
- Rather than silently picking one version, conflicts are explicitly flagged in the report appendix

---

## Conflict Handling Strategy

When the inspection report and thermal report disagree:

1. **Detection:** The merger compares overlapping fields using fuzzy string similarity. If two values for the same field differ significantly (similarity < 0.75), a conflict is flagged.

2. **Flagging:** The merged area gets:
   ```json
   {
     "conflict_detected": true,
     "conflict_description": "Moisture data conflict — Inspection: '...' vs Thermal: '...'"
   }
   ```

3. **DDR Integration:** The reasoning prompt instructs the LLM to explicitly mention conflicts and recommend further investigation.

4. **Appendix:** The final report includes an "APPENDIX A: CONFLICT SUMMARY" listing all detected conflicts.

---

## Limitations

1. **LLM Dependency** — Requires Google Gemini API access; quality depends on the model used.
2. **PDF Extraction Quality** — Scanned PDFs (images) are not supported; only text-based PDFs work.
3. **Heuristic Validation** — The validator catches common hallucinations but cannot guarantee zero false facts.
4. **Area Matching** — Fuzzy matching works well for similar names but may miss areas described very differently across reports.
5. **No Image Analysis** — Thermal images embedded in reports are not processed; only the text/data is used.
6. **Single Language** — Currently English-only.
7. **Cost** — Each pipeline run makes 3 LLM API calls (2 extractions + 1 reasoning).

---

## Future Improvements

1. **OCR Support** — Add Tesseract or cloud OCR for scanned PDF documents.
2. **Image Analysis** — Use Gemini vision to interpret thermal images directly.
3. **LLM-as-Judge Validation** — Add a second LLM call specifically to validate the DDR.
4. **Confidence Scores** — Attach confidence levels to each finding.
5. **Multi-Language Support** — Add prompt templates for other languages.
6. **Web Interface** — Build a Streamlit or FastAPI front-end for non-technical users.
7. **Batch Processing** — Support processing multiple property reports in one run.
8. **Template Customization** — Allow clients to customize DDR format and sections.
9. **Caching** — Cache LLM extraction results to reduce cost on re-runs.
10. **Local LLM Support** — Add support for Ollama / local models to eliminate API costs.

---

## How to Explain This in 3–5 Minutes

Use these bullet points for a Loom video walkthrough:

### Opening (30 seconds)
- "This is AI DDR Builder — it takes two raw technical reports and turns them into a single client-ready diagnostic report."
- Show the two sample input files side by side.

### Architecture Overview (60 seconds)
- "The system uses a 6-step pipeline." Walk through the ASCII diagram.
- Emphasise modularity: "Each step is its own Python module — easy to test, easy to swap."

### Demo Run (60 seconds)
- Run `python app.py --demo` and show the terminal output.
- Point out the progress indicators, the area/conflict counts, and the validation results.
- Open the generated `output_ddr.txt` and scroll through the sections.

### Hallucination Prevention (45 seconds)
- "The number one risk with AI-generated reports is hallucination."
- Show the extraction prompt's strict rules.
- Show the validator output — "every number and area name is cross-checked."
- "If something isn't in the source data, it says 'Not Available' instead of making something up."

### Conflict Handling (30 seconds)
- "When the two reports disagree, the system doesn't just pick one."
- Show the conflict appendix in the final report.
- "Conflicts are flagged transparently so the client knows where to investigate."

### Closing (15 seconds)
- "This is designed to be production-quality, modular, and generalizable to any inspection-style document pair."
- "Questions? Let me know."

---

## License

This project is provided as-is for demonstration and educational purposes.

---

*Built with Python, Google Gemini, Pydantic, and a strong conviction that AI should never make things up.*
