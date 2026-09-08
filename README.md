# Rulebook AI

> **The Rulebook That Argues With Itself**

Ask a question about your institution's rulebook and get an answer that cites the exact clause it came from — or, just as importantly, an honest "the rulebook doesn't say" or "these two sections disagree."

---

## Overview

Most university regulations were never written to be read as a whole. They accumulate over years — attendance clauses, exam eligibility rules, medical exemptions, committee powers — added and amended in isolation. Read three of them together and you'll usually find a contradiction nobody noticed, because nobody reads all three at once.

Rulebook AI is a retrieval-grounded question-answering service built specifically for this failure mode. It doesn't just retrieve text and generate a plausible-sounding answer. Every response is one of three explicit outcomes — **answered**, **not covered**, or **conflicting** — and every claim is traceable to a specific section, quoted passage, and similarity score.

## Problem

Standard RAG pipelines have a quiet failure mode: if a query retrieves *any* text, the model will usually generate *an* answer, whether or not that text actually supports it. Applied to a rulebook, this creates two specific risks:

1. **False confidence.** The system answers a question the corpus never actually addresses (e.g. "what if I miss an exam for a family wedding?" when only medical absence is covered), by quietly generalizing from an adjacent clause.
2. **Silent contradiction.** Two sections disagree — one clause sets a 75% attendance threshold, another implies a different one — and the system picks whichever chunk ranked highest, hiding the disagreement from the student who needed to see it.

Rulebook AI treats both of these as first-class outcomes rather than edge cases to be smoothed over.

## Core Idea

Retrieval alone cannot tell you whether a question is answerable — it only ranks similarity. Rulebook AI adds a decision layer on top of retrieval that explicitly checks two things before generating any answer:

- **Coverage** — does the retrieved evidence actually address what was asked, or is the model about to fill a gap with inference?
- **Consistency** — do the top passages agree with each other, or are they making incompatible claims?

Only after both checks pass does the system generate a grounded answer. Otherwise, it reports the gap or the contradiction directly.

## Key Features

- **Three-way verdict system** — `ANSWERED`, `NOT_COVERED`, `CONFLICT` — chosen automatically, never left to the language model's discretion alone.
- **Every answer is cited** — section reference, quoted passage, source file, and similarity score, shown inline rather than hidden behind a click.
- **Conflict detection** — surfaces disagreeing clauses side by side instead of silently picking one.
- **Confidence scoring** — a single number reflecting how well the retrieved evidence supports the verdict, shown alongside the answer.
- **Mixed-format ingestion** — Markdown pages, PDFs, and tabular data (e.g. fee/deadline tables) are all normalized into the same searchable corpus.
- **Hybrid retrieval** — semantic + keyword search, combined so that both paraphrased and exact-term questions are handled well.
- **Adversarial evaluation set** — 25 deliberately unanswerable questions and 3 planted contradictions used to test the system's honesty, not just its recall.

## Architecture

```text
                        ┌────────────────────┐
                        │   React Frontend    │
                        │  (question + UI)     │
                        └─────────┬────────────┘
                                  │ POST /ask
                                  ▼
                        ┌────────────────────┐
                        │   FastAPI Backend    │
                        │     app/api/ask.py    │
                        └─────────┬────────────┘
                                  ▼
                 ┌────────────────────────────────┐
                 │        Retrieval Service          │
                 │  semantic search + keyword search │
                 └─────────────┬──────────────────┘
                                  ▼
                 ┌────────────────────────────────┐
                 │        Evidence Service           │
                 │  ranks & assembles top passages   │
                 └─────────────┬──────────────────┘
                        ┌───────┴────────┐
                        ▼                 ▼
            ┌─────────────────┐ ┌──────────────────┐
            │ Coverage Detector │ │ Conflict Detector  │
            └─────────┬────────┘ └─────────┬─────────┘
                        └────────┬─────────┘
                                  ▼
                        ┌────────────────────┐
                        │   Decision Engine    │
                        │ ANSWERED / NOT_COVERED│
                        │      / CONFLICT        │
                        └─────────┬────────────┘
                                  ▼
                        ┌────────────────────┐
                        │  Answer Generator     │
                        │ (grounded, cited)      │
                        └────────────────────┘
```

The pipeline, end to end:

