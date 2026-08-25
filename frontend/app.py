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
    .mcq-card {
        background-color: #1E1E2E;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #313244;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .mcq-question {
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
    .badge-source { background-color: #5e35b1; color: #ffffff; }
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
        options=["MCQ"],
        index=0,
        help="Additional content types (True/False, This-or-That, Fill in Blank, Guess the Number) unlock in Phase 4.",
    )

    generate_btn = st.button("🚀 Generate MCQ", type="primary", use_container_width=True)

# ── Main Content Area ───────────────────────────────────────────────────────────
if "current_item" not in st.session_state:
    st.session_state.current_item = None

if generate_btn:
    with st.spinner(f"Generating verified {difficulty} {sport} MCQ..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/generate/item",
                json={
                    "sport": sport,
                    "difficulty": difficulty,
                    "content_type": content_type,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.current_item = data.get("item")
                st.success("✨ Generated successfully!")
            else:
                st.error(f"Error {resp.status_code}: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to FastAPI backend. Ensure server is running on port 8000.")
        except Exception as err:
            st.error(f"❌ Generation request failed: {err}")

# ── Render Item Card ────────────────────────────────────────────────────────────
if st.session_state.current_item:
    item = st.session_state.current_item

    diff_class = f"badge-{item['difficulty'].lower()}"
    grounded_label = "✅ Grounded" if item.get("grounded", True) else "⚠️ Ungrounded"

    st.markdown(
        f"""
        <div class="mcq-card">
            <div style="margin-bottom: 12px;">
                <span class="badge {diff_class}">{item['difficulty']}</span>
                <span class="badge badge-surface">📱 {item.get('platform_surface', 'Story')}</span>
                <span class="badge badge-source">📚 {item.get('source', 'vector_db')}</span>
                <span class="badge badge-grounded">{grounded_label}</span>
            </div>
            <div class="mcq-question">{item['question']}</div>
        """,
        unsafe_allow_html=True,
    )

    # Render Options
    for key, text in item["options"].items():
        is_correct = key == item["correct_answer"]
        cls = "option-correct" if is_correct else "option-default"
        marker = " ✅ (Correct Answer)" if is_correct else ""
        st.markdown(
            f'<div class="option-pill {cls}"><strong>{key}:</strong> {text}{marker}</div>',
            unsafe_allow_html=True,
        )

    # Render Explanation
    st.markdown(
        f"""
            <div style="margin-top: 16px; padding: 12px; background-color: #181825; border-radius: 8px; border-left: 3px solid #89B4FA; font-size: 0.9rem; color: #CDD6F4;">
                💡 <strong>Explanation:</strong> {item['explanation']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Raw JSON & Export
    with st.expander("🔍 Inspect Schema JSON / Export Payload"):
        st.json(item)
else:
    st.info("👈 Select a sport and difficulty on the left, then click **Generate MCQ** to create your first item.")
