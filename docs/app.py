"""
StapuBox — AI-Powered Sports Engagement Content Agent
Streamlit dashboard prototype (UI-only, mock data)

This is a design/UX prototype: the batch/regenerate/export flows work against
mock in-memory data so the look and interaction pattern can be validated before
wiring the real FastAPI + Gemini + Tavily + ChromaDB backend (see docs/04_PHASES.md).

Run with:
    pip install streamlit
    streamlit run app.py
"""

import json
import random
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# PAGE CONFIG + GLOBAL THEME (matches the IG quiz-sticker mockup palette)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="StapuBox — Sports Content Agent",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HEADER_BLUE = "#4E7CFF"
HOT_PINK = "#EC4899"
VIOLET = "#8B5CF6"
GREEN = "#4CAF50"

st.markdown(f"""
<style>
    .stApp {{
        background: radial-gradient(ellipse 1200px 600px at 20% -10%, rgba(139,92,246,0.10), transparent 60%),
                    radial-gradient(ellipse 900px 600px at 90% 100%, rgba(236,72,153,0.08), transparent 60%),
                    #0F0A1E;
        color: #F5F3FA;
    }}
    section[data-testid="stSidebar"] {{ display:none; }}
    h1, h2, h3 {{ color:#fff !important; font-family:'Trebuchet MS', sans-serif; }}
    .stButton>button {{
        background: linear-gradient(120deg, {HEADER_BLUE}, {HOT_PINK});
        color:#fff; border:none; border-radius:20px; font-weight:700;
        padding:0.5rem 1.1rem;
    }}
    .stButton>button:hover {{ opacity:0.9; color:#fff; }}
    div[data-baseweb="select"] > div {{
        background:#1A1030; border-radius:12px; border:1px solid rgba(255,255,255,0.15);
    }}
    .stMultiSelect [data-baseweb="tag"] {{
        background: linear-gradient(120deg, {HEADER_BLUE}, {VIOLET}); color:#fff;
    }}
    .metric-card {{
        background:#1A1030; border:1px solid rgba(255,255,255,0.1);
        border-radius:16px; padding:14px 16px; text-align:center;
    }}
    .metric-card .val {{ font-size:22px; font-weight:800; color:#fff; }}
    .metric-card .lbl {{ font-size:11px; color:rgba(255,255,255,0.55); text-transform:uppercase; letter-spacing:0.06em; }}
    .batch-thumb button {{
        width:100%; border-radius:12px !important;
    }}
    .eyebrow {{
        font-family:monospace; font-size:12px; letter-spacing:0.14em; text-transform:uppercase;
        color:#F9C24B;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# MOCK DATA — stands in for the real orchestrator/backend (Phases 0-6)
# ---------------------------------------------------------------------------
SPORTS = ["Cricket", "Football", "Tennis", "Badminton", "Basketball"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
TYPES = ["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"]

MOCK_POOL = {
    "MCQ": [
        dict(kicker="Quiz", prompt="Who has the most centuries in Cricket World Cup history?",
             options=["Virat Kohli", "Sachin Tendulkar", "Ricky Ponting", "Rohit Sharma"],
             correct=1, explain="Sachin Tendulkar scored 6 centuries across World Cups — still the record.",
             source="Web + Vector DB", grounded=True, surface="Story"),
        dict(kicker="Quiz", prompt="Which country has won the most FIFA World Cups?",
             options=["Germany", "Argentina", "Brazil", "Italy"],
             correct=2, explain="Brazil has won 5 FIFA World Cup titles, the most of any nation.",
             source="Vector DB", grounded=True, surface="Story"),
    ],
    "True/False": [
        dict(kicker="True or False", prompt="A football match has two 45-minute halves.",
             options=["True", "False"], correct=0,
             explain="Standard match length is 90 minutes, split into two 45-minute halves.",
             source="Vector DB", grounded=True, surface="Story"),
    ],
    "This-or-That": [
        dict(kicker="This or That", prompt="Messi or Ronaldo — who's the greater dribbler?",
             options=["Messi", "Ronaldo"], correct=None,
             explain=None, source="Opinion (no source)", grounded=None, surface="Story"),
    ],
    "Fill in the Blank": [
        dict(kicker="Fill in the Blank", prompt="A badminton match is played best of ___ games.",
             options=["2", "3", "5", "7"], correct=1,
             explain="BWF matches are best-of-3 games, each to 21 points.",
             source="Vector DB", grounded=True, surface="Feed"),
    ],
    "Guess the Number": [
        dict(kicker="Guess the Number", prompt="How many runs did Virat Kohli score in the 2023 World Cup?",
             target=765, tolerance=25,
             explain="Kohli scored 765 runs — tolerance band ±25.",
             source="Web Search", grounded=True, surface="Feed"),
    ],
}

def make_mock_item(content_type, sport, difficulty):
    base = random.choice(MOCK_POOL[content_type]).copy()
    base["type"] = content_type
    base["sport"] = sport
    base["difficulty"] = difficulty
    return base

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "batch" not in st.session_state:
    st.session_state.batch = [
        make_mock_item(t, "Cricket", "Medium") for t in TYPES
    ]
if "current" not in st.session_state:
    st.session_state.current = 0

# ---------------------------------------------------------------------------
# HTML RENDERER — same visual language as the IG quiz-sticker mockup,
# generated per-item so it reflects real batch data.
# ---------------------------------------------------------------------------
def render_story_html(item: dict) -> str:
    kicker = item["kicker"]
    prompt = item["prompt"].replace("___", '<span style="border-bottom:3px solid #fff;">___</span>')
    surface_icon = "◆" if item["surface"] == "Story" else "▤"
    grounded_badge = "" if item["grounded"] is None else ("✅ verified" if item["grounded"] else "⚠️ ungrounded")
    badge_text = f'{item["source"]} · {grounded_badge} · {surface_icon} {item["surface"]}'.strip(" ·")

    if item["type"] == "This-or-That":
        body = f"""
        <div class="tot-split">
          <div class="tot-side a" onclick="vote(this)"><div class="tot-pct" id="pctA">64%</div><div class="tot-fill" id="fillA"></div><span>{item['options'][0]}</span></div>
          <div class="tot-vs">VS</div>
          <div class="tot-side b" onclick="vote(this)"><div class="tot-pct" id="pctB">36%</div><div class="tot-fill" id="fillB"></div><span>{item['options'][1]}</span></div>
        </div>
        <div class="opinion-strip">✦ opinion-based — not fact-checked</div>
        """
    elif item["type"] == "Guess the Number":
        body = f"""
        <div class="slider-block">
          <div class="slider-track">
            <div class="slider-range" style="left:44%; width:12%;"></div>
            <div class="slider-target" style="left:50%;"></div>
            <div class="slider-handle" id="handle" style="left:20%;"></div>
          </div>
          <div class="slider-labels"><span>0</span><span>1000</span></div>
          <div class="guess-readout" id="readout">200</div>
          <button class="lock-btn" onclick="lockGuess()">Lock In Guess</button>
        </div>
        <div class="explain-strip" id="gtn-explain">{item['explain']}</div>
        """
    else:
        opts_html = ""
        for i, opt in enumerate(item["options"]):
            opts_html += f'<div class="opt" data-correct="{"true" if i==item["correct"] else "false"}" onclick="pickMCQ(this)"><span class="icon">✕</span>{opt}</div>'
        body = f"""
        <div class="quiz-options">{opts_html}</div>
        <div class="explain-strip" id="explain">{item['explain']}</div>
        """

    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
      *{{box-sizing:border-box;}}
      body{{margin:0; font-family:'Inter',sans-serif;}}
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
      .prompt{{font-family:'Baloo 2',sans-serif; font-weight:700; font-size:17px; color:#fff; margin-top:5px; line-height:1.25;}}
      .quiz-options{{padding:14px; display:flex; flex-direction:column; gap:8px;}}
      .opt{{position:relative; padding:10px 12px; border-radius:24px; background:#fff; border:1.6px solid #ECECF2;
        font-size:13.5px; font-weight:700; color:#2E2E3A; cursor:pointer; display:flex; align-items:center; gap:9px;}}
      .opt .icon{{width:20px; height:20px; border-radius:50%; border:2px solid {HOT_PINK}; color:{HOT_PINK};
        display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:800; flex-shrink:0;}}
      .opt.correct{{background:{GREEN}; border-color:{GREEN}; color:#fff;}}
      .opt.correct .icon{{background:#fff; border-color:#fff; color:{GREEN};}}
      .opt.wrong{{opacity:0.5;}}
      .tot-split{{display:flex; gap:8px; padding:14px;}}
      .tot-side{{flex:1; border-radius:16px; position:relative; overflow:hidden; height:110px;
        display:flex; align-items:flex-end; justify-content:center; padding-bottom:10px;
        background:#F4F2FA; border:1.4px solid #ECECF2; cursor:pointer; font-family:'Baloo 2',sans-serif;
        font-weight:700; font-size:14px; color:#2E2E3A;}}
      .tot-fill{{position:absolute; left:0; right:0; bottom:0; height:0%;
        background:linear-gradient(180deg, rgba(236,72,153,0.15), rgba(236,72,153,0.65)); transition:height .6s ease;}}
      .tot-side.b .tot-fill{{background:linear-gradient(180deg, rgba(249,194,75,0.2), rgba(239,90,111,0.65));}}
      .tot-side span{{position:relative; z-index:2;}}
      .tot-side.filled span{{color:#fff;}}
      .tot-pct{{position:absolute; top:8px; z-index:2; font-family:'JetBrains Mono',monospace; font-size:10px; color:#8E8E9A; display:none;}}
      .tot-vs{{position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); z-index:3;
        font-family:'Baloo 2',sans-serif; font-weight:800; font-size:11px; color:#fff;
        background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK}); width:26px; height:26px; border-radius:50%;
        display:flex; align-items:center; justify-content:center; box-shadow:0 0 0 4px #fff;}}
      .opinion-strip{{text-align:center; font-family:'JetBrains Mono',monospace; font-size:9px; color:#8E8E9A; padding:0 14px 12px;}}
      .slider-block{{padding:14px 16px 16px;}}
      .slider-track{{position:relative; height:7px; border-radius:8px; background:#ECECF2; margin:14px 0 6px;}}
      .slider-range{{position:absolute; top:0; bottom:0; background:rgba(236,72,153,0.28); border-radius:8px;}}
      .slider-target{{position:absolute; top:-5px; width:2px; height:16px; background:{VIOLET};}}
      .slider-handle{{position:absolute; top:50%; width:22px; height:22px; border-radius:50%;
        background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK}); border:3px solid #fff;
        transform:translate(-50%,-50%); cursor:grab;}}
      .slider-labels{{display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:9px; color:#8E8E9A;}}
      .guess-readout{{font-family:'Baloo 2',sans-serif; font-weight:800; font-size:24px; text-align:center; color:{VIOLET}; margin-top:2px;}}
      .lock-btn{{display:block; margin:10px auto 0; font-family:'JetBrains Mono',monospace; font-size:10px;
        text-transform:uppercase; color:#fff; background:linear-gradient(120deg,{HEADER_BLUE},{HOT_PINK});
        border:none; padding:8px 18px; border-radius:20px; cursor:pointer; font-weight:700;}}
      .explain-strip{{font-size:10.5px; color:#8E8E9A; padding:0 14px 14px; display:none; line-height:1.4;}}
      .explain-strip.show{{display:block;}}
      .badge-row{{position:relative; z-index:5; padding:0 16px 6px;}}
      .badge{{font-family:'JetBrains Mono',monospace; font-size:8px; padding:3px 8px; border-radius:20px;
        background:rgba(0,0,0,0.28); color:#fff;}}
      .bottom{{position:relative; z-index:5; display:flex; align-items:center; gap:8px; padding:8px 14px 14px;}}
      .cam{{width:32px; height:32px; border-radius:10px; background:rgba(0,0,0,0.25); display:flex;
        align-items:center; justify-content:center; color:#fff; flex-shrink:0;}}
      .reply{{flex:1; height:34px; border-radius:20px; border:1.4px solid rgba(255,255,255,0.65);
        display:flex; align-items:center; padding:0 12px; font-size:11.5px; color:rgba(255,255,255,0.85);}}
      .ic{{width:26px; height:26px; display:flex; align-items:center; justify-content:center; color:#fff;}}
    </style></head>
    <body>
      <div class="phone"><div class="screen">
        <div class="sprinkle dot" style="top:8%; left:12%; width:6px; height:6px; background:#F9C24B;"></div>
        <div class="sprinkle" style="top:6%; left:70%; width:10px; height:4px; background:#fff; transform:rotate(30deg);"></div>
        <div class="sprinkle dot" style="top:70%; left:88%; width:6px; height:6px; background:#EC4899;"></div>
        <div class="sprinkle" style="top:80%; left:10%; width:10px; height:4px; background:#4E7CFF; transform:rotate(50deg);"></div>
        <div class="story-top">
          <div class="segments">{"".join(f'<div class="seg" style="opacity:{1 if i==0 else 0.3}"></div>' for i in range(5))}</div>
          <div class="header">
            <div class="avatar">S</div>
            <div class="who"><b>stapubox</b><span>{item['sport']}</span><span class="tag">{item['difficulty'] if item['type']!='This-or-That' else 'Opinion'}</span></div>
          </div>
        </div>
        <div class="body">
          <div class="card">
            <div class="card-header"><div class="kicker">{kicker}</div><div class="prompt">{prompt}</div></div>
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
            if(o.dataset.correct==='true'){{ o.classList.add('correct'); o.querySelector('.icon').textContent='✓'; }}
            else if(o!==el){{ }} else {{ o.classList.add('wrong'); }}
          }});
          const explain = document.getElementById('explain');
          if(explain) explain.classList.add('show');
        }}
        let voted=false;
        function vote(el){{
          if(voted) return; voted=true;
          const isA = el.classList.contains('a');
          document.getElementById('fillA').style.height = isA ? '64%' : '36%';
          document.getElementById('fillB').style.height = isA ? '36%' : '64%';
          document.getElementById('pctA').style.display='block';
          document.getElementById('pctB').style.display='block';
          document.querySelectorAll('.tot-side').forEach(s=>s.classList.add('filled'));
        }}
        const handle = document.getElementById('handle');
        if(handle){{
          const track = handle.parentElement;
          const readout = document.getElementById('readout');
          let dragging=false;
          function setFromClientX(x){{
            const rect = track.getBoundingClientRect();
            let pct = (x-rect.left)/rect.width; pct=Math.max(0,Math.min(1,pct));
            handle.style.left=(pct*100)+'%'; readout.textContent=Math.round(pct*1000);
          }}
          handle.addEventListener('pointerdown', e=>{{dragging=true; handle.setPointerCapture(e.pointerId);}});
          handle.addEventListener('pointermove', e=>{{ if(dragging) setFromClientX(e.clientX); }});
          handle.addEventListener('pointerup', ()=>dragging=false);
          track.addEventListener('click', e=>{{ if(e.target===track) setFromClientX(e.clientX); }});
        }}
        let locked=false;
        function lockGuess(){{
          if(locked) return; locked=true;
          const el = document.getElementById('gtn-explain');
          if(el) el.classList.add('show');
        }}
      </script>
    </body></html>
    """

# ---------------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">AI-Powered Sports Engagement Content Agent</div>', unsafe_allow_html=True)
st.title("🏆 StapuBox Story Studio")

col_preview, col_controls = st.columns([1.1, 1], gap="large")

with col_controls:
    st.subheader("Creator Controls")
    sport = st.selectbox("Sport", SPORTS, index=0)
    difficulty = st.select_slider("Difficulty", DIFFICULTIES, value="Medium")
    types_selected = st.multiselect("Content types (mix for a varied batch)", TYPES, default=TYPES)

    gen_col1, gen_col2 = st.columns(2)
    with gen_col1:
        if st.button("🔄 Generate Batch", use_container_width=True):
            pool = types_selected if types_selected else TYPES
            st.session_state.batch = [make_mock_item(random.choice(pool), sport, difficulty) for _ in range(5)]
            st.session_state.current = 0
            st.rerun()
    with gen_col2:
        if st.button("↻ Regenerate current item", use_container_width=True):
            cur = st.session_state.current
            t = st.session_state.batch[cur]["type"]
            st.session_state.batch[cur] = make_mock_item(t, sport, difficulty)
            st.rerun()

    st.markdown("**Batch strip**")
    thumb_cols = st.columns(len(st.session_state.batch))
    for i, tc in enumerate(thumb_cols):
        with tc:
            label = st.session_state.batch[i]["type"].split()[0][:4]
            if st.button(label, key=f"thumb_{i}", use_container_width=True):
                st.session_state.current = i
                st.rerun()

    st.divider()
    st.markdown("**Freshness / Grounding Analytics**  \n*(USP feature — mock values shown here; real values come from Phase 3/6 orchestrator)*")
    grounded_count = sum(1 for it in st.session_state.batch if it.get("grounded"))
    total_factual = sum(1 for it in st.session_state.batch if it.get("grounded") is not None)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="val">{grounded_count}/{total_factual or 1}</div><div class="lbl">Grounded first try</div></div>', unsafe_allow_html=True)
    with m2:
        src_mix = len(set(it["source"] for it in st.session_state.batch))
        st.markdown(f'<div class="metric-card"><div class="val">{src_mix}</div><div class="lbl">Source types used</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="val">0</div><div class="lbl">Duplicates rejected</div></div>', unsafe_allow_html=True)

    st.divider()
    export_json = json.dumps(st.session_state.batch, indent=2)
    st.download_button("⇩ Export batch as JSON", data=export_json, file_name="batch.json",
                        mime="application/json", use_container_width=True)

with col_preview:
    current_item = st.session_state.batch[st.session_state.current]
    components.html(render_story_html(current_item), height=660, scrolling=False)
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("⬅ Prev", use_container_width=True, disabled=st.session_state.current == 0):
            st.session_state.current -= 1
            st.rerun()
    with nav2:
        st.markdown(f"<p style='text-align:center; color:rgba(255,255,255,0.6); margin-top:8px;'>Item {st.session_state.current+1} of {len(st.session_state.batch)} — {current_item['type']}</p>", unsafe_allow_html=True)
    with nav3:
        if st.button("Next ➡", use_container_width=True, disabled=st.session_state.current == len(st.session_state.batch) - 1):
            st.session_state.current += 1
            st.rerun()
