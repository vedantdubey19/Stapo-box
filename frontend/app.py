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
        padding: 24px;
        border: 1px solid #313244;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #CDD6F4;
        margin-bottom: 16px;
    }
    .option-pill {
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 0.95rem;
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
        font-size: 0.78rem;
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
        gap: 16px;
        margin: 16px 0;
    }
    .this-that-box {
        flex: 1;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
        background: #181825;
        border: 2px solid #89B4FA;
        color: #CDD6F4;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .number-highlight {
        font-size: 1.8rem;
        font-weight: 800;
        color: #F9E2AF;
        padding: 12px 20px;
        background: #181825;
        border-radius: 8px;
        display: inline-block;
        margin: 10px 0;
        border: 1px dashed #F9E2AF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">⚡ StapuBox Sports Engagement Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered, grounded Instagram trivia, polls, and interactive content generator across 5 sports</div>',
    unsafe_allow_html=True,
)

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

    content_type = st.selectbox(
        "Content Type",
        options=[
            "MCQ",
            "True/False",
            "This-or-That",
            "Fill in the Blank",
            "Guess the Number",
        ],
        index=0,
    )

    topic_hint = st.text_input("Optional Topic / Recency Hint (e.g. '2024 champions', 'World Cup')", "")

    generate_btn = st.button(f"🚀 Generate {content_type}", type="primary", use_container_width=True)

# ── Session State Initialization ───────────────────────────────────────────────
if "current_item" not in st.session_state:
    st.session_state.current_item = None
if "current_type" not in st.session_state:
    st.session_state.current_type = "MCQ"

# ── Main Content Action ─────────────────────────────────────────────────────────
if generate_btn:
    with st.spinner(f"Generating verified {difficulty} {sport} {content_type}..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/generate/item",
                json={
                    "sport": sport,
                    "difficulty": difficulty,
                    "content_type": content_type,
                    "topic_hint": topic_hint if topic_hint.strip() else None,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.current_item = data.get("item")
                st.session_state.current_type = data.get("content_type", content_type)
                st.success("✨ Content generated successfully!")
            else:
                st.error(f"Error {resp.status_code}: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to FastAPI backend. Ensure server is running on port 8000.")
        except Exception as err:
            st.error(f"❌ Generation request failed: {err}")

# ── Render Card by Content Type ─────────────────────────────────────────────────
if st.session_state.current_item:
    item = st.session_state.current_item
    c_type = st.session_state.current_type

    diff = item.get("difficulty", "Medium")
    diff_class = f"badge-{diff.lower()}"
    surface = item.get("platform_surface", "Story")
    source = item.get("source", "vector_db")

    st.markdown('<div class="item-card">', unsafe_allow_html=True)

    # Header Badges
    badge_html = f"""
    <div style="margin-bottom: 14px;">
        <span class="badge badge-type">🏷️ {c_type}</span>
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

    # 1. MCQ Renderer
    if c_type == "MCQ":
        st.markdown(f'<div class="card-title">{item["question"]}</div>', unsafe_allow_html=True)
        for key, text in item["options"].items():
            is_correct = key == item["correct_answer"]
            cls = "option-correct" if is_correct else "option-default"
            marker = " ✅ (Correct Answer)" if is_correct else ""
            st.markdown(
                f'<div class="option-pill {cls}"><strong>{key}:</strong> {text}{marker}</div>',
                unsafe_allow_html=True,
            )

    # 2. True / False Renderer
    elif c_type == "True/False":
        st.markdown(f'<div class="card-title">"{item["statement"]}"</div>', unsafe_allow_html=True)
        ans_bool = item["correct_answer"]
        ans_label = "TRUE" if ans_bool else "FALSE"
        cls = "option-correct"
        st.markdown(
            f'<div class="option-pill {cls}"><strong>Correct Answer:</strong> {ans_label}</div>',
            unsafe_allow_html=True,
        )

    # 3. This-or-That Renderer
    elif c_type == "This-or-That":
        st.markdown(f'<div class="card-title">🗳️ {item["prompt"]}</div>', unsafe_allow_html=True)
        opt1, opt2 = item["options"][0], item["options"][1]
        st.markdown(
            f"""
            <div class="this-that-container">
                <div class="this-that-box">🅰️ {opt1}</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #89B4FA; align-self: center;">VS</div>
                <div class="this-that-box">🅱️ {opt2}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Fill in the Blank Renderer
    elif c_type == "Fill in the Blank":
        st.markdown(f'<div class="card-title">{item["sentence"]}</div>', unsafe_allow_html=True)
        for opt in item["options"]:
            is_correct = opt == item["correct_answer"]
            cls = "option-correct" if is_correct else "option-default"
            marker = " ✅ (Correct Answer)" if is_correct else ""
            st.markdown(
                f'<div class="option-pill {cls}">{opt}{marker}</div>',
                unsafe_allow_html=True,
            )

    # 5. Guess the Number Renderer
    elif c_type == "Guess the Number":
        st.markdown(f'<div class="card-title">🔢 {item["question"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="number-highlight">Target: {item["target_number"]} (± {item.get("tolerance", 0)})</div>',
            unsafe_allow_html=True,
        )

    # Explanation section (for factual types)
    if "explanation" in item:
        st.markdown(
            f"""
            <div style="margin-top: 16px; padding: 12px; background-color: #181825; border-radius: 8px; border-left: 3px solid #89B4FA; font-size: 0.9rem; color: #CDD6F4;">
                💡 <strong>Explanation:</strong> {item['explanation']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Raw JSON
    with st.expander("🔍 Inspect Schema JSON"):
        st.json(item)
else:
    st.info("👈 Select a sport, difficulty, and content type on the left, then click **Generate** to create your item.")
