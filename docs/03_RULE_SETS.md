# Rule Sets
## AI-Powered Sports Engagement Content Agent

These are the concrete, enforceable rules the code must implement. Each maps to an
evaluation criterion in the assignment, or to a hiring-signal goal from the PRD (§9).

### 1. Schema Rules (Pydantic, one class per type)

**MCQSchema**
- `sport: str`, `difficulty: Literal["Easy","Medium","Hard"]`
- `question: str` (non-empty)
- `options: Dict[Literal["A","B","C","D"], str]` — exactly 4 keys, A/B/C/D, each a
  non-empty string (labeled options per the brief: *"Four answer options (A, B, C, D)"*)
- `correct_answer: Literal["A","B","C","D"]` — **must be a key present in `options`**
- `explanation: str` (non-empty, ≤ 300 chars)
- `source: Literal["web_search","vector_db","both"]`
- `platform_surface: Literal["Story","Feed","Reel Caption"]`
- `grounded: bool`

**TrueFalseSchema**
- `sport, difficulty`
- `statement: str`
- `correct_answer: bool`
- `explanation: str`
- `source: Literal["web_search","vector_db","both"]`
- `platform_surface: Literal["Story","Feed","Reel Caption"]`
- `grounded: bool`

**ThisOrThatSchema**
- `sport: str`
- `prompt: str`
- `options: List[str]` — length **must equal 2**
- `is_opinion: bool` — **must always be `True`**
- No `correct_answer` or `grounded` field permitted (not applicable — enforced by
  omitting them from the model entirely, not just leaving them null)
- `platform_surface: Literal["Story","Feed","Reel Caption"]` — defaults to `"Story"`
  (maps to the native Poll sticker)

**FillBlankSchema**
- `sport, difficulty`
- `sentence: str` — **must contain exactly one `___` blank marker**
- `options: List[str]` — length **must equal 4**
- `correct_answer: str` — must be in `options`
- `explanation: str`
- `source`, `platform_surface`, `grounded: bool`

**GuessNumberSchema**
- `sport, difficulty`
- `question: str`
- `target_number: float`
- `tolerance: float` — **must be ≥ 0**
- `explanation: str`
- `source`, `platform_surface`, `grounded: bool`

**Validation rule:** every LLM JSON response is parsed with
`Schema.model_validate(raw_json)`. On failure → capture the `ValidationError`, re-inject
it into a corrective follow-up prompt, retry once. Second failure → drop the item, log
it, generate a replacement item instead (batch count must never fall short silently).

### 2. Platform Surface Mapping Rule (baseline, not optional)
Every generated item gets a `platform_surface` tag so output is genuinely "ready to
drop into Instagram's native tools" per the Problem Statement. Deterministic lookup,
nudged by difficulty — not a separate LLM call:

| Type | Default Surface | Notes |
|---|---|---|
| MCQ | Story | Maps to native Quiz sticker |
| True/False | Story | Quick native sticker interaction |
| This-or-That | Story | Maps to native Poll sticker (2 options) |
| Fill in the Blank | Feed | Needs more reading time; caption-based |
| Guess the Number | Feed or Reel Caption | Hard → Reel caption (longer engagement); Easy/Medium → Feed |

Rule: `platform_surface` is set at generation time, not user-editable in v1.

### 3. Retrieval Routing Rules
1. `ThisOrThat` → **never retrieve**. Skip straight to generation (opinion-based).
2. `GuessNumber` and any prompt mentioning "recent/latest/this season/current" →
   **web search first**. Fall back to ChromaDB if Tavily returns nothing usable.
3. Everything else → **ChromaDB first**. Fall back to web search if similarity score
   of top result is below threshold (e.g. < 0.75) or collection is empty for that sport.
4. If **both** sources contribute to the final fact used, `source = "both"`.
5. Never call the LLM for a factual type with zero retrieved context — fail that item
   and try a different angle/question rather than let the LLM invent facts.

### 4. Prompt Template Rules
- One Python module per type under `agent/prompts/`. Each exposes
  `build_prompt(sport, difficulty, retrieved_context) -> str`.
- Every factual-type prompt **must** include:
  - Explicit instruction: "Only use facts present in the CONTEXT below. If the context
    is insufficient, say so instead of guessing."
  - The retrieved context, clearly delimited (`--- CONTEXT ---` block).
  - The exact target JSON shape.