```text
Question
   │
   ▼
Hybrid Retrieval ── semantic search + keyword search
   │
   ▼
Evidence Analysis ── rank, deduplicate, assemble top-k passages
   │
   ▼
Coverage Detection ── does the evidence actually address the question?
   │
   ▼
Conflict Detection ── do the top passages disagree with each other?
   │
   ▼
Decision Engine ── ANSWERED | NOT_COVERED | CONFLICT
   │
   ▼
Grounded Response + Evidence
```

## Retrieval Strategy

Retrieval is **hybrid** rather than purely semantic, because rulebook language mixes two very different question styles:

- **Paraphrased, conversational questions** ("what if I miss an exam for a family thing?") — handled well by dense embedding similarity, since the wording rarely matches the source text.
- **Precise, term-anchored questions** ("what is the attendance percentage for semester exams?") — where exact keyword overlap (section numbers, defined terms like "eligibility," "waiver," "condonation") is often a stronger signal than embedding distance alone.

The two retrieval paths run independently and their results are merged and re-ranked before being passed to the evidence service, so a question doesn't lose relevant clauses just because it leans conversational or leans precise.

## Conflict Detection

Conflict detection runs on the **top-ranked evidence set**, not on the whole corpus, for every query:

1. The top passages retrieved for a question are compared pairwise for semantic overlap on the same subject (e.g. two clauses both discussing attendance thresholds).
2. Where overlap is high but the extracted claims diverge (different numeric thresholds, different conditions, or one clause implicitly overriding another), the pair is flagged as a candidate conflict.
3. Candidate conflicts are verified before being surfaced, so that two clauses which merely *mention* the same topic without actually disagreeing are not misreported as conflicting.
4. On a confirmed conflict, the response returns **both** passages, their sections, and a plain-language description of how they disagree — the system does not attempt to adjudicate which clause "wins."

## Three Core Outcomes

| Status | Meaning | What the response contains |
|---|---|---|
| `ANSWERED` | One or more clauses directly and consistently address the question | Grounded answer + cited evidence + confidence score |
| `NOT_COVERED` | Retrieved evidence exists but doesn't actually address what was asked | An explicit "the rulebook doesn't say" + a reason, not a guess |
| `CONFLICT` | Two or more sections address the question but disagree | Both conflicting passages, cited side by side, with no single answer forced |

## Demo Conflict Scenarios

Three contradictions are deliberately planted in the corpus to exercise conflict detection:

1. **Attendance threshold conflict** — the core academic regulations set a 75% attendance requirement to sit an exam, while a medical-exemption clause elsewhere implies a different effective threshold for affected students.
2. **Eligibility vs. waiver authority conflict** — one section states attendance eligibility is final once published, while a separate committee-powers clause grants a body the authority to waive that same requirement after the fact.
3. **Fee-deadline conflict** — the fee schedule table lists one late-payment cutoff, while a narrative policy section elsewhere describes a grace period that extends past that same cutoff.

*(See `data/evaluation/conflicts.json` for the exact section references, quoted text, and expected system behavior for each.)*

## Corpus

- **Size:** 6,000+ words of rulebook content.
- **Formats:** Markdown pages, at least one PDF, and at least one table (e.g. fee/deadline schedule) — mixed intentionally, so ingestion has to normalize across formats rather than assume plain text.
- **Source:** institution-style academic regulations (attendance, examinations, medical exemptions, committee powers, fees), either drawn from public regulations or authored to represent a realistic rulebook.
- **Planted contradictions:** 3, documented in `data/evaluation/conflicts.json`.
- **Adversarial question set:** 25 questions the corpus deliberately cannot answer, in `data/evaluation/questions.json` — plausible, adjacent questions a student would actually ask (e.g. a non-medical excuse, when only medical exemptions are covered).

Raw source files live under `data/raw/` (`markdown/`, `pdf/`, `tables/`); normalized, chunked output is written to `data/processed/`.

## Ingestion Pipeline

`backend/scripts/ingest.py` drives ingestion end to end:

1. **Load** — read every file under `data/raw/` by type (Markdown, PDF, table).
2. **Normalize** — convert each format into plain text with preserved section metadata (heading, section number, source file, page number where applicable).
3. **Chunk** — split normalized text into overlapping passages sized for retrieval (`app/services/chunking.py`), keeping section boundaries intact so a chunk doesn't straddle two unrelated clauses.
4. **Embed** — generate vector embeddings for each chunk (`app/services/embeddings.py`).
5. **Index** — write chunks and embeddings into the vector store (`vector_store/chroma/`), alongside metadata used later for citations.

