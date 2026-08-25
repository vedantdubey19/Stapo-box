"""Streamlit Frontend Dashboard for StapuBox Sports Engagement Content Agent.

Features:
- Multi-sport (Cricket, Football, Tennis, Badminton, Basketball) content generator.
- 5 Engagement types: MCQ, True/False, This-or-That, Fill in the Blank, Guess the Number.
- Deterministic Instagram platform surface matching (Story, Feed, Reel Caption).
- Real-time Freshness & Grounding Analytics dashboard (USP).
- One-click copy-to-clipboard and JSON batch export.
"""

import json
import requests
import streamlit as st
import pandas as pd

# ── Page Configuration ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StapuBox Sports Content Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = "http://127.0.0.1:8000"

# ── Custom Design System & CSS Styling ──────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Global Container */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Header Gradient & Typography */
    .hero-header {
        background: linear-gradient(135deg, #1E1E2E 0%, #2A2B3D 100%);
        border: 1px solid #3B3C52;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF5E62 0%, #FF9966 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .hero-desc {
        color: #A6ADC8;
        font-size: 1.05rem;
        margin-bottom: 0;
    }

    /* Content Cards */
    .content-card {
        background-color: #181825;
        border-radius: 14px;
        padding: 22px 24px;
        border: 1px solid #313244;
        margin-bottom: 18px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .content-card:hover {
        border-color: #585B70;
    }
    .card-heading {
        font-size: 1.2rem;
        font-weight: 700;
        color: #CDD6F4;
        margin-bottom: 14px;
        line-height: 1.45;
    }

    /* Option Pills */
    .option-pill {
        padding: 10px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
        font-size: 0.94rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .option-default {
        background-color: #11111B;
        border: 1px solid #313244;
        color: #BAC2DE;
    }
    .option-correct {
        background-color: rgba(166, 227, 161, 0.12);
        border: 1.5px solid #A6E3A1;
        color: #A6E3A1;
        font-weight: 700;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-right: 6px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-easy { background-color: #059669; color: #FFFFFF; }
    .badge-medium { background-color: #D97706; color: #FFFFFF; }
    .badge-hard { background-color: #DC2626; color: #FFFFFF; }
    .badge-surface { background-color: #4338CA; color: #EEF2FF; }
    .badge-grounded { background-color: #0D9488; color: #FFFFFF; }
    .badge-opinion { background-color: #D97706; color: #FFFFFF; }
    .badge-source { background-color: #7C3AED; color: #FFFFFF; }
    .badge-type { background-color: #1E293B; color: #38BDF8; border: 1px solid #0284C7; }

    /* This or That Layout */
    .this-that-container {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 16px;
        align-items: center;
        margin: 16px 0;
    }
    .this-that-box {
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        background: #11111B;
        border: 2px solid #38BDF8;
        color: #F8FAFC;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .vs-circle {
        background: #38BDF8;
        color: #0F172A;
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 0.9rem;
    }

    /* Number Highlight */
    .number-highlight {
        font-size: 1.6rem;
        font-weight: 800;
        color: #FCD34D;
        padding: 12px 20px;
        background: #11111B;
        border-radius: 10px;
        display: inline-block;
        margin: 10px 0;
        border: 1px dashed #F59E0B;
    }

    /* Explanation Box */
    .explanation-box {
        margin-top: 14px;
        padding: 12px 16px;
        background-color: #11111B;
        border-radius: 8px;
        border-left: 3px solid #38BDF8;
        font-size: 0.88rem;
        color: #CBD5E1;
        line-height: 1.4;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #181825;
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #313244;
        text-align: center;
    }
    .metric-val {
        font-size: 2rem;
        font-weight: 800;
        color: #38BDF8;
        margin-bottom: 4px;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">⚡ StapuBox Sports Engagement Content Agent</div>
        <div class="hero-desc">Production AI agent generating verified, Instagram-ready sports trivia, polls, and challenges with real-time grounding analytics.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Session State Initialization ───────────────────────────────────────────────
if "batch_items" not in st.session_state:
    st.session_state.batch_items = []
if "last_params" not in st.session_state:
    st.session_state.last_params = {}

# ── Sidebar Controls ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Content Controls")

    sport = st.selectbox(
        "Sport",
        options=["Cricket", "Football", "Tennis", "Badminton", "Basketball"],
        index=0,
    )

    difficulty = st.selectbox(
        "Difficulty Tier",
        options=["Easy", "Medium", "Hard"],
        index=1,
    )

    gen_mode = st.radio("Generation Mode", ["Mixed Batch (5 Items)", "Single Content Type"], index=0)

    selected_types = []
    single_type = "MCQ"
    if gen_mode == "Single Content Type":
        single_type = st.selectbox(
            "Content Type",
            options=["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"],
            index=0,
        )
        selected_types = [single_type]
    else:
        selected_types = st.multiselect(
            "Included Formats",
            options=["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"],
            default=["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"],
        )

    topic_hint = st.text_input("Optional Focus / Recency Topic", placeholder="e.g. 2024 World Cup, records")

    generate_btn = st.button("🚀 Generate Content", type="primary", use_container_width=True)

# ── Tabs Navigation ─────────────────────────────────────────────────────────────
tab_gen, tab_analytics = st.tabs(["⚡ Content Generator", "📊 Freshness & Grounding Analytics (USP)"])

# ── Tab 1: Content Generator ────────────────────────────────────────────────────
with tab_gen:
    if generate_btn:
        st.session_state.last_params = {
            "sport": sport,
            "difficulty": difficulty,
            "types": selected_types or ["MCQ"],
            "topic_hint": topic_hint,
        }

        with st.spinner(f"Researching and generating verified {difficulty} {sport} content..."):
            try:
                if gen_mode == "Mixed Batch (5 Items)":
                    resp = requests.post(
                        f"{BACKEND_URL}/generate/batch",
                        json={
                            "sport": sport,
                            "difficulty": difficulty,
                            "count": 5,
                            "content_types": selected_types or ["MCQ"],
                            "topic_hint": topic_hint if topic_hint.strip() else None,
                        },
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.batch_items = data.get("items", [])
                        st.success(f"✨ Successfully created batch of {len(st.session_state.batch_items)} items!")
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                else:
                    resp = requests.post(
                        f"{BACKEND_URL}/generate/item",
                        json={
                            "sport": sport,
                            "difficulty": difficulty,
                            "content_type": single_type,
                            "topic_hint": topic_hint if topic_hint.strip() else None,
                        },
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.batch_items = [{
                            "id": "single_0",
                            "content_type": data.get("content_type"),
                            "item": data.get("item"),
                        }]
                        st.success("✨ Single item generated successfully!")
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
            except requests.exceptions.ReadTimeout:
                st.error("⏳ Generation timed out while awaiting rate-pacing slots on the free-tier model. Please try again.")
            except Exception as err:
                st.error(f"❌ Backend connection failed: {err}")

    # Render Batch Output
    if st.session_state.batch_items:
        action_col1, action_col2, action_col3 = st.columns([3, 1.2, 1.2])
        with action_col1:
            st.subheader(f"📋 Generated Content ({len(st.session_state.batch_items)} Items)")
        with action_col2:
            if st.button("🔄 Refresh Entire Batch", use_container_width=True):
                params = st.session_state.last_params
                with st.spinner("Regenerating full batch (pacing requests for rate limits)..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/generate/batch",
                            json={
                                "sport": params.get("sport", "Cricket"),
                                "difficulty": params.get("difficulty", "Medium"),
                                "count": 5,
                                "content_types": params.get("types", ["MCQ"]),
                                "topic_hint": params.get("topic_hint"),
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            st.session_state.batch_items = resp.json().get("items", [])
                            st.rerun()
                    except requests.exceptions.ReadTimeout:
                        st.error("⏳ Batch refresh timed out while awaiting rate-pacing slots. Please retry.")
                    except Exception as e:
                        st.error(f"Batch refresh failed: {e}")
        with action_col3:
            batch_json_str = json.dumps([b["item"] for b in st.session_state.batch_items], indent=2)
            st.download_button(
                label="💾 Export JSON",
                data=batch_json_str,
                file_name=f"{sport.lower()}_engagement_batch.json",
                mime="application/json",
                use_container_width=True,
            )

        # Render Individual Cards
        for idx, wrapper in enumerate(st.session_state.batch_items):
            item = wrapper["item"]
            c_type = wrapper["content_type"]
            item_id = wrapper["id"]

            diff = item.get("difficulty", "Medium")
            diff_class = f"badge-{diff.lower()}"
            surface = item.get("platform_surface", "Story")
            source = item.get("source", "vector_db")

            st.markdown('<div class="content-card">', unsafe_allow_html=True)

            header_col, action_col = st.columns([5.5, 1])
            with header_col:
                badge_html = f"""
                <div style="margin-bottom: 12px;">
                    <span class="badge badge-type">#{idx+1} {c_type}</span>
                    <span class="badge {diff_class}">{diff}</span>
                    <span class="badge badge-surface">📱 {surface}</span>
                """
                if c_type == "This-or-That":
                    badge_html += '<span class="badge badge-opinion">🗳️ Opinion Poll</span>'
                else:
                    badge_html += f'<span class="badge badge-source">📚 {source}</span>'
                    badge_html += '<span class="badge badge-grounded">✅ Verified Grounded</span>'
                badge_html += "</div>"
                st.markdown(badge_html, unsafe_allow_html=True)

            with action_col:
                if st.button(f"🔄 Redo", key=f"btn_redo_{item_id}", help="Regenerate only this item"):
                    with st.spinner("Regenerating..."):
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/regenerate/item",
                                json={
                                    "sport": item.get("sport", sport),
                                    "difficulty": diff,
                                    "content_type": c_type,
                                    "topic_hint": topic_hint if topic_hint.strip() else None,
                                },
                                timeout=60,
                            )
                            if resp.status_code == 200:
                                new_wrapper = resp.json().get("item")
                                st.session_state.batch_items[idx] = new_wrapper
                                st.rerun()
                            else:
                                st.error(f"Error: {resp.text}")
                        except requests.exceptions.ReadTimeout:
                            st.error("⏳ Item regeneration timed out while awaiting rate-pacing slots. Please retry.")
                        except Exception as err:
                            st.error(f"Failed to regenerate: {err}")

            # Specific Type Card Renders
            if item.get("error"):
                st.markdown(f'<div class="card-heading" style="color: #f87171;">⚠️ Couldn\'t generate this item</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.75rem;">{item.get("message", "Upstream rate limit or temporary timeout. Click Redo to regenerate.")}</div>', unsafe_allow_html=True)

            elif c_type == "MCQ":
                st.markdown(f'<div class="card-heading">{item["question"]}</div>', unsafe_allow_html=True)
                for key, text in item["options"].items():
                    is_correct = key == item["correct_answer"]
                    cls = "option-correct" if is_correct else "option-default"
                    marker = " ✅ (Correct Answer)" if is_correct else ""
                    st.markdown(f'<div class="option-pill {cls}"><span><strong>{key}:</strong> {text}</span><span>{marker}</span></div>', unsafe_allow_html=True)

            elif c_type == "True/False":
                st.markdown(f'<div class="card-heading">"{item["statement"]}"</div>', unsafe_allow_html=True)
                ans_label = "TRUE" if item["correct_answer"] else "FALSE"
                st.markdown(f'<div class="option-pill option-correct"><strong>Correct Answer:</strong> {ans_label}</div>', unsafe_allow_html=True)

            elif c_type == "This-or-That":
                st.markdown(f'<div class="card-heading">🗳️ {item["prompt"]}</div>', unsafe_allow_html=True)
                opt1, opt2 = item["options"][0], item["options"][1]
                st.markdown(
                    f"""
                    <div class="this-that-container">
                        <div class="this-that-box">🅰️ {opt1}</div>
                        <div class="vs-circle">VS</div>
                        <div class="this-that-box">🅱️ {opt2}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            elif c_type == "Fill in the Blank":
                st.markdown(f'<div class="card-heading">{item["sentence"]}</div>', unsafe_allow_html=True)
                for opt in item["options"]:
                    is_correct = opt == item["correct_answer"]
                    cls = "option-correct" if is_correct else "option-default"
                    marker = " ✅ (Correct Answer)" if is_correct else ""
                    st.markdown(f'<div class="option-pill {cls}"><span>{opt}</span><span>{marker}</span></div>', unsafe_allow_html=True)

            elif c_type == "Guess the Number":
                st.markdown(f'<div class="card-heading">🔢 {item["question"]}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="number-highlight">Target: {item["target_number"]} (± {item.get("tolerance", 0)})</div>',
                    unsafe_allow_html=True,
                )

            if "explanation" in item:
                st.markdown(
                    f"""
                    <div class="explanation-box">
                        💡 <strong>Explanation:</strong> {item['explanation']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🔍 Inspect Full Batch Raw JSON"):
            st.json([b["item"] for b in st.session_state.batch_items])
    else:
        st.info("👈 Select your desired sport, difficulty, and format mix on the left, then click **Generate Content**.")


# ── Tab 2: Freshness & Grounding Analytics (USP) ────────────────────────────────
with tab_analytics:
    st.subheader("📊 Real-Time Freshness & Grounding Telemetry")
    st.caption("Live metrics capturing anti-hallucination verification loops, semantic deduplication, and platform distribution.")

    try:
        analytics_resp = requests.get(f"{BACKEND_URL}/analytics", timeout=5)
        if analytics_resp.status_code == 200:
            stats = analytics_resp.json()

            # KPI Grid
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-val">{stats.get('total_items_generated', 0)}</div>
                        <div class="metric-label">Items Generated</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-val">{stats.get('grounding_success_rate_pct', 100)}%</div>
                        <div class="metric-label">Grounding Verification Rate</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-val">{stats.get('grounded_first_try', 0)} / {stats.get('grounded_after_retry', 0)}</div>
                        <div class="metric-label">1st Try vs Retry Grounded</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi4:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-val">{stats.get('dedup_rejections', 0)}</div>
                        <div class="metric-label">Duplicates Filtered</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Distribution Breakdown Charts
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("#### 🌐 Retrieval Knowledge Sources")
                sources_data = stats.get("sources", {})
                if sources_data and any(sources_data.values()):
                    df_sources = pd.DataFrame(
                        list(sources_data.items()),
                        columns=["Source", "Count"],
                    ).set_index("Source")
                    st.bar_chart(df_sources, color="#7C3AED")
                else:
                    st.info("Generate content to populate source metrics.")

            with chart_col2:
                st.markdown("#### 📱 Instagram Platform Surface Placement")
                surfaces_data = stats.get("surfaces", {})
                if surfaces_data and any(surfaces_data.values()):
                    df_surfaces = pd.DataFrame(
                        list(surfaces_data.items()),
                        columns=["Surface", "Count"],
                    ).set_index("Surface")
                    st.bar_chart(df_surfaces, color="#38BDF8")
                else:
                    st.info("Generate content to populate platform surface metrics.")

            # Architectural Note
            st.markdown(
                """
                ---
                ##### 🛡️ How Anti-Hallucination & Deduplication Work Behind the Scenes:
                1. **2-Stage Grounding Verification:** Every generated factual claim is string/fuzzy-checked against retrieved context. If ungrounded, an automatic corrective prompt is triggered. If still ungrounded, the item is discarded and replaced.
                2. **Cosine Semantic Deduplication:** Every accepted item is embedded and indexed in ChromaDB. New candidate questions with cosine similarity > 0.90 are automatically rejected and regenerated.
                """
            )
        else:
            st.error("Failed to load telemetry stats from backend.")
    except Exception as e:
        st.warning(f"Could not connect to analytics endpoint: {e}")