- This-or-That prompt must **not** include a "correct answer" instruction, and must
  explicitly instruct the LLM to produce a genuinely debatable pair.
- No shared/generic mega-prompt is allowed to serve more than one type.

### 5. Grounding Verification Rule (hiring-signal requirement)
This is what turns "we told the LLM to stay grounded" into a checkable guarantee:

1. After schema validation, extract the claimed fact: `correct_answer` text (MCQ,
   True/False, Fill-in-Blank) or `target_number` (Guess-the-Number).
2. Run a match check against the retrieved context used for that item:
   - Text answers: case-insensitive substring / fuzzy match (e.g. `rapidfuzz`,
     threshold ~85%) of the answer text against the context.
   - Numeric answers: the number (or a close paraphrase of it) must appear in the
     context, within reasonable tolerance.
3. Set `grounded = True` if matched, else `False`.
4. If `grounded = False`:
   - Attempt **one** corrective regeneration, explicitly telling the LLM its previous
     answer wasn't found in the context.
   - If still ungrounded, **discard the item** and generate a different
     question/fact pair from the same retrieved context, rather than ever returning an
     item flagged as ungrounded to the user.
5. `grounded` is never shown as `False` in the final UI — it's an internal gate. The
   badge visible to the user is really "Verified ✅" on every accepted item, which is
   only true *because* of this rule. (This is the "proof, not a promise" mechanism.)
6. This check must run for every factual type. This-or-That is exempt (no fact to
   ground).

### 6. Freshness / Deduplication Rules
- Every accepted item's core text (question/statement/prompt) is embedded and stored
  in a ChromaDB `generation_history` collection, tagged with sport + type + timestamp.
- Before accepting a new item, check cosine similarity against the **last 50 items for
  that sport+type**. If similarity > 0.9 → duplicate, regenerate (max 3 tries), then
  relax slightly rather than block indefinitely.
- History persists across sessions (ChromaDB on-disk) — satisfies "avoid repeating
  across sessions."

### 7. Batch & Regeneration Rules
- A batch request always returns **4–5 items** — never fewer, even if some individual
  generations needed retries internally.
- "Mixed" batch: types assigned round-robin/random from the user-selected set before
  generation begins.
- Per-item regenerate: re-runs the full pipeline (retrieval + grounding + dedup) for
  just that one item, replaces it in place.
- Full-batch regenerate: same, for all items, honoring the original type mix.

### 8. Error Handling Rules
- Any external API failure (Tavily/Gemini/ChromaDB) → caught, logged, surfaced as a
  clear inline error on that item ("Couldn't generate this item — retry?"), never a
  silent blank card or raw stack trace.
- LLM output that isn't valid JSON → treated as a schema validation failure (retry-once
  rule applies).

### 9. Code Quality Rules
- Type hints throughout; Pydantic for all data contracts.
- No hardcoded API keys — all via `.env` / `config.py`.
- Each retrieval/LLM call wrapped with a timeout (e.g. 15s).
- Docstring on every public function explaining inputs/outputs.
- Unit tests for: schema edge cases, grounding match logic (positive + negative cases),
  dedup similarity logic, surface mapping table.

### 10. Git & Process Rules (hiring-signal requirement)
- Commit at the end of **each phase** in the Phases doc, not one giant final commit.
  Commit messages should describe *what became runnable*, e.g.
  `"Phase 2: wire retrieval + source tagging into MCQ pipeline"`.
- Keep `docs/` (this PRD/Architecture/Rules/Phases set) in the repo — it doubles as
  design documentation a reviewer can read without asking you questions.
- No committed `.env`, API keys, or `chroma_db/` data directories — `.gitignore` these.

### 11. README Rules (hiring-signal requirement)
The README is not just setup instructions. It must include, in this order:
1. One-paragraph project overview + a demo GIF/short video.
2. Setup instructions (env vars needed, `pip install`, run commands).
3. Architecture summary (can link to `docs/02_ARCHITECTURE.md`).
4. Type-specific design explanation (why separate templates per type — ties to Rules §4).
5. **How grounding/low-hallucination is enforced** (ties to Rules §5) — this is the
   single most important paragraph for the "effective use of the AI agent" criterion.
6. **Known Limitations / What I'd improve with more time** — an honest, specific list
   (e.g. "seed fact set only covers 3 sports," "grounding check is fuzzy-match, not
   semantic entailment," "no caching layer for repeated Tavily queries").