`backend/scripts/rebuild_index.py` re-runs ingestion from scratch when the corpus changes.

## Evidence and Citations

Every non-`NOT_COVERED` response returns an `evidence` array. Each entry includes:

- `section` — the clause's section heading or number
- `text` — the exact quoted passage
- `source_file` — which corpus file it came from
- `page` — page number, when the source is a PDF
- `similarity` — the retrieval similarity score for that passage

The frontend renders this evidence inline, next to the answer, rather than behind a collapsed panel — the design intent is that a student can verify the answer without extra clicks.

## Confidence

The confidence score reported alongside each answer reflects how strongly the retrieved evidence supports the chosen verdict — a function of top-passage similarity, agreement across the retrieved set, and (for `ANSWERED` responses) how directly the passage addresses the question, not a measure of the language model's own certainty in its phrasing. Low confidence on an `ANSWERED` result is a signal worth reading the evidence for, not a bug.

## Tech Stack

**Backend**
- FastAPI (Python) — `POST /ask` endpoint
- Vector store: Chroma (`vector_store/chroma/`)
- Embeddings + retrieval services under `app/services/`
- Pydantic models for request/response schemas (`app/models/`)

**Frontend**
- React + Vite
- `react-markdown` for rendering answer text
- Plain CSS (no framework dependency) using a shared design-token palette

**Data**
- Markdown, PDF, and tabular sources normalized into a single processed corpus

## Project Structure

```text
rulebook-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI routes (POST /ask)
│   │   ├── core/                 # config, logging
│   │   ├── models/                # request/response/document schemas
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   ├── chunking.py
│   │   │   ├── embeddings.py
│   │   │   ├── vector_store.py
│   │   │   ├── retrieval.py
│   │   │   ├── evidence.py
│   │   │   ├── coverage_detector.py
│   │   │   ├── conflict_detector.py
│   │   │   └── answer_generator.py
│   │   └── utils/
│   ├── scripts/
│   │   ├── ingest.py
│   │   ├── rebuild_index.py
│   │   └── evaluate.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/            # Header, QuestionInput, AnswerCard, EvidenceList, etc.
│   │   ├── services/api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   └── package.json
│
├── data/
│   ├── raw/{markdown,pdf,tables}/
│   ├── processed/
│   └── evaluation/{questions.json,conflicts.json,expected_answers.json}
│
├── docs/{architecture.md,api.md,evaluation.md,decisions.md}
├── vector_store/chroma/
├── README.md
└── LICENSE
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- `pip`, `npm`

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in any required config/API keys
python scripts/ingest.py         # builds the vector index from data/raw/
uvicorn app.main:app --reload    # starts the API on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # starts the dev server, default http://localhost:5173
```

Set the backend URL the frontend calls in `frontend/src/services/api.js` (defaults to `http://localhost:8000`).

## API Documentation

### `POST /ask`

**Request**

```json
{
  "question": "What happens if I miss an exam for a family wedding?"
}
```

**Response — answered**

```json
{
  "status": "ANSWERED",
  "answer": "Students may request a re-examination only for documented medical emergencies...",
  "confidence": 0.82,
  "reason": null,
  "evidence": [
    {
      "chunk_id": "sec-4-2-01",
      "section": "4.2 Medical Exemptions",
      "text": "A student who is unable to sit an examination due to a documented medical emergency may apply for a re-examination...",
      "source_file": "university_rulebook_part2.md",
      "page": null,
      "similarity": 0.78
    }
  ]
}
```

**Response — not covered**

```json
{
  "status": "NOT_COVERED",
  "answer": null,
  "confidence": 0.31,
  "reason": "The rulebook only defines exemptions for documented medical emergencies; non-medical personal absences (e.g. family events) are not addressed.",
  "evidence": []
}
```

**Response — conflict**

```json
{
  "status": "CONFLICT",
  "answer": null,
  "confidence": 0.65,
  "reason": "Section 3.2 sets a 75% attendance threshold, while Section 4.2's medical exemption implies a lower effective threshold for affected students.",
  "evidence": [
    { "chunk_id": "sec-3-2-01", "section": "3.2 Attendance-Based Eligibility", "text": "...", "source_file": "university_rulebook_part1.md", "similarity": 0.81 },
    { "chunk_id": "sec-4-2-03", "section": "4.2 Medical Exemptions", "text": "...", "source_file": "university_rulebook_part2.md", "similarity": 0.74 }
  ]
}
```

