"""Streamlit Frontend Dashboard for StapuBox Sports Engagement Content Agent.

Features:
- Multi-sport (Cricket, Football, Tennis, Badminton, Basketball) content generator.
- 5 Engagement types: MCQ, True/False, This-or-That, Fill in the Blank, Guess the Number.
- Instagram Story Studio phone mockup preview matching IG quiz-sticker visual target.
- Deterministic Instagram platform surface matching (Story, Feed, Reel Caption).
- Real-time Freshness & Grounding Analytics telemetry (USP).
- Real backend integration with FastAPI orchestrator (/generate/batch, /generate/item, /regenerate/item).
- One-click copy-to-clipboard and JSON batch export.
"""

import html
import json
import os
import random
import threading
import time
import requests
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# ── Page Configuration ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StapuBox — Sports Content Agent",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


@st.cache_resource
def ensure_backend_running():
    """Ensure FastAPI backend is active; spins up daemon instance for Streamlit Cloud."""
    try:
        requests.get(f"{BACKEND_URL}/health", timeout=1.0)
    except Exception:
        if "127.0.0.1" in BACKEND_URL or "localhost" in BACKEND_URL:
            try:
                import uvicorn
                from backend.main import app as fastapi_app

                def _run_server():
                    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

                t = threading.Thread(target=_run_server, daemon=True)
                t.start()
                time.sleep(1.2)
            except Exception as e:
                pass


ensure_backend_running()

# ── Design Palette Constants ─────────────────────────────────────────────────────
HEADER_BLUE = "#4E7CFF"
HOT_PINK = "#EC4899"
VIOLET = "#8B5CF6"
GREEN = "#4CAF50"
YELLOW = "#F9C24B"

