# ⚡ StapuBox AI Sports Engagement Content Agent

A production-grade, full-stack AI content agent and interactive dashboard designed for sports content creators and social media managers on Instagram. The agent synthesizes **real-time web search** (Tavily API) and a **curated on-disk ChromaDB knowledge base** to generate 5 distinct formats of Instagram-ready engagement content across 5 sports (`Cricket`, `Football`, `Tennis`, `Badminton`, `Basketball`) with deterministic platform surface placement, verifiable anti-hallucination fact checking, persistent semantic deduplication, and a live **Freshness & Grounding Analytics** dashboard.

---

## 🎬 Quick Demo Preview

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  ⚡ StapuBox Sports Engagement Content Agent                                           │
│  [Sport: Cricket ▼]  [Difficulty: Medium ▼]  [Mode: Mixed Batch (5 Items) ▼]           │
│  [ 🚀 Generate Content ]                                                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  #1 MCQ [MEDIUM] [📱 STORY] [📚 VECTOR_DB] [✅ VERIFIED GROUNDED]                      │
│  "Which legendary bowler holds the world record for the highest number of Test wickets?"│
│  [A] Shane Warne          [B] Muttiah Muralitharan ✅ (Correct)                         │
│  [C] James Anderson       [D] Anil Kumble                                              │
│  💡 Explanation: Muttiah Muralitharan took 800 wickets in 133 Test matches.            │
│                                                                                        │
│  #2 TRUE/FALSE [EASY] [📱 STORY] [📚 VECTOR_DB] [✅ VERIFIED GROUNDED]                 │
│  "Wimbledon is the only Grand Slam tournament played on natural grass courts."         │
│  [Correct Answer: TRUE ✅]                                                             │
│                                                                                        │
│  #3 THIS-OR-THAT [MEDIUM] [📱 STORY] [🗳️ OPINION POLL]                                 │
│  "Prime CR7 (2012) vs Prime Messi (2012): Who was more unstoppable?"                  │
│  [ 🅰️ Prime Cristiano Ronaldo ]  VS  [ 🅱️ Prime Lionel Messi ]                         │
│                                                                                        │
│  #4 FILL IN THE BLANK [MEDIUM] [📱 FEED] [📚 VECTOR_DB] [✅ VERIFIED GROUNDED]          │
│  "Rohit Sharma holds the world record for highest ODI score with ___ runs."            │
│  [264 ✅]  [200]  [219]  [237]                                                         │
│                                                                                        │
│  #5 GUESS THE NUMBER [HARD] [📱 REEL CAPTION] [🌐 WEB_SEARCH] [✅ VERIFIED GROUNDED]   │
│  "Can you guess how many total points Wilt Chamberlain scored in his 1962 record game?"│
│  [ Target: 100.0 (± 0.0) ]                                                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup & Quickstart Instructions

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- API Keys:
  - **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))
  - **Tavily Web Search API Key** ([Tavily AI](https://tavily.com/))

### 2. Installation
Clone the repository and install dependencies:
```bash
# 1. Clone repository
git clone https://github.com/your-username/stapubox-sports-agent.git
cd stapubox-sports-agent

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and enter your API keys:
```bash
cp .env.example .env
```

Ensure `.env` contains the required keys:
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
TAVILY_API_KEY=your_tavily_api_key_here
CHROMA_PERSIST_DIR=./data/chroma_db
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
API_TIMEOUT_SECONDS=15
```

### 4. Running the Application
Launch both the FastAPI backend and Streamlit dashboard in separate terminal tabs:

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Streamlit Frontend:**
```bash
streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`.

---

## 🏗️ Architecture & Data Flow

Detailed specifications and architectural contracts are documented in [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md).

```
┌────────────────────────────────────────────────────────┐
│                  STREAMLIT FRONTEND                    │
│   (Sports, Difficulty, Batch & Format Controls, Cards, │
│    One-Click JSON Export, Live Telemetry Visualizer)   │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP REST (JSON)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                      │
│   (/generate/batch, /generate/item, /regenerate, etc.) │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR AGENT                              │
│  1. Retrieval Router (Rules §3: Vector DB vs Web Search vs None)      │
│  2. Isolated Prompt Module Dispatch (mcq, true_false, this_or_that...)│
│  3. LLM Generation (Gemini 2.0 Flash / Swappable Client)              │
│  4. Pydantic v2 Schema Validation (with automatic error retry)        │
│  5. 2-Stage Anti-Hallucination Grounding Gate (Rules §5)               │
│     -> Exact Substring / RapidFuzz Fuzzy / Numeric Proximity Check    │
│     -> Corrective LLM Prompt on failure -> Discard & Replace guard    │
│  6. Deterministic Platform Surface Tagging (Rules §2)                 │
│  7. Cosine Semantic Deduplication (Rules §6: ChromaDB History)        │
└──────────────┬───────────────────────────┬────────────────────────────┘
               ▼                           ▼
 ┌──────────────────────────┐   ┌─────────────────────────────┐
 │     RETRIEVAL LAYER      │   │         LLM CLIENT          │
 │  • ChromaDB Knowledge DB │   │  • Google GenAI SDK         │
 │  • Tavily Web Search API │   │  • Gemini 2.0 Flash         │
 │  • Persistent History    │   │  • Swappable (Claude/OpenAI)│
 └──────────────────────────┘   └─────────────────────────────┘
```

---

## 🧩 Type-Specific Design Rationale

Unlike naive implementations that rely on a single, fragile "mega-prompt", this system uses **strictly isolated prompt modules** per content format (`backend/agent/prompts/`):

| Content Type | Schema Contract | Grounding Strategy | Instagram Surface Placement |
|---|---|---|---|
| **MCQ** | Exactly 4 options labeled `A, B, C, D`, `correct_answer` in options | Verified text matching of the correct option in context | **Story** (native Instagram Quiz sticker) |
| **True/False** | `statement: str`, `correct_answer: bool`, explanation | Token set and fuzzy ratio verification against context | **Story** (quick Poll / Quiz sticker interaction) |
| **This-or-That** | Exactly 2 choices, `is_opinion: True`, NO `correct_answer`/`grounded` fields | **Exempt from retrieval** (pure opinion debate) | **Story** (native 2-choice Poll sticker) |
| **Fill in the Blank** | Sentence with exactly one `___` blank, 4 options, `correct_answer` | Substring match of missing word/phrase in context | **Feed** (requires caption reading time) |
| **Guess the Number** | `question: str`, `target_number: float`, `tolerance >= 0` | Numerical extraction & ±2% proximity check in context | **Feed** (Easy/Med) or **Reel Caption** (Hard) |

---

## 🛡️ How Grounding & Hallucination Prevention is Enforced

The core differentiator of this agent is **verifiable grounding, not claimed grounding**. We do not merely ask the LLM to "be truthful"; we enforce a deterministic 2-stage verification gate ([`backend/agent/grounding.py`](backend/agent/grounding.py)):

```
LLM Output ──▶ Pydantic Validation ──▶ Grounding Verification
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
              [Fact in Context]                              [Fact NOT in Context]
              Mark Grounded ✅                                        │
              Accept & Store                                          ▼
                                                          1. Corrective Retry Prompt
                                                          ("Answer not in context, retry")
                                                                      │
                                                      ┌───────────────┴───────────────┐
                                                      ▼                               ▼
                                              [Passes Retry]                  [Still Fails]
                                              Mark Grounded ✅                Discard Item &
                                              Accept & Store                  Generate Replacement
```

1. **Extraction:** After schema validation, the agent extracts the core factual claim (`correct_answer` text for MCQ / Fill in Blank, statement tokens for True/False, or `target_number` float for Guess the Number).
2. **Deterministic Match Verification:**
   - **Text Claims:** Case-insensitive substring matching + `RapidFuzz` partial and token-set ratio scoring (threshold $\ge 85\%$).
   - **Numeric Claims:** Regular-expression numerical extraction from context and proximity tolerance verification ($\le 2\%$).
3. **Corrective Retry & Discard Safeguard:**
   - If ungrounded on attempt 1, a corrective feedback prompt explicitly instructs the LLM that its previous answer was missing from the evidence.
   - If the corrective retry remains ungrounded, the item is **discarded** and replaced with a fresh context/fact pair. Unverified factual claims are never surfaced to the creator.
4. **Telemetry:** All attempts, retry recoveries, and discards are tracked in real-time and visualized in the **Analytics** view.

---

## 🔄 Persistent Semantic Deduplication

To guarantee fresh, non-repetitive content across creator sessions:
1. Every accepted item's core text is embedded using `all-MiniLM-L6-v2` and indexed in an on-disk ChromaDB collection (`./data/chroma_db`).
2. Before accepting any new item, the agent queries the last 50 items for that sport and content type.
3. If cosine similarity $> 0.90$, the candidate is rejected as a duplicate, incrementing the telemetry counter and triggering regeneration.
4. History persists across application restarts.

---

## 📊 USP Feature: Freshness & Grounding Analytics View

The dashboard includes a dedicated **Analytics Tab** pulling live telemetry from `GET /analytics`:
- **Real-Time Grounding Verification Rate:** Live percentage of generated items passing anti-hallucination checks.
- **First-Try vs Retry Recovery Ratio:** Transparency into how often corrective prompt self-healing succeeded.
- **Deduplication Rejection Counter:** Real-time count of semantic duplicates caught and discarded.
- **Source Breakdown:** Ratio of items powered by the curated Vector Knowledge Base vs live Tavily Web Search.
- **Platform Surface Allocation:** Distribution of content tailored for Story stickers, Feed captions, and Reel captions.

---

## 🧪 Comprehensive Test Suite

Run the full automated test suite (30 unit & integration tests) covering schema edge cases, grounding positive/negative assertions, numeric extraction, surface mapping, and deduplication:

```bash
pytest tests/ -v
```

### Test Breakdown:
- `tests/test_schemas.py`: Structural validation across all 5 Pydantic schemas.
- `tests/test_grounding.py`: Positive matches, deliberate hallucination rejections, fuzzy matching, and numeric parsing.
- `tests/test_surface_mapping.py`: Deterministic Instagram surface lookup matrix.
- `tests/test_dedup.py`: Cosine similarity thresholds and persistent on-disk history.
- `tests/test_orchestrator.py`: FastAPI endpoints, error handling, and routing rules.

---

## ⚠️ Known Limitations & Future Roadmap

*An honest engineering assessment of trade-offs and areas for production enhancement:*

1. **Static Seed Dataset Scope:**
   - *Current:* 90 curated seed facts across 5 sports (18 facts each) stored in `data/seed_facts/*.json`.
   - *Production Improvement:* Connect automated scrapers to official sports feeds (ESPN API, Sportmonks, Cricinfo) to continuously hydrate the ChromaDB knowledge base.
2. **Grounding Verification Approach:**
   - *Current:* High-performance deterministic substring, `RapidFuzz` token-set ratio, and numeric proximity matching.
   - *Production Improvement:* Integrate a lightweight Natural Language Inference (NLI) cross-encoder (e.g. `DeBERTa-v3-nli`) for deep semantic entailment on complex multi-hop claims without LLM overhead.
3. **Retrieval Caching:**
   - *Current:* Live queries are made directly to Tavily Web Search when recency flags or fallback conditions trigger.
   - *Production Improvement:* Add a Redis TTL caching layer for popular sports queries to minimize API cost and latency.
4. **Export Formats:**
   - *Current:* JSON export and clipboard copying.
   - *Production Improvement:* Provide direct CSV / Buffer / Hootsuite CSV scheduling templates and native image card rendering (Pillow/Canvas) for direct Story sticker overlay export.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app & REST endpoints
│   ├── config.py                # Pydantic environment configuration
│   ├── agent/
│   │   ├── orchestrator.py      # Core agent loop (routing, LLM, grounding, dedup, batch)
│   │   ├── grounding.py         # Grounding verification engine (RapidFuzz + numeric)
│   │   ├── surface_mapping.py   # Deterministic Instagram placement rules
│   │   ├── schemas.py           # Pydantic v2 schemas across all 5 content formats
│   │   └── prompts/             # Isolated prompt templates
│   │       ├── mcq.py
│   │       ├── true_false.py
│   │       ├── this_or_that.py
│   │       ├── fill_blank.py
│   │       └── guess_number.py
│   ├── retrieval/
│   │   ├── vector_store.py      # ChromaDB wrapper (knowledge base & dedup history)
│   │   └── web_search.py        # Tavily Search API wrapper
│   └── llm/
│       └── client.py            # Swappable LLM client wrapper (Gemini 2.0 Flash)
├── frontend/
│   └── app.py                   # Streamlit dashboard & Freshness Analytics view
├── data/
│   └── seed_facts/              # Curated sports facts (Cricket, Football, Tennis, Badminton, Basketball)
├── tests/                       # Complete pytest suite (30 tests)
├── docs/                        # PRD, Architecture, Rules, and Phased Plan specifications
├── scripts/
│   └── test_phase0.py           # Phase 0 connectivity verification script
├── .env.example
├── requirements.txt
└── README.md
```

---

## 📜 License
MIT License. Built for the StapuBox AI Product/Engineer Assignment.