Full request/response schemas are in `app/models/request.py` and `app/models/response.py`; a narrative walkthrough is in `docs/api.md`.

## Testing

```bash
cd backend
pytest tests/
```

`tests/test_core.py` covers the retrieval, coverage, and conflict-detection services in isolation, independent of any specific corpus content, so the logic can be validated without re-running full ingestion.

## Evaluation Dataset

`data/evaluation/` holds the adversarial test set used to validate the system's honesty, not just its recall:

- `questions.json` — 25 plausible, adjacent questions the corpus cannot answer (expected verdict: `NOT_COVERED`).
- `conflicts.json` — the 3 planted contradictions, with expected verdict `CONFLICT` and the section pairs each should surface.
- `expected_answers.json` — expected verdicts/answers for a set of genuinely answerable questions, used as a positive control.

Run the full evaluation with:

```bash
python backend/scripts/evaluate.py
```

This reports, per question, whether the system's verdict matched the expected one — the metric that matters here is verdict accuracy (did it correctly choose `ANSWERED` / `NOT_COVERED` / `CONFLICT`), not just answer quality.

## Design Decisions

- **Verdict is a first-class field, not a side effect.** The decision engine chooses the outcome explicitly before generation runs, so the language model is never in a position to "decide" whether a question is answerable by simply producing text.
- **Coverage and conflict checks run on the same evidence set**, sequentially, so a question can't be marked `ANSWERED` on the strength of passages that merely resemble the question rather than address it.
- **Citations are shown inline, not on demand.** Hiding evidence behind a click makes it too easy to trust the headline answer without checking it — this system is only useful if verification is effortless.
- **Conflicts are reported, not resolved.** The system deliberately does not pick a "winning" clause when two sections disagree — that's a judgment call for the institution, not the model.
- **Mixed corpus formats are normalized at ingestion, not at query time**, so retrieval and citation logic don't need to know whether a passage originally came from Markdown, a PDF, or a table.

## Limitations

- Conflict detection is scoped to the top-ranked evidence per query; a contradiction between two low-ranked, rarely-retrieved clauses may not surface unless a question specifically targets both.
- Coverage and conflict judgments depend on embedding quality; ambiguous phrasing in the source rulebook can occasionally produce a borderline verdict.
- The system assumes the ingested corpus is the full source of truth — it cannot know about verbal policy, unwritten precedent, or amendments not yet reflected in the documents.
- Confidence scores are a relative signal for comparing responses, not a calibrated probability of correctness.

## Future Improvements

- Corpus-wide conflict pre-computation (an offline pass that flags all contradiction pairs, not just ones surfaced by a specific query).
- Section-level versioning, so amendments can be tracked and superseded clauses flagged automatically.
- Multi-turn follow-up questions that stay grounded in the same evidence set.
- Admin view for institutions to review and annotate flagged conflicts before they're shown to students.

## Security Notes

- `.env` holds any API keys or secrets and is git-ignored; only `.env.example` (with placeholder values) is committed.
- The API does not execute or evaluate user input beyond passing it to retrieval — no code execution paths are exposed.
- Uploaded/ingested corpus files are trusted institutional documents; the ingestion pipeline does not accept arbitrary user-uploaded files at query time.

## Demo Flow

1. Open the frontend and ask one of the suggested questions (e.g. the attendance threshold).
2. Show the `ANSWERED` response with its cited clause and confidence score.
3. Ask one of the 25 adversarial questions (e.g. the family-wedding exam question) to show `NOT_COVERED`.
4. Ask a question that touches the planted attendance/medical-exemption contradiction to show `CONFLICT`, with both clauses shown side by side.
5. Briefly show `data/evaluation/` and `scripts/evaluate.py` to demonstrate the test set backing these behaviors.

## Project Philosophy

A confident wrong answer is worse than an honest "I don't know" — and a silently-resolved contradiction is worse than both, because it looks authoritative while hiding a real disagreement someone needs to see. Rulebook AI is built around that ordering: correctness of *verdict* comes before fluency of *answer*.

## License

This project is licensed under the MIT License — see `LICENSE` for details.