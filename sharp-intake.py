import streamlit as st
import pandas as pd
import json
import os
from anthropic import Anthropic
from pypdf import PdfReader
from docx import Document

# ==============================================================================
# 🧠 SHARP-STANDARDS PROTOCOL (Intake v1.0)
# ==============================================================================
# 1. VISUAL IDENTITY: Deep Black (#0e1117), Neon Cyan (#00e5ff), Neon Green (#39ff14)
# 2. OPS CENTER: Live Cost, Status Tile, Version v1.0
# 3. LOGIC: Candidate Extraction (n8n Port), Profile Matching, Database Entry
# ==============================================================================

APP_VERSION = "v1.0"
st.set_page_config(page_title="Sharp Intake", page_icon="📥", layout="wide")

# --- CSS: SHARP PALETTE ---
st.markdown("""
<style>
    /* MAIN BACKGROUND */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    
    /* INPUTS */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1c1c1c !important;
        color: #00e5ff !important;
        border: 1px solid #333 !important;
        font-family: 'Helvetica Neue', sans-serif !important;
    }
    
    /* UPLOADER */
    div[data-testid="stFileUploader"] section {
        background-color: #161b22;
        border: 2px dashed #00e5ff; 
        border-radius: 10px;
        min-height: 120px !important; 
        display: flex; align-items: center; justify-content: center;
    }
    div[data-testid="stFileUploader"] section:hover { border-color: #00ffab; }

    /* HEADERS */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #00e5ff, #d500f9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }
    
    /* BUTTONS */
    div[data-testid="stButton"] button {
        background: linear-gradient(45deg, #00e5ff, #00ffab) !important;
        color: #000000 !important;
        border: none !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        transition: transform 0.2s;
    }
    div[data-testid="stButton"] button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px #00ffab;
    }
    
    /* STATUS BOX */
    .status-box {
        background-color: #1c1c1c;
        border-left: 3px solid #d500f9;
        padding: 10px;
        font-family: monospace;
        color: #aaa;
        font-size: 0.9rem;
    }
    
    div[data-testid="stMetricValue"] { color: #39ff14 !important; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'intake_results' not in st.session_state: st.session_state.intake_results = []
if 'total_cost' not in st.session_state: st.session_state.total_cost = 0.0
if 'processing_log' not in st.session_state: st.session_state.processing_log = "Intake System Online."

# --- SECRETS ---
try:
    ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
except:
    st.error("❌ Missing Anthropic API Key.")
    st.stop()

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# --- UTILITIES ---

def update_status(msg):
    st.session_state.processing_log = msg

def track_cost(amount):
    st.session_state.total_cost += amount

def extract_text(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PdfReader(file)
            return "\n".join([p.extract_text() for p in reader.pages])
        elif file.name.endswith('.docx'):
            return "\n".join([p.text for p in Document(file).paragraphs])
        elif file.name.endswith('.txt'):
            return file.read().decode("utf-8")
        return ""
    except: return ""

def clean_json(text):
    text = text.strip()
    if "```json" in text: text = text.split("```json")[1].split("```")[0]
    elif "```" in text: text = text.split("```")[1].split("```")[0]
    return json.loads(text)

# --- INTELLIGENCE ENGINE (The n8n Logic) ---

def process_application(cv_text, profile_wanted, filename):
    """
    Simulates the 'Extraction -> Summarization -> HR Expert' flow from n8n.
    """
    
    # STEP 1: EXTRACTION (Personal Data + Quals)
    extraction_prompt = f"""
    You are an expert extraction algorithm. Extract relevant info from this CV.
    
    CV TEXT:
    {cv_text[:10000]}

    Extract these specific fields:
    1. Name (Infer from top of CV)
    2. Email (Infer from header)
    3. City/Location
    4. Education (Summary)
    5. Job History (Summary of last 2 roles)
    6. Skills (Comma separated list)

    OUTPUT JSON:
    {{
        "name": "...",
        "email": "...",
        "city": "...",
        "education": "...",
        "history": "...",
        "skills": "..."
    }}
    """
    
    try:
        msg_ext = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1000, temperature=0.0,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        track_cost(0.01)
        extracted = clean_json(msg_ext.content[0].text)
    except:
        return {"name": filename, "vote": 0, "consideration": "Extraction Failed"}

    # STEP 2: HR EXPERT VOTING (Matching against Profile Wanted)
    voting_prompt = f"""
    You are an HR Expert. Evaluate this candidate against the Desired Profile.

    DESIRED PROFILE:
    "{profile_wanted}"

    CANDIDATE SUMMARY:
    Location: {extracted.get('city')}
    Skills: {extracted.get('skills')}
    History: {extracted.get('history')}
    Education: {extracted.get('education')}

    TASK:
    Vote 1-10 on fit. 
    1 = Not in line. 10 = Ideal match.

    OUTPUT JSON:
    {{
        "vote": 0,
        "consideration": "One sentence justification."
    }}
    """

    try:
        msg_vote = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, temperature=0.2,
            messages=[{"role": "user", "content": voting_prompt}]
        )
        track_cost(0.01)
        vote_data = clean_json(msg_vote.content[0].text)
        
        # Merge results
        return {**extracted, **vote_data}
    except:
        return {"name": filename, "vote": 0, "consideration": "Scoring Failed"}

# --- LAYOUT ---

# OPS CENTER
c_title, c_meta = st.columns([3, 1])
with c_title:
    st.title("📥 Sharp Intake")
    st.caption("High-Volume Application Processing")
with c_meta:
    st.markdown(f"<div style='text-align: right; color: #666;'>{APP_VERSION}</div>", unsafe_allow_html=True)
    st.metric("Session Cost", f"${st.session_state.total_cost:.4f}")
    st.markdown(f"<div class='status-box'><span style='color: #00e5ff;'>● INTAKE ACTIVE</span><br>{st.session_state.processing_log}</div>", unsafe_allow_html=True)

# INPUTS
c_profile, c_upload = st.columns([1, 2])

with c_profile:
    st.markdown("### 1. Profile Wanted")
    # Defaulting to the text from your n8n workflow for consistency
    default_profile = "We are a web agency looking for a full-stack web developer who knows PHP, Python and Javascript. Must have experience in the sector and lives in Northern Italy."
    profile_wanted = st.text_area("Define the Ideal Candidate", value=default_profile, height=250)

with c_upload:
    st.markdown("### 2. Incoming Applications")
    uploaded_files = st.file_uploader("Upload CVs (PDF/DOCX)", type=['pdf','docx','txt'], accept_multiple_files=True)

st.write("")
if st.button("Start Intake Processing", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("⚠️ No CVs uploaded.")
    else:
        st.session_state.intake_results = []
        
        with st.status("🚀 Processing Applications...", expanded=True) as status:
            total = len(uploaded_files)
            
            for i, file in enumerate(uploaded_files):
                update_status(f"Processing {i+1}/{total}: {file.name}")
                st.write(f"📄 Extracting data from **{file.name}**...")
                
                text = extract_text(file)
                if text:
                    result = process_application(text, profile_wanted, file.name)
                    st.session_state.intake_results.append(result)
            
            update_status("Intake Complete.")
            status.update(label="✅ All Applications Processed!", state="complete", expanded=False)

# --- DATABASE VIEW ---
if st.session_state.intake_results:
    st.divider()
    st.subheader("📊 Candidate Database")
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.intake_results)
    
    # Sort by Vote (Highest First)
    if 'vote' in df.columns:
        df = df.sort_values(by='vote', ascending=False)
    
    # Display nicely
    st.dataframe(
        df,
        column_config={
            "vote": st.column_config.ProgressColumn("Fit Score", format="%d/10", min_value=0, max_value=10),
            "email": st.column_config.LinkColumn("Contact"),
            "consideration": "HR Notes"
        },
        use_container_width=True,
        hide_index=True,
        column_order=["name", "vote", "city", "skills", "consideration", "email"]
    )
    
    # Export Option
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download Database (CSV)",
        csv,
        "candidate_intake.csv",
        "text/csv",
        key='download-csv'
    )
