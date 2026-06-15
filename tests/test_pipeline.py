import unittest
import sys
import os

# Add the workspace root to sys.path so we can import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.filter import is_honeypot
from src.scoring import calculate_score

class TestRecruiterPipeline(unittest.TestCase):
    def test_valid_candidate_passes(self):
        """Verifies that a genuine candidate is not flagged as a honeypot."""
        valid_cand = {
            "candidate_id": "CAND_TEST_01",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "AI Engineer",
                "current_company": "Yellow.ai"
            },
            "skills": [
                {"name": "Qdrant", "proficiency": "expert", "duration_months": 24}
            ],
            "career_history": [
                {"company": "Yellow.ai", "duration_months": 72}
            ]
        }
        self.assertFalse(is_honeypot(valid_cand))

    def test_honeypot_detection(self):
        """Verifies that a candidate with expert skills and 0 months experience is blocked."""
        honeypot_cand = {
            "candidate_id": "CAND_TEST_02",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "AI Engineer",
                "current_company": "Yellow.ai"
            },
            "skills": [
                {"name": "Qdrant", "proficiency": "expert", "duration_months": 0}
            ],
            "career_history": [
                {"company": "Yellow.ai", "duration_months": 72}
            ]
        }
        self.assertTrue(is_honeypot(honeypot_cand))

    def test_title_gating_suppression(self):
        """Verifies that non-technical roles (like Accountants) get aggressively suppressed."""
        ai_cand = {
            "candidate_id": "CAND_TEST_03",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "AI Research Engineer",
                "current_company": "Yellow.ai"
            },
            "skills": [
                {"name": "Pinecone", "proficiency": "expert", "duration_months": 24}
            ],
            "career_history": [
                {"company": "Yellow.ai", "duration_months": 72}
            ],
            "redrob_signals": {
                "notice_period_days": 30,
                "recruiter_response_rate": 0.9,
                "last_active_date": "2026-05-24"
            }
        }
        ai_score = calculate_score(ai_cand)

        accountant_cand = {
            "candidate_id": "CAND_TEST_04",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "Accountant",
                "current_company": "Yellow.ai"
            },
            "skills": [
                {"name": "Pinecone", "proficiency": "expert", "duration_months": 24}
            ],
            "career_history": [
                {"company": "Yellow.ai", "duration_months": 72}
            ],
            "redrob_signals": {
                "notice_period_days": 30,
                "recruiter_response_rate": 0.9,
                "last_active_date": "2026-05-24"
            }
        }
        accountant_score = calculate_score(accountant_cand)
        self.assertTrue(accountant_score < (ai_score * 0.2))

    def test_it_services_penalty(self):
        """Verifies that an IT Services only career history triggers the 0.25x penalty."""
        product_cand = {
            "candidate_id": "CAND_TEST_05",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "AI Engineer",
                "current_company": "Glance"
            },
            "skills": [{"name": "Pinecone", "proficiency": "expert", "duration_months": 24}],
            "career_history": [{"company": "Glance", "duration_months": 72}],
            "redrob_signals": {"notice_period_days": 30, "recruiter_response_rate": 0.9}
        }
        product_score = calculate_score(product_cand)

        service_cand = {
            "candidate_id": "CAND_TEST_06",
            "profile": {
                "years_of_experience": 6.0,
                "current_title": "AI Engineer",
                "current_company": "Wipro"
            },
            "skills": [{"name": "Pinecone", "proficiency": "expert", "duration_months": 24}],
            "career_history": [{"company": "Wipro", "duration_months": 72}],
            "redrob_signals": {"notice_period_days": 30, "recruiter_response_rate": 0.9}
        }
        service_score = calculate_score(service_cand)
        self.assertTrue(service_score < (product_score * 0.35))

    def test_langchain_only_penalty(self):
        """Verifies that candidates with only LangChain but no core ML/retrieval are penalized."""
        ml_cand = {
            "candidate_id": "CAND_TEST_07",
            "profile": {"years_of_experience": 6.0, "current_title": "AI Engineer", "current_company": "Yellow.ai"},
            "skills": [
                {"name": "LangChain", "proficiency": "expert", "duration_months": 24},
                {"name": "NLP", "proficiency": "expert", "duration_months": 24}
            ],
            "career_history": [{"company": "Yellow.ai", "duration_months": 72}],
            "redrob_signals": {"notice_period_days": 30}
        }
        ml_score = calculate_score(ml_cand)

        wrapper_cand = {
            "candidate_id": "CAND_TEST_08",
            "profile": {"years_of_experience": 6.0, "current_title": "AI Engineer", "current_company": "Yellow.ai"},
            "skills": [
                {"name": "LangChain", "proficiency": "expert", "duration_months": 24}
            ],
            "career_history": [{"company": "Yellow.ai", "duration_months": 72}],
            "redrob_signals": {"notice_period_days": 30}
        }
        wrapper_score = calculate_score(wrapper_cand)
        self.assertTrue(wrapper_score < (ml_score * 0.5))

    def test_experience_boundary(self):
        """Verifies that experience scores drop step-wise outside the optimal 5-9 years sweet spot."""
        opt_cand = {
            "candidate_id": "CAND_TEST_09",
            "profile": {"years_of_experience": 5.0, "current_title": "AI Engineer", "current_company": "Yellow.ai"},
            "skills": [{"name": "Pinecone", "proficiency": "expert", "duration_months": 24}],
            "career_history": [{"company": "Yellow.ai", "duration_months": 60}],
            "redrob_signals": {"notice_period_days": 30}
        }
        opt_score = calculate_score(opt_cand)

        sub_opt_cand = {
            "candidate_id": "CAND_TEST_10",
            "profile": {"years_of_experience": 4.99, "current_title": "AI Engineer", "current_company": "Yellow.ai"},
            "skills": [{"name": "Pinecone", "proficiency": "expert", "duration_months": 24}],
            "career_history": [{"company": "Yellow.ai", "duration_months": 60}],
            "redrob_signals": {"notice_period_days": 30}
        }
        sub_opt_score = calculate_score(sub_opt_cand)
        self.assertTrue(sub_opt_score < opt_score)

    def test_null_fields_robustness(self):
        """Verifies that the scoring and filter engines handle missing or Null/None values without crashing."""
        corrupted_cand = {
            "candidate_id": "CAND_TEST_11",
            "profile": {
                "years_of_experience": None,
                "current_title": None,
                "current_company": None,
                "summary": None
            },
            "skills": [
                {"name": None, "proficiency": None, "duration_months": None, "endorsements": None}
            ],
            "career_history": [
                {"company": None, "title": None, "duration_months": None}
            ],
            "redrob_signals": {
                "notice_period_days": None,
                "recruiter_response_rate": None,
                "last_active_date": None,
                "willing_to_relocate": None
            }
        }
        
        # Test that they do not raise any exceptions
        try:
            is_trap = is_honeypot(corrupted_cand)
            score = calculate_score(corrupted_cand)
        except Exception as e:
            self.fail(f"System crashed on None-value candidate with exception: {e}")

    def test_reasoning_robustness(self):
        """Verifies that the reasoning generator does not crash on None or missing values."""
        from src.reasoning import generate_reasoning
        corrupted_cand = {
            "candidate_id": None,
            "profile": {
                "years_of_experience": None,
                "current_title": None,
                "current_company": None,
                "location": None
            },
            "skills": [
                None,
                {"name": None}
            ],
            "career_history": [],
            "redrob_signals": {
                "notice_period_days": None,
                "recruiter_response_rate": None
            }
        }
        try:
            reason = generate_reasoning(corrupted_cand, 50)
            self.assertTrue(isinstance(reason, str))
            self.assertTrue(len(reason) > 0)
        except Exception as e:
            self.fail(f"Reasoning generator crashed on None values with: {e}")

if __name__ == "__main__":
    unittest.main()
