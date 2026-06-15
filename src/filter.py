import re

# Regex to find experience years in candidate summaries
EXP_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs|year)\s+(?:of\s+)?(?:hands-on\s+)?experience", 
    re.IGNORECASE
)

def is_honeypot(cand):
    """
    Identifies if a candidate profile is a honeypot or contains impossible contradictions.
    Returns True if it's a trap, False otherwise.
    """
    profile = cand.get("profile", {})
    history = cand.get("career_history", [])
    skills = cand.get("skills", [])
    
    # 1. Rule A: Expert skills with 0 duration months (Optimized using any())
    # Real experts have worked with their expert skills.
    if any(s.get("proficiency") == "expert" and (s.get("duration_months") or 0) == 0 for s in skills if s):
        return True
        
    # 2. Rule B: Experience field vs Summary text mismatch (Robust findall check)
    summary = profile.get("summary", "")
    field_exp = float(profile.get("years_of_experience") or 0.0)
    field_exp = max(0.0, field_exp)
    
    matches = EXP_PATTERN.findall(summary) if summary else []
    if matches:
        # Only flag if ALL mentioned experience values contradict the profile field exp.
        # This prevents false positives when a summary mentions sub-skills experience.
        contradicts = all(abs(field_exp - float(num)) > 1.0 for num in matches)
        if contradicts:
            return True
            
    # 3. Rule C: Job duration sum vs profile experience mismatch (Optimized generator sum)
    total_job_months = sum((job.get("duration_months") or 0) for job in history if job)
    profile_months = field_exp * 12
    if abs(total_job_months - profile_months) > 36: # More than 3 years difference
        return True
        
    return False
