# Product Requirements Document (PRD)
## AI-Powered Sports Engagement Content Agent — StapuBox Assignment

### 1. Overview
An AI agent + dashboard that generates ready-to-post, text-based Instagram engagement
content (quizzes, polls, challenges) for sports content creators. The agent combines
**live web search** (recent/fast-changing facts) with a **ChromaDB vector store**
(stable/historical facts) to ground every factual claim, generates content through
**type-specific templates**, and validates every output against a strict schema before
returning it.

This PRD is written with a second objective in mind, alongside functional correctness:
**this project is also a hiring signal.** Every section below flags where correctness
alone is not enough and product/engineering judgment is expected to show.

### 2. Goals
- Give a creator a one-stop tool to generate a *batch* of varied interactive content
  (not just repetitive MCQs) for a chosen sport and difficulty.
- Ensure factual content (MCQ, T/F, Fill-in-blank, Guess-the-Number) is grounded in
  retrieved evidence, with the source (web search vs vector DB) visible per item, and
  a **verifiable, low hallucination rate** — not just a claimed one.
- Keep This-or-That polls clearly separated as opinion-based, never fact-checked.
- Guarantee structurally valid output every time (no malformed JSON reaching the UI).
- Avoid repeating the same question/fact across sessions.
- Match content to the right Instagram surface (Story / Feed / Reel Caption).
- Demonstrate product thinking through one genuine USP feature the brief didn't ask for.

### 3. Non-Goals
- No image generation or image sourcing — text only.
- No direct Instagram API posting — output is copy-paste/export ready.
- No user accounts / multi-tenant auth — single-user local tool is sufficient.

### 4. Target User
A sports content creator / social media manager who wants fresh interactive content
without manually researching stats each time. (For this assignment: the evaluator,
acting as that user — and separately, as a hiring reviewer.)

### 5. Core User Flow
1. User opens the dashboard.
2. User selects: **Sport**, **Difficulty** (Easy/Medium/Hard), **Content type(s)**
   (single type or "mixed batch").
3. User clicks **Generate Batch** → agent researches (web search + ChromaDB) → generates
   4–5 items → each factual item is grounding-checked → schema-validated → rendered.
4. User can **regenerate a single item** or **regenerate the whole batch**.
5. Each factual item shows: source tag (Web Search / Vector DB / Both), a short
   explanation, a **suggested platform surface**, and a **grounding confidence
   indicator**.
6. User can copy/export the batch as text or JSON for pasting into Instagram tools.

### 6. Functional Requirements (from assignment brief)
- Sport selector (Cricket, Football, Tennis, Badminton, Basketball, + extensible list)
- Difficulty selector (Easy / Medium / Hard)
- Content type selector: MCQ, True/False, This-or-That, Fill in the Blank
  (4 labeled options), Guess the Number
- Batch generation: 4–5 items, optionally mixed types
- Per-item regenerate + full-batch regenerate
- Every factual type grounded in retrieved knowledge; polls exempt
- Freshness: no repeated question/fact across sessions

### 7. Output Schema (summary — full schema in Rules doc)
| Type | Required Fields |
|---|---|
| MCQ | sport, difficulty, question, options {A,B,C,D: str}, correct_answer (A/B/C/D), explanation, source, platform_surface, grounded (bool) |
| True/False | sport, difficulty, statement, correct_answer(bool), explanation, source, platform_surface, grounded (bool) |
| This-or-That | sport, prompt, 2 options, is_opinion=true, platform_surface |
| Fill in the Blank | sport, difficulty, sentence_with_blank, 4 options, correct_answer, explanation, source, platform_surface, grounded (bool) |
| Guess the Number | sport, difficulty, question, target_number, tolerance_range, explanation, source, platform_surface, grounded (bool) |

`grounded: bool` is new — see §9. It records whether the accepted answer was verified
present in the retrieved context, not just generated alongside it.

### 8. Success Metrics (functional, mirrors evaluation criteria)
- 0 schema-invalid items reach the UI
- Every factual item has a non-empty, correct source citation
- No duplicate question/fact within recent generations (dedup check passes)
- Full batch generates in a reasonable time (target: <20s for 5 items)
- Clean separation of prompt templates per type

### 9. Hiring-Signal Success Criteria (beyond the brief)
These are the differentiators from a hiring standpoint — treated as first-class
requirements in this build, not polish:

- **Verifiable grounding, not claimed grounding.** After generation, a lightweight
  check confirms the `correct_answer`/key fact actually appears in the retrieved
  context before the item is accepted (see Architecture §2, Rules §5). The
  `grounded` flag on each item is the visible proof of this to an evaluator.
- **One real USP**, chosen because it reflects understanding of the creator's actual
  problem (repetitive content, no visibility into freshness), not cosmetic polish.
- **README that explains trade-offs**, not just setup steps — includes a "Known
  Limitations / What I'd improve with more time" section.
- **A demo (GIF or short video)** embedded in the README so evaluators don't have to
  run the project to understand it.
- **A commit history that tells the build story** (matches the Phases doc), not one
  squashed commit — signals real engineering process.

### 10. Assumptions
- Single local user, no auth needed.
- Free-tier APIs (Gemini + Tavily) are sufficient for demo-scale usage.
- ChromaDB runs embedded/local (no separate server needed).

### 11. Open Questions for Stakeholder (you)
- Fixed sport list or free-text entry?
- Export format beyond copy/JSON (e.g. CSV)?
- Final USP pick (see Phases doc §6)?
