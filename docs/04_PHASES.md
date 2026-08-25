# Phased Build Plan
## AI-Powered Sports Engagement Content Agent

Each phase produces something *runnable*, so we test as we go, and each phase ends
with a **git commit** (Rules doc §10) so the commit history itself becomes evidence of
process — useful if this project gets discussed in an interview.

---
### Phase 0 — Setup (foundation)
- Repo structure created (per Architecture doc).
- `.env.example`, `requirements.txt`, `config.py`, `.gitignore` (env, chroma data).
- Get free API keys: Gemini (Google AI Studio) + Tavily.
- ChromaDB installed, confirm a local collection can be created/queried.
- **Exit check:** test script hits Gemini and Tavily and prints a response.
- **Commit:** `"Phase 0: project scaffold + API connectivity confirmed"`

### Phase 1 — Single-type vertical slice (MCQ only, no retrieval yet)
- Pydantic `MCQSchema` (with labeled A/B/C/D options).
- `agent/prompts/mcq.py` with no-retrieval prompt.
- Orchestrator: generate → validate → return, no retries yet.
- FastAPI route `/generate/item` (single MCQ).
- Minimal Streamlit page: sport dropdown + "Generate MCQ" button + JSON display.
- **Exit check:** clicking the button returns one schema-valid MCQ in the UI.
- **Commit:** `"Phase 1: MCQ vertical slice, no retrieval yet"`

### Phase 2 — Add retrieval (web search + ChromaDB) for MCQ
- `retrieval/web_search.py` (Tavily wrapper).
- `retrieval/vector_store.py` (ChromaDB wrapper) + seed facts for 2–3 sports.
- Wire routing rules (Rules §3) into the orchestrator for MCQ only.
- Source tag flows through to the UI.
- **Exit check:** MCQ answers visibly use retrieved facts; source badge correct;
  disconnecting one source still degrades gracefully to the other.
- **Commit:** `"Phase 2: retrieval + source tagging wired into MCQ pipeline"`

### Phase 3 — Grounding verification (hiring-signal core, do this before scaling to
### all 5 types — it's the most important phase to get right)
- `agent/grounding.py`: fact-match logic (text substring/fuzzy + numeric proximity).
- Wire grounding check + corrective retry + discard-and-retry into orchestrator
  (Rules §5), for MCQ first.
- Unit tests: grounding check correctly flags a deliberately-wrong test case as
  ungrounded, and a correct one as grounded.
- **Exit check:** feed the orchestrator a deliberately mismatched context/answer pair
  in a test — confirm it's caught and never reaches the UI.
- **Commit:** `"Phase 3: grounding verification layer, tested against wrong-answer case"`

### Phase 4 — Remaining 4 content types + platform surface tagging
- Schemas + prompt templates for True/False, This-or-That, Fill-in-Blank,
  Guess-the-Number (Rules §1).
- Extend grounding check to all factual types.
- `platform_surface` field + deterministic mapping (Rules §2) wired into every type.
- Extend routing rules and orchestrator dispatch by type.
- UI: content-type selector supports all 5; each card shows source, grounded, and
  surface badges.
- **Exit check:** each type generates a valid, correctly-shaped, grounded item with
  a surface tag.
- **Commit:** `"Phase 4: all 5 content types + platform surface tagging"`

### Phase 5 — Batch generation + regeneration
- `/generate/batch` endpoint: 4–5 items, single or mixed types.
- Per-item regenerate + full-batch regenerate endpoints and UI buttons.
- Schema-retry and grounding-retry logic fully exercised at batch scale.
- **Exit check:** a mixed batch of 5 renders correctly; regenerating one item only
  replaces that card; forced failures (bad LLM output / ungrounded answer) are retried
  transparently without shrinking the batch.
- **Commit:** `"Phase 5: batch generation + per-item/full regeneration"`

### Phase 6 — Freshness / deduplication
- `generation_history` ChromaDB collection.
- Similarity check before accepting an item (Rules §6).
- Test: generate the same sport+type+difficulty batch twice, confirm low overlap.
- **Exit check:** repeated requests produce materially different content; history
  persists after restarting the app.
- **Commit:** `"Phase 6: dedup/freshness via persistent ChromaDB history"`

### Phase 7 — USP feature + dashboard polish
- Pick **one** differentiator — must reflect real product thinking, not cosmetics:
  - **Freshness/Grounding Analytics view** (recommended) — shows, per session: % of
    items grounded on first try vs after retry, source mix (web/vector/both),
    duplicate-rejection count, surface distribution. This directly visualizes the
    hiring-signal work from Phases 3 & 6 — it turns invisible engineering into
    something a reviewer can *see* and appreciate in 10 seconds.
  - Alternative: difficulty auto-balancer across a batch.
  - Alternative: "streak mode" chaining related questions into a mini narrative.
- Clean card layout, badges, copy-to-clipboard/export as JSON or IG-caption-formatted
  text.
- **Exit check:** USP feature works end-to-end and is visually obvious in the demo.
- **Commit:** `"Phase 7: USP feature — [chosen feature] + UI polish"`

### Phase 8 — Testing, README, submission polish
- Full test suite: schema edge cases, grounding positive/negative cases, dedup logic,
  retrieval fallback logic, surface mapping.
- README written per Rules §11 — overview, demo GIF, setup, architecture summary,
  type-specific design rationale, grounding explanation, **Known Limitations** section.
- Record a 2–3 min demo GIF/video, embed in README.
- Final pass on code comments/docstrings.
- Confirm `docs/` folder (this PRD/Architecture/Rules/Phases) is committed.
- **Exit check:** fresh clone + `.env` fill-in + `pip install -r requirements.txt` +
  run instructions works end-to-end, no manual fixes needed.
- **Commit:** `"Phase 8: tests, README, demo — submission ready"`

---
### Suggested Order of Attack
Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, strictly in order. Note Phase 3 (grounding)
is deliberately placed **before** scaling to all 5 types — it's the highest-leverage
phase for the hiring outcome, so get it right once on MCQ before replicating the
pattern everywhere in Phase 4.
