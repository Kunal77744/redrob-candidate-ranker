# Core skill groups matching the JD
RETRIEVAL_SKILLS = {
    "embeddings", "sentence-transformers", "bge", "e5", "pinecone", "weaviate", 
    "qdrant", "milvus", "faiss", "elasticsearch", "opensearch", "hybrid search", 
    "bm25", "information retrieval", "rag", "vector search", "retrieval", "nlp",
    "search", "ranking", "indexing"
}

LTR_SKILLS = {
    "learning-to-rank", "xgboost", "lightgbm", "re-ranking", "neural ranking", 
    "ranking models", "ltr"
}

EVAL_SKILLS = {
    "ndcg", "mrr", "map", "a/b testing", "offline-to-online", "evaluation", 
    "evaluation frameworks", "metrics"
}

PLUS_SKILLS = {
    "fine-tuning", "lora", "qlora", "peft", "llms", "llamaindex", "langchain",
    "deep learning", "machine learning", "pytorch", "tensorflow"
}

IT_SERVICES_COMPANIES = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture", 
    "cognizant", "capgemini", "tech mahindra", "hcl", "cognizant technology solutions",
    "l&t infotech", "lti", "mindtree", "dxc", "wipro technologies"
}

TIER1_CITIES = {
    "noida", "pune", "delhi", "ncr", "gurgaon", "gurugram", "ghaziabad", 
    "faridabad", "hyderabad", "mumbai", "bangalore", "bengaluru", "chennai", "kolkata"
}