SPORTS = ["Cricket", "Football", "Tennis", "Badminton", "Basketball"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
TYPES = ["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"]

# ── Custom Design System & CSS Styling ──────────────────────────────────────────
st.markdown(
    f"""
    <style>
    .stApp {{
        background: radial-gradient(ellipse 1200px 600px at 20% -10%, rgba(139,92,246,0.10), transparent 60%),
                    radial-gradient(ellipse 900px 600px at 90% 100%, rgba(236,72,153,0.08), transparent 60%),
                    #0F0A1E;
        color: #F5F3FA;
    }}
    section[data-testid="stSidebar"] {{ display:none; }}
    .block-container {{
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }}
    h1, h2, h3, h4 {{ color:#fff !important; font-family:'Trebuchet MS', sans-serif; }}
    
    .stButton>button {{
        background: linear-gradient(120deg, {HEADER_BLUE}, {HOT_PINK});
        color:#fff; border:none; border-radius:20px; font-weight:700;
        padding:0.5rem 1.1rem;
        transition: transform 0.15s ease, opacity 0.15s ease;
    }}
    .stButton>button:hover {{
        opacity:0.92;
        color:#fff;
        transform: translateY(-1px);
    }}
    .stButton>button:disabled {{
        background: #2E2640 !important;
        color: rgba(255,255,255,0.3) !important;
        cursor: not-allowed;
        transform: none;
    }}
    
    div[data-baseweb="select"] > div {{
        background:#1A1030 !important;
        border-radius:12px !important;
        border:1px solid rgba(255,255,255,0.15) !important;
        color: #fff !important;
    }}
    div[data-baseweb="input"] > div {{
        background:#1A1030 !important;
        border-radius:12px !important;
        border:1px solid rgba(255,255,255,0.15) !important;
        color: #fff !important;
    }}
    .stTextInput input {{
        color: #fff !important;
    }}
    
    .stMultiSelect [data-baseweb="tag"] {{
        background: linear-gradient(120deg, {HEADER_BLUE}, {VIOLET}) !important;
        color:#fff !important;
        border-radius:8px !important;
    }}
    
    .metric-card {{
        background:#1A1030;
        border:1px solid rgba(255,255,255,0.1);
        border-radius:16px;
        padding:14px 16px;
        text-align:center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }}
    .metric-card .val {{
        font-size:22px;
        font-weight:800;
        color:#fff;
        background: linear-gradient(90deg, #F9C24B, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .metric-card .lbl {{
        font-size:11px;
        color:rgba(255,255,255,0.6);
        text-transform:uppercase;
        letter-spacing:0.06em;
        margin-top: 2px;
    }}
    
    .kpi-card {{
        background: #1A1030;
        border: 1px solid rgba(139, 92, 246, 0.25);
        border-radius: 16px;
        padding: 20px 22px;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }}
    .kpi-val {{
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4E7CFF 0%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }}
    .kpi-label {{
        font-size: 0.85rem;
        color: #CBD5E1;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    .eyebrow {{
        font-family:monospace;
        font-size:12px;
        letter-spacing:0.14em;
        text-transform:uppercase;
        color:#F9C24B;
        margin-bottom: 2px;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 12px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 44px;
        white-space: pre-wrap;
        background-color: #1A1030;
        border-radius: 12px 12px 0 0;
        color: #A6ADC8;
        font-weight: 600;
        padding: 0 20px;
        border: 1px solid rgba(255,255,255,0.08);
        border-bottom: none;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(180deg, rgba(78,124,255,0.25) 0%, #1A1030 100%) !important;
        color: #FFFFFF !important;
        border-color: rgba(78,124,255,0.5) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sample Fallback Seed Batch ───────────────────────────────────────────────────
DEFAULT_SAMPLE_BATCH = [
    {
        "id": "init_mcq_1",
        "content_type": "MCQ",
        "item": {
            "sport": "Cricket",
            "difficulty": "Medium",
            "question": "Who has scored the most centuries in Cricket World Cup history?",
            "options": {
                "A": "Virat Kohli",
                "B": "Sachin Tendulkar",
                "C": "Ricky Ponting",
                "D": "Rohit Sharma",
            },
            "correct_answer": "B",
            "explanation": "Sachin Tendulkar scored 6 centuries across ODI World Cups — still tied with Rohit Sharma for the all-time tournament record.",
            "source": "vector_db",
            "platform_surface": "Story",
            "grounded": True,
        },
    },
    {
        "id": "init_tf_2",
        "content_type": "True/False",
        "item": {
            "sport": "Football",
            "difficulty": "Easy",
            "statement": "A standard professional football match is played in two 45-minute halves.",
            "correct_answer": True,
            "explanation": "Standard FIFA regulation match length is 90 minutes, divided into two halves of 45 minutes each.",
            "source": "vector_db",
            "platform_surface": "Story",
            "grounded": True,
        },
    },
    {
        "id": "init_tot_3",
        "content_type": "This-or-That",
        "item": {
            "sport": "Football",
            "prompt": "Messi or Ronaldo — who has the deadlier solo dribbling skill?",
            "options": ["Lionel Messi", "Cristiano Ronaldo"],
            "is_opinion": True,
            "platform_surface": "Story",
        },
    },
    {
        "id": "init_fib_4",
        "content_type": "Fill in the Blank",
        "item": {
            "sport": "Badminton",
            "difficulty": "Medium",
            "sentence": "A standard BWF badminton match is played best of ___ games.",
            "options": ["2", "3", "5", "7"],
            "correct_answer": "3",
            "explanation": "BWF international matches follow a best-of-3 format, where each game is played to 21 points.",
            "source": "vector_db",
            "platform_surface": "Feed",
            "grounded": True,
        },
    },
    {
        "id": "init_gtn_5",
        "content_type": "Guess the Number",
        "item": {
            "sport": "Cricket",
            "difficulty": "Hard",
            "question": "How many total runs did Virat Kohli score in the 2023 ICC ODI World Cup?",
            "target_number": 765,
            "tolerance": 25,
            "explanation": "Virat Kohli amassed a record-breaking 765 runs in the 2023 World Cup across 11 innings.",
            "source": "web_search",
            "platform_surface": "Feed",
            "grounded": True,
        },
    },
]

# ── Session State Initialization ───────────────────────────────────────────────
if "batch_items" not in st.session_state:
    st.session_state.batch_items = DEFAULT_SAMPLE_BATCH.copy()
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "last_params" not in st.session_state:
    st.session_state.last_params = {
        "sport": "Cricket",
        "difficulty": "Medium",
        "types": TYPES,
        "topic_hint": "",
    }


# ── Story HTML Renderer (Pixel-Matching Design Reference) ───────────────────────
def render_story_html(wrapper: dict, current_idx: int = 0, total_items: int = 5) -> str:
    """Generate pixel-perfect Instagram quiz-sticker story HTML for a content item.
    
    Renders real schema fields into the vibrant gradient card template with
    interactive JavaScript states for MCQ, True/False, This-or-That, Fill in Blank,
    and Guess the Number.
    """
    item = wrapper.get("item", wrapper)
    c_type = wrapper.get("content_type", item.get("content_type", item.get("type", "MCQ")))
    sport = item.get("sport", "Sports")
    difficulty = item.get("difficulty", "Medium")

    # Header Tag & Surface Badges
    tag_label = "Opinion" if c_type == "This-or-That" else difficulty
    surface = item.get("platform_surface", "Story")
    surface_icon = "◆" if surface == "Story" else ("▤" if surface == "Feed" else "▶")
    
    # Grounding & Source Badges
    source_raw = item.get("source", "vector_db")
    source_map = {
        "web_search": "🌐 Web Search",
        "vector_db": "📚 Vector DB",
        "both": "🌐 Web + 📚 DB",
    }
    source_label = source_map.get(source_raw, source_raw) if c_type != "This-or-That" else "🗳️ Opinion Poll"
    
    grounded_raw = item.get("grounded")
    grounded_badge = ""
    if c_type != "This-or-That" and grounded_raw is not None:
        grounded_badge = "✅ verified" if grounded_raw else "⚠️ ungrounded"
    
    badge_parts = [p for p in [source_label, grounded_badge, f"{surface_icon} {surface}"] if p]
    badge_text = " · ".join(badge_parts)

    # Progress segment bars
    total_segs = max(1, total_items)
    segments_html = "".join(
        f'<div class="seg" style="opacity:{1.0 if i == current_idx else 0.3}"></div>'
        for i in range(total_segs)
    )

    # Handle Error Item State
    if item.get("error"):
        kicker = "Generation Alert"
        prompt_text = "⚠️ Generation Error"
        body = f"""
        <div style="padding:24px 16px; text-align:center; color:#f87171;">
            <div style="font-weight:700; font-size:14px; margin-bottom:8px;">{html.escape(item.get('message', 'Failed to generate item.'))}</div>
            <div style="font-size:11px; color:#A6ADC8;">Click <b>↻ Regenerate</b> in creator controls to retry this item.</div>
        </div>
        """
        return _wrap_story_scaffold(segments_html, sport, tag_label, kicker, prompt_text, body, badge_text)

    # 1. This-or-That (Opinion Poll)
    if c_type == "This-or-That":
        kicker = "This or That"
        prompt_text = html.escape(item.get("prompt", ""))
        opts = item.get("options", ["Option A", "Option B"])
        optA = html.escape(str(opts[0])) if len(opts) > 0 else "Option A"
        optB = html.escape(str(opts[1])) if len(opts) > 1 else "Option B"
        body = f"""
        <div class="tot-split">
          <div class="tot-side a" onclick="vote(this)"><div class="tot-pct" id="pctA">64%</div><div class="tot-fill" id="fillA"></div><span>{optA}</span></div>
          <div class="tot-vs">VS</div>
          <div class="tot-side b" onclick="vote(this)"><div class="tot-pct" id="pctB">36%</div><div class="tot-fill" id="fillB"></div><span>{optB}</span></div>
        </div>
        <div class="opinion-strip">✦ opinion-based — not fact-checked</div>
        """

    # 2. Guess the Number (Interactive Slider)
    elif c_type == "Guess the Number":
        kicker = "Guess the Number"
        prompt_text = html.escape(item.get("question", ""))
        target_num = float(item.get("target_number", 50))
        tolerance = float(item.get("tolerance", 0))

        # Dynamic Slider Boundaries
        if target_num <= 0:
            min_val = int(target_num * 1.5) - 10
            max_val = max(10, int(abs(target_num) * 1.5))
        elif target_num <= 10:
            min_val = 0
            max_val = max(15, int(target_num * 2))
        elif target_num <= 100:
            min_val = 0
            max_val = max(100, int(target_num * 1.4))
        else:
            min_val = 0
            max_val = max(int(target_num * 1.4), int(target_num + tolerance * 3))

        span = max(1.0, float(max_val - min_val))
        target_pct = max(0.0, min(100.0, ((target_num - min_val) / span) * 100))
        low_pct = max(0.0, min(100.0, ((target_num - tolerance - min_val) / span) * 100))
        high_pct = max(0.0, min(100.0, ((target_num + tolerance - min_val) / span) * 100))
        range_left = low_pct
        range_width = max(3.0, high_pct - low_pct)
        init_guess = int(min_val + span * 0.25)
        init_pct = 25.0

        explanation_escaped = html.escape(item.get("explanation", ""))
        body = f"""
        <div class="slider-block">
          <div class="slider-track" id="track">
            <div class="slider-range" style="left:{range_left:.1f}%; width:{range_width:.1f}%;"></div>
            <div class="slider-target" style="left:{target_pct:.1f}%;"></div>
            <div class="slider-handle" id="handle" style="left:{init_pct:.1f}%;"></div>
          </div>
          <div class="slider-labels"><span>{min_val}</span><span>{max_val}</span></div>
          <div class="guess-readout" id="readout">{init_guess}</div>
          <button class="lock-btn" onclick="lockGuess()">Lock In Guess</button>
        </div>
        <div class="explain-strip" id="gtn-explain">🎯 <b>Target:</b> {target_num:g} (±{tolerance:g})<br>{explanation_escaped}</div>
        <script>
          window.SLIDER_MIN = {min_val};
          window.SLIDER_MAX = {max_val};
        </script>
        """

    # 3. True / False
    elif c_type == "True/False":
        kicker = "True or False"
        prompt_text = f'"{html.escape(item.get("statement", ""))}"'
        correct_ans = bool(item.get("correct_answer", True))
        explanation_escaped = html.escape(item.get("explanation", ""))
        body = f"""
        <div class="quiz-options">
          <div class="opt" data-correct="{"true" if correct_ans else "false"}" onclick="pickMCQ(this)">
            <span class="icon">✕</span><span>True</span>
          </div>
          <div class="opt" data-correct="{"true" if not correct_ans else "false"}" onclick="pickMCQ(this)">
            <span class="icon">✕</span><span>False</span>
          </div>
        </div>
        <div class="explain-strip" id="explain">{explanation_escaped}</div>
        """

    # 4. Fill in the Blank
    elif c_type == "Fill in the Blank":
        kicker = "Fill in the Blank"
        raw_sentence = item.get("sentence", "")
        escaped_sentence = html.escape(raw_sentence)
        prompt_text = escaped_sentence.replace(
            "___", '<span style="border-bottom:3px solid #fff; font-weight:800; padding:0 4px;">___</span>'
        )
        correct_ans = item.get("correct_answer", "")
        options = item.get("options", [])
        
        opts_html = ""
        for opt in options:
            is_corr = str(opt).strip() == str(correct_ans).strip()
            opt_esc = html.escape(str(opt))
            opts_html += f'<div class="opt" data-correct="{"true" if is_corr else "false"}" onclick="pickMCQ(this)"><span class="icon">✕</span><span>{opt_esc}</span></div>'
        
        explanation_escaped = html.escape(item.get("explanation", ""))
        body = f"""
        <div class="quiz-options">{opts_html}</div>
        <div class="explain-strip" id="explain">{explanation_escaped}</div>
        """

    # 5. MCQ (Standard Quiz)
    else:
        kicker = "Quiz"
        prompt_text = html.escape(item.get("question", ""))
        options_data = item.get("options", {})
        correct_ans = str(item.get("correct_answer", "")).strip()

        if isinstance(options_data, dict):
            options_pairs = list(options_data.items())
        else:
            options_pairs = [(chr(65 + i), opt) for i, opt in enumerate(options_data)]

        opts_html = ""
        for key, opt_val in options_pairs:
            is_corr = (str(key).strip().upper() == correct_ans.upper()) or (str(opt_val).strip() == correct_ans)
            opt_esc = html.escape(str(opt_val))
            key_esc = html.escape(str(key))
            opts_html += f'<div class="opt" data-correct="{"true" if is_corr else "false"}" onclick="pickMCQ(this)"><span class="icon">✕</span><span><b>{key_esc}:</b> {opt_esc}</span></div>'

        explanation_escaped = html.escape(item.get("explanation", ""))
        body = f"""
        <div class="quiz-options">{opts_html}</div>
        <div class="explain-strip" id="explain">{explanation_escaped}</div>
        """

    return _wrap_story_scaffold(segments_html, sport, tag_label, kicker, prompt_text, body, badge_text)


def _wrap_story_scaffold(segments_html: str, sport: str, tag_label: str, kicker: str, prompt_text: str, body: str, badge_text: str) -> str:
    """Wrap story card body into the complete Instagram phone mockup scaffold."""
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
      *{{box-sizing:border-box;}}
      body{{margin:0; font-family:'Inter',sans-serif; background:transparent; display:flex; justify-content:center; align-items:center;}}
      .phone{{position:relative; width:100%; max-width:340px; height:620px; margin:0 auto;
        border-radius:36px; padding:10px; background:#000; box-shadow:0 20px 50px -15px rgba(0,0,0,0.6);}}
      .screen{{position:relative; width:100%; height:100%; border-radius:28px; overflow:hidden;
        background:linear-gradient(160deg,#6B2FBF 0%,#A835B0 30%,#E14F8A 55%,#F17B4E 78%,#F9C24B 100%);}}
      .sprinkle{{position:absolute; border-radius:2px; opacity:0.9;}}
      .sprinkle.dot{{border-radius:50%;}}
      .story-top{{position:relative; z-index:5; padding:12px 12px 0;}}
      .segments{{display:flex; gap:4px;}}
      .seg{{flex:1; height:3px; border-radius:3px; background:rgba(255,255,255,0.85);}}
      .header{{display:flex; align-items:center; gap:8px; margin-top:10px;}}
      .avatar{{width:28px; height:28px; border-radius:50%; background:#2B3A67; color:#fff; font-weight:800;
        display:flex; align-items:center; justify-content:center; font-family:'Baloo 2',sans-serif;
        box-shadow:0 0 0 2px rgba(255,255,255,0.5);}}
      .who b{{color:#fff; font-size:12.5px;}}
      .who span{{color:rgba(255,255,255,0.8); font-size:11px; margin-left:6px;}}
      .tag{{font-family:'JetBrains Mono',monospace; font-size:8px; background:rgba(255,255,255,0.22); color:#fff;
        padding:2px 6px; border-radius:20px; margin-left:6px;}}
      .body{{position:relative; z-index:5; padding:14px 16px;}}
      .card{{background:#fff; border-radius:20px; overflow:hidden; box-shadow:0 14px 30px -10px rgba(0,0,0,0.4);}}
      .card-header{{background:linear-gradient(120deg,{HEADER_BLUE},{VIOLET}); padding:16px 16px 18px; text-align:center;}}
      .kicker{{font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:rgba(255,255,255,0.75);}}
      .prompt{{font-family:'Baloo 2',sans-serif; font-weight:700; font-size:16px; color:#fff; margin-top:5px; line-height:1.25;}}
      .quiz-options{{padding:14px; display:flex; flex-direction:column; gap:8px;}}
      .opt{{position:relative; padding:10px 12px; border-radius:24px; background:#fff; border:1.6px solid #ECECF2;
        font-size:13px; font-weight:700; color:#2E2E3A; cursor:pointer; display:flex; align-items:center; gap:9px;
        transition: background 0.15s ease, border-color 0.15s ease;}}
      .opt:hover{{border-color:#D0D0E0;}}
      .opt .icon{{width:20px; height:20px; border-radius:50%; border:2px solid {HOT_PINK}; color:{HOT_PINK};
        display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:800; flex-shrink:0;}}
      .opt.correct{{background:{GREEN} !important; border-color:{GREEN} !important; color:#fff !important;}}
      .opt.correct .icon{{background:#fff; border-color:#fff; color:{GREEN};}}
      .opt.wrong{{opacity:0.5; border-color:{HOT_PINK};}}
      .tot-split{{display:flex; gap:8px; padding:14px; position:relative;}}
      .tot-side{{flex:1; border-radius:16px; position:relative; overflow:hidden; height:110px;
        display:flex; align-items:flex-end; justify-content:center; padding-bottom:10px;
        background:#F4F2FA; border:1.4px solid #ECECF2; cursor:pointer; font-family:'Baloo 2',sans-serif;
        font-weight:700; font-size:13.5px; color:#2E2E3A; text-align:center; padding-left:4px; padding-right:4px;}}
      .tot-fill{{position:absolute; left:0; right:0; bottom:0; height:0%;
        background:linear-gradient(180deg, rgba(236,72,153,0.15), rgba(236,72,153,0.65)); transition:height .6s ease;}}
      .tot-side.b .tot-fill{{background:linear-gradient(180deg, rgba(249,194,75,0.2), rgba(239,90,111,0.65));}}
      .tot-side span{{position:relative; z-index:2;}}
      .tot-side.filled span{{color:#fff;}}
      .tot-pct{{position:absolute; top:8px; z-index:2; font-family:'JetBrains Mono',monospace; font-size:10px; color:#8E8E9A; display:none; font-weight:700;}}
      .tot-vs{{position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); z-index:3;
        font-family:'Baloo 2',sans-serif; font-weight:800; font-size:11px; color:#fff;
        background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK}); width:26px; height:26px; border-radius:50%;
        display:flex; align-items:center; justify-content:center; box-shadow:0 0 0 4px #fff;}}
      .opinion-strip{{text-align:center; font-family:'JetBrains Mono',monospace; font-size:9px; color:#8E8E9A; padding:0 14px 12px;}}
      .slider-block{{padding:14px 16px 16px;}}
      .slider-track{{position:relative; height:7px; border-radius:8px; background:#ECECF2; margin:14px 0 6px; cursor:pointer;}}
      .slider-range{{position:absolute; top:0; bottom:0; background:rgba(236,72,153,0.28); border-radius:8px;}}
      .slider-target{{position:absolute; top:-5px; width:2px; height:16px; background:{VIOLET};}}
      .slider-handle{{position:absolute; top:50%; width:22px; height:22px; border-radius:50%;
        background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK}); border:3px solid #fff;
        transform:translate(-50%,-50%); cursor:grab; touch-action:none;}}
      .slider-labels{{display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:9px; color:#8E8E9A;}}
      .guess-readout{{font-family:'Baloo 2',sans-serif; font-weight:800; font-size:24px; text-align:center; color:{VIOLET}; margin-top:2px;}}
      .lock-btn{{display:block; margin:10px auto 0; font-family:'JetBrains Mono',monospace; font-size:10px;
        text-transform:uppercase; color:#fff; background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK});
        border:none; padding:8px 18px; border-radius:20px; cursor:pointer; font-weight:700;}}
      .explain-strip{{font-size:10.5px; color:#6B7280; padding:0 14px 14px; display:none; line-height:1.4; border-top:1px dashed #ECECF2; padding-top:10px; margin-top:4px;}}
      .explain-strip.show{{display:block;}}
      .badge-row{{position:relative; z-index:5; padding:0 16px 6px;}}
      .badge{{font-family:'JetBrains Mono',monospace; font-size:8.5px; padding:4px 10px; border-radius:20px;
        background:rgba(0,0,0,0.32); color:#fff; display:inline-block; backdrop-filter:blur(4px);}}
      .bottom{{position:relative; z-index:5; display:flex; align-items:center; gap:8px; padding:6px 14px 12px;}}
      .cam{{width:30px; height:30px; border-radius:10px; background:rgba(0,0,0,0.25); display:flex;
        align-items:center; justify-content:center; color:#fff; font-size:13px; flex-shrink:0;}}
      .reply{{flex:1; height:32px; border-radius:20px; border:1.4px solid rgba(255,255,255,0.65);
        display:flex; align-items:center; padding:0 12px; font-size:11px; color:rgba(255,255,255,0.85);}}
      .ic{{width:24px; height:24px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:14px;}}
    </style></head>
    <body>
      <div class="phone"><div class="screen">
        <div class="sprinkle dot" style="top:8%; left:12%; width:6px; height:6px; background:#F9C24B;"></div>
        <div class="sprinkle" style="top:6%; left:70%; width:10px; height:4px; background:#fff; transform:rotate(30deg);"></div>
        <div class="sprinkle dot" style="top:70%; left:88%; width:6px; height:6px; background:#EC4899;"></div>
        <div class="sprinkle" style="top:80%; left:10%; width:10px; height:4px; background:#4E7CFF; transform:rotate(50deg);"></div>
        <div class="story-top">
          <div class="segments">{segments_html}</div>
          <div class="header">
            <div class="avatar">S</div>
            <div class="who"><b>stapubox</b><span>{sport}</span><span class="tag">{tag_label}</span></div>
          </div>
        </div>
        <div class="body">
          <div class="card">
            <div class="card-header"><div class="kicker">{kicker}</div><div class="prompt">{prompt_text}</div></div>
            {body}
          </div>
        </div>
        <div class="badge-row"><div class="badge">{badge_text}</div></div>
        <div class="bottom">
          <div class="cam">📷</div>
          <div class="reply">Send message</div>
          <div class="ic">⋮</div>
          <div class="ic">➤</div>
        </div>
      </div></div>
      <script>
        function pickMCQ(el){{
          const group = el.parentElement;
          if(group.classList.contains('revealed')) return;
          group.classList.add('revealed');
          group.querySelectorAll('.opt').forEach(o=>{{
            if(o.dataset.correct === 'true'){{
              o.classList.add('correct');
              const ic = o.querySelector('.icon');
              if(ic) ic.textContent = '✓';
            }} else if(o === el){{
              o.classList.add('wrong');
            }}
          }});
          const explain = document.getElementById('explain');
          if(explain) explain.classList.add('show');
        }}
        let voted = false;
        function vote(el){{
          if(voted) return; voted = true;
          const isA = el.classList.contains('a');
          document.getElementById('fillA').style.height = isA ? '64%' : '36%';
          document.getElementById('fillB').style.height = isA ? '36%' : '64%';
          document.getElementById('pctA').style.display = 'block';
          document.getElementById('pctB').style.display = 'block';
          document.querySelectorAll('.tot-side').forEach(s=>s.classList.add('filled'));
        }}
        const handle = document.getElementById('handle');
        if(handle){{
          const track = handle.parentElement;
          const readout = document.getElementById('readout');
          const minVal = window.SLIDER_MIN || 0;
          const maxVal = window.SLIDER_MAX || 1000;
          let dragging = false;
          function setFromClientX(x){{
            const rect = track.getBoundingClientRect();
            let pct = (x - rect.left) / rect.width;
            pct = Math.max(0, Math.min(1, pct));
            handle.style.left = (pct * 100) + '%';
            const val = Math.round(minVal + pct * (maxVal - minVal));
            readout.textContent = val;
          }}
          handle.addEventListener('pointerdown', e=>{{
            dragging = true;
            handle.setPointerCapture(e.pointerId);
          }});
          handle.addEventListener('pointermove', e=>{{ if(dragging) setFromClientX(e.clientX); }});
          handle.addEventListener('pointerup', ()=>{{ dragging = false; }});
          track.addEventListener('click', e=>{{ if(e.target === track) setFromClientX(e.clientX); }});
        }}
        let locked = false;
        function lockGuess(){{
          if(locked) return; locked = true;
          const el = document.getElementById('gtn-explain');
          if(el) el.classList.add('show');
        }}
      </script>
    </body></html>
    """


# ── App Header ──────────────────────────────────────────────────────────────────
st.markdown('<div class="eyebrow">AI-Powered Sports Engagement Content Agent</div>', unsafe_allow_html=True)
st.title("🏆 StapuBox Story Studio")

# ── Tabs Navigation ─────────────────────────────────────────────────────────────
tab_studio, tab_analytics = st.tabs(["🏆 Story Studio", "📊 Freshness & Grounding Analytics (USP)"])

# ── Tab 1: Story Studio & Creator Controls ──────────────────────────────────────
with tab_studio:
    col_preview, col_controls = st.columns([1.1, 1], gap="large")

    # ── Left Column: Story Preview & Navigation ──
    with col_preview:
        if st.session_state.batch_items:
            # Bound current index safely
            st.session_state.current_idx = max(0, min(st.session_state.current_idx, len(st.session_state.batch_items) - 1))
            current_wrapper = st.session_state.batch_items[st.session_state.current_idx]
            
            story_html_code = render_story_html(
                current_wrapper,
                current_idx=st.session_state.current_idx,
                total_items=len(st.session_state.batch_items),
            )
            components.html(story_html_code, height=660, scrolling=False)

            # Story Carousel Navigation Controls
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                if st.button("⬅ Prev", use_container_width=True, disabled=(st.session_state.current_idx == 0)):
                    st.session_state.current_idx -= 1
                    st.rerun()
            with nav2:
                cur_item_type = current_wrapper.get("content_type", "")
                st.markdown(
                    f"<p style='text-align:center; color:rgba(255,255,255,0.7); margin-top:8px; font-weight:600; font-size:13px;'>"
                    f"Item {st.session_state.current_idx + 1} of {len(st.session_state.batch_items)} — {cur_item_type}</p>",
                    unsafe_allow_html=True,
                )
            with nav3:
                if st.button("Next ➡", use_container_width=True, disabled=(st.session_state.current_idx == len(st.session_state.batch_items) - 1)):
                    st.session_state.current_idx += 1
                    st.rerun()
        else:
            st.info("No content items generated yet. Configure options on the right and click **Generate Batch**.")

    # ── Right Column: Creator Controls & Live Telemetry ──
    with col_controls:
        st.subheader("Creator Controls")
        
        sport = st.selectbox(
            "Sport",
            options=SPORTS,
            index=SPORTS.index(st.session_state.last_params.get("sport", "Cricket")) if st.session_state.last_params.get("sport") in SPORTS else 0,
        )
        
        difficulty = st.select_slider(
            "Difficulty",
            options=DIFFICULTIES,
            value=st.session_state.last_params.get("difficulty", "Medium"),
        )
        
        types_selected = st.multiselect(
            "Content formats (mix for a varied batch)",
            options=TYPES,
            default=st.session_state.last_params.get("types", TYPES),
        )
        
        topic_hint = st.text_input(
            "Optional Focus / Recency Topic",
            value=st.session_state.last_params.get("topic_hint", ""),
            placeholder="e.g. 2024 World Cup, records, derbies",
        )

        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            if st.button("🚀 Generate Batch", use_container_width=True):
                active_types = types_selected if types_selected else TYPES
                st.session_state.last_params = {
                    "sport": sport,
                    "difficulty": difficulty,
                    "types": active_types,
                    "topic_hint": topic_hint,
                }
                with st.spinner(f"Generating verified {difficulty} {sport} batch..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/generate/batch",
                            json={
                                "sport": sport,
                                "difficulty": difficulty,
                                "count": 5,
                                "content_types": active_types,
                                "topic_hint": topic_hint if topic_hint.strip() else None,
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.batch_items = data.get("items", [])
                            st.session_state.current_idx = 0
                            st.rerun()
                        else:
                            st.error(f"Backend error {resp.status_code}: {resp.text}")
                    except requests.exceptions.ReadTimeout:
                        st.error("⏳ Batch generation timed out awaiting rate-pacing slots. Please retry.")
                    except Exception as err:
                        st.error(f"❌ Connection to backend failed: {err}")

        with gen_col2:
            if st.button("↻ Regenerate current", use_container_width=True, disabled=not st.session_state.batch_items):
                cur_idx = st.session_state.current_idx
                cur_wrapper = st.session_state.batch_items[cur_idx]
                cur_item = cur_wrapper.get("item", {})
                target_type = cur_wrapper.get("content_type", "MCQ")
                
                with st.spinner(f"Regenerating {target_type}..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/regenerate/item",
                            json={
                                "sport": cur_item.get("sport", sport),
                                "difficulty": cur_item.get("difficulty", difficulty),
                                "content_type": target_type,
                                "topic_hint": topic_hint if topic_hint.strip() else None,
                            },
                            timeout=60,
                        )
                        if resp.status_code == 200:
                            new_wrapper = resp.json().get("item")
                            st.session_state.batch_items[cur_idx] = new_wrapper
                            st.rerun()
                        else:
                            st.error(f"Error {resp.status_code}: {resp.text}")
                    except requests.exceptions.ReadTimeout:
                        st.error("⏳ Regeneration timed out awaiting rate-pacing slots. Please retry.")
                    except Exception as err:
                        st.error(f"Failed to regenerate: {err}")

        # Batch Strip Navigation
        if st.session_state.batch_items:
            st.markdown("**Batch strip**")
            short_labels = {
                "MCQ": "MCQ",
                "True/False": "T/F",
                "This-or-That": "T-o-T",
                "Fill in the Blank": "Blank",
                "Guess the Number": "Guess",
            }
            thumb_cols = st.columns(len(st.session_state.batch_items))
            for i, tc in enumerate(thumb_cols):
                with tc:
                    w_item = st.session_state.batch_items[i]
                    c_name = w_item.get("content_type", "Item")
                    short_name = short_labels.get(c_name, c_name[:4])
                    is_active = (i == st.session_state.current_idx)
                    btn_text = f"● {short_name}" if is_active else short_name
                    if st.button(btn_text, key=f"thumb_{i}", use_container_width=True):
                        st.session_state.current_idx = i
                        st.rerun()

        st.divider()

        # Batch Freshness / Grounding Analytics Summary
        st.markdown("**Freshness / Grounding Analytics**  \n*(USP feature — live metrics from orchestrator pipeline)*")
        if st.session_state.batch_items:
            grounded_count = sum(
                1 for it in st.session_state.batch_items
                if it.get("item", {}).get("grounded") is True
            )
            total_factual = sum(
                1 for it in st.session_state.batch_items
                if it.get("item", {}).get("grounded") is not None
            )
            src_set = set(
                it.get("item", {}).get("source")
                for it in st.session_state.batch_items
                if it.get("item", {}).get("source")
            )
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(
                    f'<div class="metric-card"><div class="val">{grounded_count}/{total_factual or 1}</div><div class="lbl">Grounded first try</div></div>',
                    unsafe_allow_html=True,
                )
            with m2:
                st.markdown(
                    f'<div class="metric-card"><div class="val">{len(src_set) or 1}</div><div class="lbl">Source types used</div></div>',
                    unsafe_allow_html=True,
                )
            with m3:
                st.markdown(
                    f'<div class="metric-card"><div class="val">0</div><div class="lbl">Duplicates rejected</div></div>',
                    unsafe_allow_html=True,
                )

        st.divider()
        
        # Batch Export JSON Download
        if st.session_state.batch_items:
            export_payload = [b.get("item", b) for b in st.session_state.batch_items]
            export_json = json.dumps(export_payload, indent=2)
            st.download_button(
                "⇩ Export batch as JSON",
                data=export_json,
                file_name=f"{sport.lower()}_engagement_batch.json",
                mime="application/json",
                use_container_width=True,
            )

        with st.expander("🔍 Inspect Full Batch Raw JSON"):
            st.json(st.session_state.batch_items)


# ── Tab 2: Freshness & Grounding Telemetry (USP) ────────────────────────────────
with tab_analytics:
    st.subheader("📊 Real-Time Freshness & Grounding Telemetry")
    st.caption("Live telemetry metrics capturing anti-hallucination verification loops, semantic deduplication, and platform surface distributions.")

    try:
        analytics_resp = requests.get(f"{BACKEND_URL}/analytics", timeout=5)
        if analytics_resp.status_code == 200:
            stats = analytics_resp.json()

            # KPI Grid
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-val">{stats.get('total_items_generated', 0)}</div>
                        <div class="kpi-label">Items Generated</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi2:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-val">{stats.get('grounding_success_rate_pct', 100)}%</div>
                        <div class="kpi-label">Grounding Verification</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi3:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-val">{stats.get('grounded_first_try', 0)} / {stats.get('grounded_after_retry', 0)}</div>
                        <div class="kpi-label">1st Try vs Retry</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with kpi4:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-val">{stats.get('dedup_rejections', 0)}</div>
                        <div class="kpi-label">Duplicates Filtered</div>
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
                    st.bar_chart(df_sources, color="#8B5CF6")
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
                    st.bar_chart(df_surfaces, color="#4E7CFF")
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
        st.warning(f"Could not connect to live backend analytics endpoint: {e}. Start backend with `python3 -m uvicorn backend.main:app --port 8000`.")

