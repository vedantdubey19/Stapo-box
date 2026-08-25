"""Streamlit Frontend Dashboard for Sports Engagement Content Agent."""

import json
import requests
import streamlit as st

# ── Page Configuration ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StapuBox Sports Content Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = "http://127.0.0.1:8000"

# ── Custom Styling ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B, #FF8533);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #888888;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .item-card {
        background-color: #1E1E2E;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #313244;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #CDD6F4;
        margin-bottom: 14px;
        line-height: 1.4;
    }
    .option-pill {
        padding: 8px 14px;
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 0.92rem;
        font-weight: 500;
    }
    .option-default {
        background-color: #181825;
        border: 1px solid #45475A;
        color: #BAC2DE;
    }
    .option-correct {
        background-color: rgba(166, 227, 161, 0.15);
        border: 1.5px solid #A6E3A1;
        color: #A6E3A1;
        font-weight: 700;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 700;
        margin-right: 6px;
        text-transform: uppercase;
    }
    .badge-easy { background-color: #2e7d32; color: #ffffff; }
    .badge-medium { background-color: #e65100; color: #ffffff; }
    .badge-hard { background-color: #c62828; color: #ffffff; }
    .badge-surface { background-color: #3b4252; color: #eceff4; }
    .badge-grounded { background-color: #00897b; color: #ffffff; }
    .badge-opinion { background-color: #f39c12; color: #ffffff; }
    .badge-source { background-color: #5e35b1; color: #ffffff; }
    .badge-type { background-color: #2b3a4a; color: #89B4FA; border: 1px solid #89B4FA; }
    .this-that-container {
        display: flex;
        gap: 12px;
        margin: 12px 0;
    }
    .this-that-box {
        flex: 1;
        padding: 14px;
        border-radius: 8px;
        text-align: center;
        background: #181825;
        border: 2px solid #89B4FA;
        color: #CDD6F4;
        font-size: 1rem;
        font-weight: 700;
    }
    .number-highlight {
        font-size: 1.5rem;
        font-weight: 800;
        color: #F9E2AF;
        padding: 10px 16px;
        background: #181825;
        border-radius: 8px;
        display: inline-block;
        margin: 8px 0;
        border: 1px dashed #F9E2AF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">⚡ StapuBox Sports Engagement Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered, grounded Instagram trivia, polls, and interactive content generator</div>',
    unsafe_allow_html=True,
)

# ── Session State Initialization ───────────────────────────────────────────────
if "batch_items" not in st.session_state:
    st.session_state.batch_items = []
if "last_params" not in st.session_state:
    st.session_state.last_params = {}

# ── Sidebar Controls ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Generation Settings")

    sport = st.selectbox(
        "Select Sport",
        options=["Cricket", "Football", "Tennis", "Badminton", "Basketball"],
        index=0,
    )

    difficulty = st.selectbox(
        "Difficulty Level",
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
            "Include Content Types",
            options=["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"],
            default=["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"],
        )

    topic_hint = st.text_input("Optional Focus / Recency Hint", "")

    generate_btn = st.button("🚀 Generate Content", type="primary", use_container_width=True)

# ── Batch Generation Handler ────────────────────────────────────────────────────
if generate_btn:
    st.session_state.last_params = {
        "sport": sport,
        "difficulty": difficulty,
        "types": selected_types or ["MCQ"],
        "topic_hint": topic_hint,
    }

    with st.spinner(f"Generating verified {difficulty} {sport} content batch..."):
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
                    timeout=45,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.batch_items = data.get("items", [])
                    st.success(f"✨ Successfully generated {len(st.session_state.batch_items)} items!")
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
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.batch_items = [{
                        "id": "single_0",
                        "content_type": data.get("content_type"),
                        "item": data.get("item"),
                    }]
                    st.success("✨ Generated single item successfully!")
                else:
                    st.error(f"Error {resp.status_code}: {resp.text}")
        except Exception as err:
            st.error(f"❌ Generation request failed: {err}")

# ── Render Batch Actions & Items ────────────────────────────────────────────────
if st.session_state.batch_items:
    top_col1, top_col2, top_col3 = st.columns([2, 1, 1])
    with top_col1:
        st.subheader(f"📋 Generated Batch ({len(st.session_state.batch_items)} Items)")
    with top_col2:
        if st.button("🔄 Regenerate Full Batch", use_container_width=True):
            params = st.session_state.last_params
            with st.spinner("Regenerating full batch..."):
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
                        timeout=45,
                    )
                    if resp.status_code == 200:
                        st.session_state.batch_items = resp.json().get("items", [])
                        st.rerun()
                except Exception as e:
                    st.error(f"Regeneration failed: {e}")
    with top_col3:
        batch_json_str = json.dumps([b["item"] for b in st.session_state.batch_items], indent=2)
        st.download_button(
            label="💾 Export Batch JSON",
            data=batch_json_str,
            file_name=f"sports_batch_{sport.lower()}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Render each item card
    for idx, wrapper in enumerate(st.session_state.batch_items):
        item = wrapper["item"]
        c_type = wrapper["content_type"]
        item_id = wrapper["id"]

        diff = item.get("difficulty", "Medium")
        diff_class = f"badge-{diff.lower()}"
        surface = item.get("platform_surface", "Story")
        source = item.get("source", "vector_db")

        st.markdown('<div class="item-card">', unsafe_allow_html=True)

        header_col, action_col = st.columns([5, 1])
        with header_col:
            badge_html = f"""
            <div style="margin-bottom: 10px;">
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
            if st.button(f"🔄 Redo", key=f"regen_btn_{item_id}", help="Regenerate only this item"):
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
                            timeout=25,
                        )
                        if resp.status_code == 200:
                            new_wrapper = resp.json().get("item")
                            st.session_state.batch_items[idx] = new_wrapper
                            st.rerun()
                        else:
                            st.error(f"Error: {resp.text}")
                    except Exception as err:
                        st.error(f"Failed to regenerate item: {err}")

        # Item Card Content
        if c_type == "MCQ":
            st.markdown(f'<div class="card-title">{item["question"]}</div>', unsafe_allow_html=True)
            for key, text in item["options"].items():
                is_correct = key == item["correct_answer"]
                cls = "option-correct" if is_correct else "option-default"
                marker = " ✅ (Correct Answer)" if is_correct else ""
                st.markdown(f'<div class="option-pill {cls}"><strong>{key}:</strong> {text}{marker}</div>', unsafe_allow_html=True)

        elif c_type == "True/False":
            st.markdown(f'<div class="card-title">"{item["statement"]}"</div>', unsafe_allow_html=True)
            ans_label = "TRUE" if item["correct_answer"] else "FALSE"
            st.markdown(f'<div class="option-pill option-correct"><strong>Correct Answer:</strong> {ans_label}</div>', unsafe_allow_html=True)

        elif c_type == "This-or-That":
            st.markdown(f'<div class="card-title">🗳️ {item["prompt"]}</div>', unsafe_allow_html=True)
            opt1, opt2 = item["options"][0], item["options"][1]
            st.markdown(
                f"""
                <div class="this-that-container">
                    <div class="this-that-box">🅰️ {opt1}</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #89B4FA; align-self: center;">VS</div>
                    <div class="this-that-box">🅱️ {opt2}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif c_type == "Fill in the Blank":
            st.markdown(f'<div class="card-title">{item["sentence"]}</div>', unsafe_allow_html=True)
            for opt in item["options"]:
                is_correct = opt == item["correct_answer"]
                cls = "option-correct" if is_correct else "option-default"
                marker = " ✅ (Correct Answer)" if is_correct else ""
                st.markdown(f'<div class="option-pill {cls}">{opt}{marker}</div>', unsafe_allow_html=True)

        elif c_type == "Guess the Number":
            st.markdown(f'<div class="card-title">🔢 {item["question"]}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="number-highlight">Target: {item["target_number"]} (± {item.get("tolerance", 0)})</div>',
                unsafe_allow_html=True,
            )

        if "explanation" in item:
            st.markdown(
                f"""
                <div style="margin-top: 12px; padding: 10px; background-color: #181825; border-radius: 8px; border-left: 3px solid #89B4FA; font-size: 0.88rem; color: #CDD6F4;">
                    💡 <strong>Explanation:</strong> {item['explanation']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("🔍 Inspect Full Batch JSON"):
        st.json([b["item"] for b in st.session_state.batch_items])
else:
    st.info("👈 Select your settings on the left and click **Generate Content** to create a batch of 5 interactive items.")