def calculate_score(cand, return_breakdown=False):
    """
    Computes a matching score (0.0 to 10.0) for a candidate against the Senior AI Engineer JD.
    """
    profile = cand.get("profile", {})
    history = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    
    score = 0.0
    
    # -------------------------------------------------------------------------
    # 1. Experience Fit (Max: 2.0)
    # -------------------------------------------------------------------------
    # Safely convert to float, clamp at 0, and check boundary ranges
    field_exp = float(profile.get("years_of_experience") or 0.0)
    field_exp = max(0.0, field_exp)
    
    if 5.0 <= field_exp <= 9.0:
        exp_score = 2.0
    elif 4.0 <= field_exp < 5.0:
        exp_score = 1.6
    elif 9.0 < field_exp <= 12.0:
        exp_score = 1.8
    elif 3.0 <= field_exp < 4.0:
        exp_score = 1.0
    elif 12.0 < field_exp <= 15.0:
        exp_score = 1.2
    elif field_exp > 15.0:
        exp_score = 1.0 # Keep overqualified above fresher level (0.5)
    else:
        exp_score = 0.5
    score += exp_score

    # -------------------------------------------------------------------------
    # 2. Current Title Fit (Max: 2.5)
    # -------------------------------------------------------------------------
    current_title = profile.get("current_title", "")
    current_title = current_title.lower() if current_title else ""
    title_score = 0.0
    if any(w in current_title for w in ["ai engineer", "ml engineer", "machine learning engineer", "nlp engineer", "search engineer", "retrieval engineer"]):
        title_score = 2.5
    elif any(w in current_title for w in ["data scientist", "applied scientist", "ml researcher"]):
        title_score = 2.0
    elif any(w in current_title for w in ["backend engineer", "software engineer", "data engineer", "systems engineer", "full stack developer", "fullstack"]):
        title_score = 1.5
    elif any(w in current_title for w in ["architect", "tech lead", "lead engineer"]):
        title_score = 1.2
    else:
        # Heavily downweight unrelated titles (like Marketing Manager, HR Manager)
        title_score = 0.0
    score += title_score

    # -------------------------------------------------------------------------
    # 3. Skills Alignment (Max: 3.5)
    # -------------------------------------------------------------------------
    skills_score = 0.0
    has_retrieval = False
    has_eval = False
    has_ltr = False
    has_llm = False
    
    for s in skills:
        if not s:
            continue
        name = s.get("name", "")
        name = name.lower() if name else ""
        proficiency = s.get("proficiency") or "beginner"
        duration = s.get("duration_months") or 0
        endorsements = s.get("endorsements") or 0
        
        # Determine proficiency multiplier
        prof_multiplier = {
            "expert": 1.0,
            "advanced": 0.8,
            "intermediate": 0.5,
            "beginner": 0.2
        }.get(proficiency, 0.2)
        
        # Trust factor based on duration and endorsements (safe from None values)
        trust_factor = 1.0 + (min(float(duration), 60.0) / 60.0) * 0.3 + (min(float(endorsements), 50.0) / 50.0) * 0.2
        
        skill_weight = 0.0
        if name in RETRIEVAL_SKILLS:
            skill_weight = 0.5
            has_retrieval = True
        elif name in LTR_SKILLS:
            skill_weight = 0.6
            has_ltr = True
        elif name in EVAL_SKILLS:
            skill_weight = 0.6
            has_eval = True
        elif name in PLUS_SKILLS:
            skill_weight = 0.3
            has_llm = True
            
        if skill_weight > 0:
            skills_score += skill_weight * prof_multiplier * trust_factor
            
    # Cap skills score to prevent keyword stuffers from dominating
    skills_score = min(skills_score, 3.0)
    
    # Bonuses for cross-discipline capability (highly valued in JD)
    if has_retrieval and has_eval:
        skills_score += 0.3 # Strong bonus for retrieval + eval
    if has_ltr:
        skills_score += 0.2 # Bonus for Learning-to-rank
        
    score += min(skills_score, 3.5)

    # -------------------------------------------------------------------------
    # 4. Behavioral and Availability Modifiers (Multiplier / Modifier)
    # -------------------------------------------------------------------------
    behavior_mult = 1.0
    
    # Notice Period (sub-30 is bonus, >90 is penalty) (Safe from None value keys)
    notice_days = signals.get("notice_period_days")
    notice_days = int(notice_days) if notice_days is not None else 90
    
    if notice_days <= 15:
        behavior_mult *= 1.15
    elif notice_days <= 30:
        behavior_mult *= 1.1
    elif notice_days <= 60:
        behavior_mult *= 1.0
    elif notice_days <= 90:
        behavior_mult *= 0.85
    else:
        behavior_mult *= 0.6 # >90 days is heavily penalized
        
    # Recruiter Response Rate (Safe from None value keys)
    response_rate = signals.get("recruiter_response_rate")
    response_rate = float(response_rate) if response_rate is not None else 1.0
    # Factor: 0.6 + 0.4 * response_rate. If 5%, it's 0.62. If 90%, it's 0.96.
    behavior_mult *= (0.6 + 0.4 * response_rate)
    
    # Activity recency (signup & last active)
    last_active_str = signals.get("last_active_date", "2020-01-01")
    active_year = 2020
    try:
        active_year = int(str(last_active_str).split("-")[0])
        if active_year >= 2026:
            behavior_mult *= 1.0
        elif active_year == 2025:
            behavior_mult *= 0.85
        elif active_year == 2024:
            behavior_mult *= 0.6
        else:
            behavior_mult *= 0.4 # Inactive for > 2 years is not available
    except (ValueError, AttributeError, IndexError, TypeError):
        behavior_mult *= 0.4 # Default penalty for invalid/None activity dates
        
    # Interview Completion Rate
    completion_rate = signals.get("interview_completion_rate")
    completion_rate = float(completion_rate) if completion_rate is not None else 1.0
    behavior_mult *= (0.7 + 0.3 * completion_rate)
    
    # Location Match & Relocation
    loc = profile.get("location")
    loc = loc.lower() if loc else ""
    country = profile.get("country")
    country = country.lower() if country else ""
    willing_relocate = signals.get("willing_to_relocate", False)
    
    loc_score = 1.0
    if any(city in loc for city in ["noida", "pune", "delhi", "ncr", "gurgaon", "gurugram", "ghaziabad", "faridabad"]):
        loc_score = 1.0
    elif any(city in loc for city in ["hyderabad", "mumbai", "bangalore", "bengaluru", "chennai", "kolkata"]):
        if willing_relocate:
            loc_score = 0.9
        else:
            loc_score = 0.7 # Tier-1 but unwilling to relocate to Noida/Pune
    else:
        # Outside Tier-1 or abroad
        if country not in ["india", "in"] and country != "":
            loc_score = 0.3 # Visa issue case-by-case
        else:
            loc_score = 0.8 if willing_relocate else 0.5
            
    behavior_mult *= loc_score
    
    # -------------------------------------------------------------------------
    # 5. Strict Disqualifiers & Red Flags (Penalties)
    # -------------------------------------------------------------------------
    # Red Flag A: IT Services / Consulting only
    all_companies = [job.get("company") for job in history if job]
    all_companies = [c.lower() for c in all_companies if c]
    
    # Always append current company if available to represent their entire career
    current_company = profile.get("current_company")
    if current_company:
        all_companies.append(current_company.lower())
        
    only_services = False
    if all_companies:
        only_services = all(c in IT_SERVICES_COMPANIES for c in all_companies)
        if only_services:
            behavior_mult *= 0.25 # Severe penalty for only IT services history
            
    # Red Flag B: Research-only without production
    all_titles = [job.get("title") for job in history if job]
    all_titles = [t.lower() for t in all_titles if t]
    
    # Always append current title to represent their entire career
    current_title = profile.get("current_title")
    if current_title:
        all_titles.append(current_title.lower())
        
    research_keywords = ["researcher", "research assistant", "scientist", "professor", "phd", "fellow", "postdoc"]
    only_research = all(any(rk in t for rk in research_keywords) for t in all_titles) if all_titles else False
    if only_research:
        behavior_mult *= 0.3 # Severe penalty for research-only without production engineering
        
    # Red Flag C: LangChain-only recent AI experience (under 12 months)
    # If they have LangChain/OpenAI but no other ML, NLP or retrieval skills
    has_langchain = any(s.get("name") and s.get("name").lower() in ["langchain", "openai"] for s in skills if s)
    has_traditional_ml = has_retrieval or has_ltr or has_eval or any(s.get("name") and s.get("name").lower() in ["nlp", "machine learning", "tensorflow", "pytorch", "scikit-learn"] for s in skills if s)
    if has_langchain and not has_traditional_ml:
        behavior_mult *= 0.4
        
    final_score = score * behavior_mult
    
    # Strict gate: If the current title is completely unrelated to tech/engineering (title_score is 0),
    # aggressively dump their final score to the bottom of the pool.
    if title_score == 0.0:
        final_score *= 0.1
        
    if return_breakdown:
        # Map notice days to a normalized score [0, 1] for UI visualization
        notice_score = 1.0 if notice_days <= 30 else (0.8 if notice_days <= 60 else (0.5 if notice_days <= 90 else 0.2))
        active_score = 1.0 if active_year >= 2026 else (0.7 if active_year == 2025 else 0.3)
        
        breakdown = {
            "exp_raw": round(exp_score / 2.0, 2),        # Max score is 2.0
            "title_raw": round(title_score / 2.5, 2),    # Max score is 2.5
            "skills_raw": round(skills_score / 3.5, 2),  # Max score is 3.5
            "signals_raw": round(min(behavior_mult / 1.15, 1.0), 2),  # Normalized by max multiplier
            "notice_score": round(notice_score, 2),
            "response_rate": round(response_rate, 2),
            "active_score": round(active_score, 2),
            "loc_multiplier": round(loc_score, 2),
            "only_services": only_services
        }
        return round(final_score, 3), breakdown
        
    return round(final_score, 3)
