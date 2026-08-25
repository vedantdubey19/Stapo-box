# Architecture Document
## AI-Powered Sports Engagement Content Agent

### 1. High-Level Diagram (textual)

```
┌─────────────────────┐
│   Streamlit UI       │  sport / difficulty / type selectors
│  (frontend/app.py)   │  batch view, regenerate buttons, source + surface +
└──────────┬───────────┘  grounding badges
           │ HTTP (requests)
           ▼
┌─────────────────────┐
│   FastAPI Backend     │  /generate/batch  /generate/item  /regenerate
│   (backend/main.py)   │
└──────────┬───────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR / AGENT LAYER                    │
│  (backend/agent/orchestrator.py)                                │
│  1. Decide retrieval need (fresh fact? historical fact?         │
│     opinion — skip retrieval)                                   │
│  2. Call Retrieval Layer                                        │
│  3. Pick type-specific template                                 │
│  4. Call LLM with retrieved context                             │
│  5. Validate output against Pydantic schema                     │
│  6. GROUNDING CHECK: verify correct_answer/key fact actually     │
│     appears in retrieved context (string/fuzzy match) →          │
│     sets `grounded: bool`. If not grounded, retry once with a    │
│     corrective prompt before falling back to a new question.     │
│  7. Assign platform_surface via deterministic lookup              │
│  8. Check dedup store → if duplicate, regenerate                  │
└───────────┬───────────────────────────┬─────────────────────┘
            ▼                           ▼
 ┌────────────────────┐      ┌────────────────────────┐
 │  RETRIEVAL LAYER     │      │   LLM CLIENT             │
 │                      │      │   (Gemini 2.0 Flash,      │
 │ ┌─────────────────┐ │      │    swappable to           │
 │ │ Web Search Tool  │ │      │    OpenAI/Claude)          │
 │ │ (Tavily API)     │ │      └────────────────────────┘
 │ │ → fresh/live facts│ │
 │ └─────────────────┘ │
 │ ┌─────────────────┐ │
 │ │ ChromaDB          │ │
 │ │ (local vector DB) │ │
 │ │ → stable/historical│ │
 │ │   facts + generated│ │
 │ │   item history      │ │
 │ │   (dedup store)      │ │
 │ └─────────────────┘ │
 └────────────────────┘
```

### 2. Component Responsibilities

**Frontend (Streamlit)**
- Pure presentation + user input. No business logic.
- Calls backend REST endpoints, renders returned JSON as cards.
- Shows badges per item: 🌐 Web / 📚 Vector DB / 🌐📚 Both source; ✅ Grounded /
  ⚠️ Ungrounded (should be rare — see Rules §5); Story/Feed/Reel surface tag.

**Backend (FastAPI)**
- Thin HTTP layer. Routes: `POST /generate/batch`, `POST /generate/item`,
  `POST /regenerate/item`, `POST /regenerate/batch`.
- Delegates everything to the Orchestrator.

**Orchestrator (the actual "agent")**
- The brain: decides retrieval strategy per content type, invokes retrieval, builds the
  type-specific prompt, calls the LLM, validates, **grounding-checks**, assigns surface,
  dedups.
- This is where "grounding" and "low hallucination" requirements are enforced concretely
  — the grounding check is what turns "we prompted the LLM to only use context" (a
  claim) into "we verified the output matches the context" (a proof).

**Grounding Verification (new component)**
- `agent/grounding.py`: takes the LLM's claimed `correct_answer` (or key numeric fact
  for Guess-the-Number) and the retrieved context string, checks for a match (exact
  substring for text answers; numeric proximity check for Guess-the-Number).
- Sets `grounded=True/False` on the item. If `False`, one corrective retry is attempted
  ("your answer wasn't found in the provided context, regenerate using only the
  context"). If still ungrounded after retry, the item is discarded and a fresh
  question/context pair is tried instead of ever surfacing an unverified factual claim.
- This is intentionally simple (string/fuzzy match, not another LLM call) — cheap,
  deterministic, explainable in an interview.

**Retrieval Layer**
- `web_search.py`: wraps Tavily API. Used for recency-sensitive queries.
- `vector_store.py`: wraps ChromaDB. Used for stable facts, pre-seeded with a curated
  fact set per sport. Also the **dedup store** (embeds every accepted item's core text).

**Retrieval routing** (heuristic, documented in Rules §3):
- Guess-the-Number & recency-flavored queries → web search first, fallback vector DB.
- General/historical facts → vector DB first, fallback web search.
- This-or-That → no retrieval (opinion-based by design).

**LLM Client**
- Thin wrapper so the model provider is swappable (`GEMINI` / `OPENAI` / `CLAUDE` via
  env var) without touching orchestrator logic.

**Schema Validation**
- Pydantic models, one per content type, mirroring the brief's "Expected Output"
  section exactly, plus `grounded` and `platform_surface`.

### 3. Proposed Folder Structure
```
stapubox-sports-agent/
├── backend/
│   ├── main.py                  # FastAPI app + routes
│   ├── agent/
│   │   ├── orchestrator.py
│   │   ├── grounding.py         # grounding verification logic
│   │   ├── surface_mapping.py   # platform_surface lookup
│   │   ├── prompts/
│   │   │   ├── mcq.py
│   │   │   ├── true_false.py
│   │   │   ├── this_or_that.py
│   │   │   ├── fill_blank.py
│   │   │   └── guess_number.py
│   │   └── schemas.py           # Pydantic models per type
│   ├── retrieval/
│   │   ├── web_search.py
│   │   └── vector_store.py
│   ├── llm/
│   │   └── client.py
│   └── config.py
├── frontend/
│   └── app.py                   # Streamlit dashboard
├── data/
│   └── seed_facts/              # curated per-sport fact seeds for ChromaDB
├── tests/
│   ├── test_schemas.py
│   ├── test_grounding.py
│   └── test_dedup.py
├── .env.example
├── requirements.txt
├── README.md                    # setup + architecture + limitations + demo gif
└── docs/                        # this PRD/Architecture/Rules/Phases set, kept in repo
```

### 4. Data Flow Example (MCQ, Cricket, Medium)
1. UI sends `{sport: "Cricket", difficulty: "Medium", types: ["MCQ"], count: 5}`.
2. Orchestrator queries ChromaDB for cricket facts at that difficulty; if
   insufficient/stale, calls Tavily for recent cricket news.
3. Builds MCQ-specific prompt with retrieved snippets injected.
4. Calls LLM → gets JSON.
5. Validates against `MCQSchema`.
6. Grounding check: is `correct_answer`'s underlying fact present in the retrieved
   context? If not, one corrective retry, else discard and retry with fresh retrieval.
7. Assigns `platform_surface` via the deterministic type/difficulty lookup.
8. Embeds the question, checks similarity against last N stored questions in ChromaDB
   dedup collection; if too similar, regenerate.
9. Stores accepted item in ChromaDB dedup collection.
10. Returns validated item + source tag + grounded flag + surface tag to frontend.

### 5. Why this architecture satisfies the brief (and the hiring bar)
- **Type-specific templates** → separate prompt module per type.
- **Schema validation** → Pydantic model per type, enforced before returning.
- **Source citation** → every retrieval call tags its origin, carried to output.
- **Freshness/diversity** → ChromaDB doubles as a dedup/history store.
- **Web search + vector DB combo** → explicit routing logic, not "always search."
- **Platform-surface matching** → deterministic tag on every item.
- **Verifiable grounding** → a concrete, explainable mechanism (not just prompt
  wording) that a reviewer can point at and ask "how do you know it's not
  hallucinating?" and get a real answer.
