import streamlit as st
import json
import pandas as pd
import io
import re
from src.filter import is_honeypot
from src.scoring import calculate_score, RETRIEVAL_SKILLS, LTR_SKILLS, EVAL_SKILLS, PLUS_SKILLS, IT_SERVICES_COMPANIES

# Set page config
st.set_page_config(
    page_title="Redrob AI-Recruiter Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Adaptive Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .title-text {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa 0%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle-text {
        font-size: 1.2rem;
        color: var(--text-color);
        opacity: 0.7;
        margin-bottom: 2rem;
    }
    
    /* Theme adaptive card layout */
    .candidate-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
    }
    
    .candidate-card:hover {
        transform: translateY(-2px);
        border-color: rgba(167, 139, 250, 0.5);
        box-shadow: 0 10px 15px -3px rgba(167, 139, 250, 0.1);
    }
    
    .badge-pills {
        background: rgba(167, 139, 250, 0.15);
        color: #a78bfa;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        display: inline-block;
    }
    
    .badge-notice {
        background: rgba(244, 114, 182, 0.15);
        color: #f472b6;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .stat-box {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    
    .stat-val {
        font-size: 2rem;
        font-weight: 800;
        color: var(--text-color);
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: var(--text-color);
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# Advanced score calculation with feature-level attribution
def calculate_dynamic_score_breakdown(cand, w_exp, w_title, w_skills, w_signals):
    profile = cand.get("profile", {})
    history = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    
    # 1. Experience Score (Safely parsed and clamped)
    field_exp = float(profile.get("years_of_experience") or 0.0)
    field_exp = max(0.0, field_exp)
    
    if 5.0 <= field_exp <= 9.0:
        exp_score = 1.0
    elif 4.0 <= field_exp < 5.0 or 9.0 < field_exp <= 12.0:
        exp_score = 0.8
    else:
        exp_score = 0.4
        
    # 2. Title Score
    current_title = profile.get("current_title", "")
    current_title = current_title.lower() if current_title else ""
    if any(w in current_title for w in ["ai engineer", "ml engineer", "machine learning engineer", "nlp engineer", "search engineer", "retrieval engineer"]):
        title_score = 1.0
    elif any(w in current_title for w in ["data scientist", "applied scientist", "ml researcher"]):
        title_score = 0.8
    elif any(w in current_title for w in ["backend engineer", "software engineer", "data engineer", "systems engineer", "full stack"]):
        title_score = 0.6
    else:
        title_score = 0.1
        
    # 3. Skills Score
    skills_score = 0.0
    has_retrieval, has_eval, has_ltr = False, False, False
    for s in skills:
        if not s:
            continue
        name = s.get("name", "")
        name = name.lower() if name else ""
        proficiency = s.get("proficiency") or "beginner"
        prof_multiplier = {"expert": 1.0, "advanced": 0.8, "intermediate": 0.5, "beginner": 0.2}.get(proficiency, 0.2)
        
        weight = 0.0
        if name in RETRIEVAL_SKILLS:
            weight = 0.5
            has_retrieval = True
        elif name in LTR_SKILLS:
            weight = 0.6
            has_ltr = True
        elif name in EVAL_SKILLS:
            weight = 0.6
            has_eval = True
        elif name in PLUS_SKILLS:
            weight = 0.3
            
        skills_score += weight * prof_multiplier
        
    skills_score = min(skills_score, 1.0)
    if has_retrieval and has_eval:
        skills_score = min(skills_score + 0.1, 1.0)
        
    # 4. Signals Score
    notice = signals.get("notice_period_days", 90)
    notice = int(notice) if notice is not None else 90
    notice_score = 1.0 if notice <= 30 else (0.8 if notice <= 60 else (0.5 if notice <= 90 else 0.2))
    
    response_rate = signals.get("recruiter_response_rate")
    response_rate = float(response_rate) if response_rate is not None else 1.0
    
    last_active_str = signals.get("last_active_date", "2026-01-01")
    try:
        active_year = int(str(last_active_str).split("-")[0])
        active_score = 1.0 if active_year >= 2026 else (0.7 if active_year == 2025 else 0.3)
    except (ValueError, AttributeError, IndexError, TypeError):
        active_score = 0.3 # Default penalty for invalid/missing dates
        
    signals_score = (notice_score * 0.4) + (response_rate * 0.3) + (active_score * 0.3)
    
    # 5. Modifiers
    loc = profile.get("location")
    loc = loc.lower() if loc else ""
    willing_relocate = signals.get("willing_to_relocate", False)
    loc_mult = 1.0
    if not any(city in loc for city in ["noida", "pune", "delhi", "ncr", "gurgaon", "gurugram"]):
        loc_mult = 0.9 if willing_relocate else 0.6
        
    all_companies = [job.get("company") for job in history if job]
    all_companies = [c.lower() for c in all_companies if c]
    
    current_company = profile.get("current_company")
    if current_company:
        all_companies.append(current_company.lower())
        
    only_services = all(c in IT_SERVICES_COMPANIES for c in all_companies) if all_companies else False
    if only_services:
        loc_mult *= 0.3
        
    weighted_sum = (exp_score * w_exp) + (title_score * w_title) + (skills_score * w_skills) + (signals_score * w_signals)
    final_score = weighted_sum * loc_mult
    
    # Strict gate: If the current title is completely unrelated to tech (title_score is 0.1),
    # aggressively dump their final score to the bottom of the pool.
    if title_score == 0.1:
        final_score *= 0.1
        
    breakdown = {
        "exp_raw": round(exp_score, 2),
        "title_raw": round(title_score, 2),
        "skills_raw": round(skills_score, 2),
        "signals_raw": round(signals_score, 2),
        "notice_score": round(notice_score, 2),
        "response_rate": round(response_rate, 2),
        "active_score": round(active_score, 2),
        "loc_multiplier": round(loc_mult, 2),
        "only_services": only_services
    }
    
    return round(final_score, 3), breakdown

# App header
st.markdown('<div class="title-text">🧠 Redrob AI-Recruiter Brain</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">Interactive Proof of Concept & Match Sandbox (Track 1: Intelligent Candidate Discovery)</div>', unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.markdown("### ⚙️ Search Controls")

# Official Scoring Toggle
use_official_scoring = st.sidebar.checkbox(
    "Use Official Hackathon Weights & Scoring", 
    value=True,
    help="When checked, matches the exact scoring logic and ranking of the generated submission.csv. Mutes custom weighting sliders below."
)

if use_official_scoring:
    # Muted labels representing official relative base weights
    st.sidebar.caption("Skills Alignment: 35%")
    st.sidebar.caption("Current Title Fit: 25%")
    st.sidebar.caption("Experience Years: 20%")
    st.sidebar.caption("Behavioral Signals: 20% (Multiplier)")
    w_skills, w_title, w_exp, w_signals = 0.35, 0.25, 0.20, 0.20
else:
    # Sliders for dynamic weighting
    w_skills = st.sidebar.slider("Skills Alignment Weight", 0.0, 1.0, 0.40, 0.05)
    w_title = st.sidebar.slider("Current Title Fit Weight", 0.0, 1.0, 0.25, 0.05)
    w_exp = st.sidebar.slider("Experience Years Fit Weight", 0.0, 1.0, 0.20, 0.05)
    w_signals = st.sidebar.slider("Behavioral Signals Weight", 0.0, 1.0, 0.15, 0.05)

    # Normalize weights
    total_w = w_skills + w_title + w_exp + w_signals
    if total_w > 0:
        w_skills /= total_w
        w_title /= total_w
        w_exp /= total_w
        w_signals /= total_w

# File Uploader
uploaded_file = st.sidebar.file_uploader("Upload Candidates JSONL file", type=["jsonl", "json"])

# Cached Data Loader for instant slider updates and high scalability
@st.cache_data
def load_candidate_data(file_bytes, file_name):
    # If file_bytes is None, load the default path
    if file_bytes is None:
        default_path = "candidates_subset.jsonl"
        import os
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                if default_path.endswith(".json"):
                    return json.load(f), f"Loaded {default_path} from default cache."
                else:
                    return [json.loads(line) for line in f if line.strip()], f"Loaded {default_path} from default cache."
        else:
            # Fallback to sample if subset not found
            fallback_path = r"[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/sample_candidates.json"
            with open(fallback_path, "r", encoding="utf-8") as f:
                return json.load(f), "Loaded fallback sample from cache."
    else:
        content = file_bytes.decode("utf-8")
        if file_name.endswith(".json"):
            return json.loads(content), f"Loaded {file_name} from uploaded cache."
        else:
            return [json.loads(line) for line in content.split("\n") if line.strip()], f"Loaded {file_name} from uploaded cache."

# Load Candidates
candidates = []
info_msg = ""

try:
    if uploaded_file is not None:
        # Get raw bytes to allow hash caching by Streamlit
        file_bytes = uploaded_file.getvalue()
        candidates, info_msg = load_candidate_data(file_bytes, uploaded_file.name)
        st.sidebar.success(info_msg)
    else:
        candidates, info_msg = load_candidate_data(None, "")
        st.sidebar.info(info_msg)
except Exception as e:
    st.sidebar.error(f"Error loading candidates: {e}")

if candidates:
    # Process
    valid_candidates = []
    honeypot_count = 0
    
    for cand in candidates:
        if is_honeypot(cand):
            honeypot_count += 1
            continue
        
        # Decide between Official and Custom scoring
        if use_official_scoring:
            score, bd = calculate_score(cand, return_breakdown=True)
        else:
            score, bd = calculate_dynamic_score_breakdown(cand, w_exp, w_title, w_skills, w_signals)
            
        valid_candidates.append((score, cand["candidate_id"], cand, bd))
        
    # Sort
    valid_candidates.sort(key=lambda x: x[1]) # Tie break
    valid_candidates.sort(key=lambda x: x[0], reverse=True) # Score sort
    
    # UI Layout
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color: #3b82f6;">{len(candidates)}</div><div class="stat-label">Total Loaded</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color: #ef4444;">{honeypot_count}</div><div class="stat-label">Traps/Honeypots Blocked</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color: #10b981;">{len(valid_candidates)}</div><div class="stat-label">Valid Scored Candidates</div></div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 🏆 Top Ranked Shortlist")
    
    top_display = valid_candidates[:25]
    
    from src.reasoning import generate_reasoning
    
    for idx, (score, cid, cand, bd) in enumerate(top_display):
        profile = cand.get("profile", {})
        skills = cand.get("skills", [])
        signals = cand.get("redrob_signals", {})
        
        rank = idx + 1
        reason = generate_reasoning(cand, rank)
        
        # Color coding the score dynamically based on active scoring mode
        if use_official_scoring:
            if score >= 6.0:
                score_color = "#10b981" # Success Green
            elif score >= 4.0:
                score_color = "#f59e0b" # Warning Amber
            else:
                score_color = "#888888" # Muted Gray
        else:
            if score >= 0.80:
                score_color = "#10b981" # Success Green
            elif score >= 0.60:
                score_color = "#f59e0b" # Warning Amber
            else:
                score_color = "#888888" # Muted Gray
            
        # Sort skills so that target matching skills come first, followed by others
        matching_skills = []
        other_skills = []
        for s in skills:
            if not s:
                continue
            name = s.get("name", "")
            lname = name.lower()
            is_target = (lname in RETRIEVAL_SKILLS or 
                         lname in LTR_SKILLS or 
                         lname in EVAL_SKILLS or 
                         lname in PLUS_SKILLS)
            if is_target:
                matching_skills.append(s)
            else:
                other_skills.append(s)
        sorted_skills = matching_skills + other_skills
        
        # Skill-level badges emphasizing matching target skills
        skill_badges = []
        for s in sorted_skills[:6]:
            name = s.get("name", "")
            lname = name.lower()
            is_target = (lname in RETRIEVAL_SKILLS or 
                         lname in LTR_SKILLS or 
                         lname in EVAL_SKILLS or 
                         lname in PLUS_SKILLS)
            if is_target:
                badge_style = "background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-right: 6px; display: inline-block;"
            else:
                badge_style = "background: rgba(128, 128, 128, 0.08); color: var(--text-color); opacity: 0.75; border: 1px solid rgba(128, 128, 128, 0.2); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; margin-right: 6px; display: inline-block;"
            skill_badges.append(f'<span style="{badge_style}">{name}</span>')
            
        skills_html = " ".join(skill_badges) if skill_badges else '<span style="color: var(--text-color); opacity: 0.5; font-size: 0.8rem;">None listed</span>'
        
        # Card body with theme-adaptive text colors
        st.markdown(f"""
        <div class="candidate-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #a78bfa;">Rank {rank}: {profile.get('anonymized_name')} ({cid})</h4>
                <div style="font-size: 1.5rem; font-weight: 800; color: {score_color};">Score: {score}</div>
            </div>
            <p style="margin: 6px 0; font-size: 0.95rem; font-weight: bold; color: var(--text-color); opacity: 0.95;">{profile.get('current_title')} @ {profile.get('current_company')} | {profile.get('years_of_experience')} Years Exp</p>
            <p style="margin: 4px 0; color: var(--text-color); opacity: 0.8; font-size: 0.9rem;"><strong>Location:</strong> {profile.get('location')} | <strong>Preferred:</strong> {signals.get('preferred_work_mode')}</p>
            <div style="margin: 10px 0; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;">
                <strong style="font-size: 0.85rem; color: var(--text-color); opacity: 0.7; margin-right: 6px;">Skills:</strong>
                {skills_html}
                <span class="badge-notice" style="margin-left: auto;">Notice: {signals.get('notice_period_days')} Days</span>
            </div>
            <div style="background: rgba(167, 139, 250, 0.08); border-left: 3px solid #a78bfa; padding: 10px; border-radius: 4px; font-size: 0.9rem; color: var(--text-color); margin-top: 10px; font-style: italic;">
                "{reason}"
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable Score Attribution details (Explainable AI)
        with st.expander("🔍 Score Attribution (Explainable AI / Feature-Level Breakdown)"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("**Technical Fit Elements**")
                st.caption(f"Experience Match: {bd['exp_raw']} / 1.0")
                st.progress(max(0.0, min(float(bd['exp_raw']), 1.0)))
                st.caption(f"Title Match Index: {bd['title_raw']} / 1.0")
                st.progress(max(0.0, min(float(bd['title_raw']), 1.0)))
            with c2:
                st.markdown("**Skills Alignment**")
                st.caption(f"Tech-Stack Align: {bd['skills_raw']} / 1.0")
                st.progress(max(0.0, min(float(bd['skills_raw']), 1.0)))
            with c3:
                st.markdown("**Behavioral & Availability**")
                st.caption(f"Notice Score: {bd['notice_score']} / 1.0")
                st.progress(max(0.0, min(float(bd['notice_score']), 1.0)))
                st.caption(f"Response Rate: {bd['response_rate']} / 1.0")
                st.progress(max(0.0, min(float(bd['response_rate']), 1.0)))
            with c4:
                st.markdown("**Match Modifiers**")
                st.write(f"- **Location rel. factor**: `{bd['loc_multiplier']}`")
                st.write(f"- **Services-Only penalty**: `{'Applied (0.3x)' if bd['only_services'] else 'None'}`")
                
    # Download Button
    csv_data = io.StringIO()
    writer = csv_writer = csv = pd.DataFrame([
        {
            "candidate_id": item[1],
            "rank": i + 1,
            "score": item[0],
            "reasoning": generate_reasoning(item[2], i + 1)
        } for i, item in enumerate(valid_candidates[:100])
    ])
    
    st.markdown("---")
    st.markdown("### 📥 Download Results CSV")
    csv_file = csv_writer.to_csv(index=False)
    st.download_button(
        label="Download Ranked List (Top 100 CSV)",
        data=csv_file,
        file_name="ranked_candidates.csv",
        mime="text/csv"
    )
else:
    st.warning("No candidate data loaded. Please upload a JSONL file in the sidebar.")
