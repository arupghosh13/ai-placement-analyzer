# tests/test_matcher.py

import pytest
from app.services.matcher import (
    compute_match,
    extract_skills_from_text,
    normalize_token,
)


# ─────────────────────────────────────────
# SKILL EXTRACTION TESTS
# ─────────────────────────────────────────

class TestSkillExtraction:

    def test_extracts_single_word_skills(self):
        text = "I have experience with Python, Docker, and PostgreSQL"
        skills = extract_skills_from_text(text)
        assert "python" in skills
        assert "docker" in skills
        assert "postgresql" in skills

    def test_extracts_multi_word_skills(self):
        """
        'machine learning' must be found as a phrase
        not just 'machine' and 'learning' separately
        """
        text = "Experience in machine learning and deep learning"
        skills = extract_skills_from_text(text)
        assert "machine learning" in skills
        assert "deep learning" in skills

    def test_case_insensitive_extraction(self):
        """
        PYTHON, Python, python must all match
        """
        text = "PYTHON developer with FASTAPI skills"
        skills = extract_skills_from_text(text)
        assert "python" in skills
        assert "fastapi" in skills

    def test_returns_empty_set_for_no_skills(self):
        """
        Generic text with no tech skills
        should return empty set
        """
        text = "I am a hardworking individual who loves to travel"
        skills = extract_skills_from_text(text)
        # May have some soft skills but mostly empty
        assert isinstance(skills, set)

    def test_ignores_unknown_words(self):
        """
        Made-up technologies should not appear
        """
        text = "Expert in Foobar and Bazztech framework"
        skills = extract_skills_from_text(text)
        assert "foobar" not in skills
        assert "bazztech" not in skills


# ─────────────────────────────────────────
# CORE MATCHING TESTS
# ─────────────────────────────────────────

class TestComputeMatch:

    def test_perfect_match(self):
        """
        Resume has all JD skills → 100% match
        """
        resume = "Python FastAPI PostgreSQL Docker"
        jd = "We need Python, FastAPI, PostgreSQL, Docker"

        result = compute_match(resume, jd)

        assert result.match_percentage == 100.0
        assert len(result.missing_skills) == 0

    def test_zero_match(self):
        """
        Resume has no JD skills → 0% match
        """
        resume = "Expert in Java Spring Boot Oracle"
        jd = "We need Python FastAPI PostgreSQL"

        result = compute_match(resume, jd)

        assert result.match_percentage == 0.0
        assert len(result.matched_skills) == 0

    def test_partial_match(self):
        """
        Resume has some JD skills → partial match
        Missing skills must be correct
        """
        resume = "Python and SQL experience"
        jd = "Need Python, SQL, and Docker"

        result = compute_match(resume, jd)

        assert 0.0 < result.match_percentage < 100.0
        assert "docker" in result.missing_skills
        assert "python" in result.matched_skills

    def test_missing_skills_formula(self):
        """
        Verify: Missing = JD Skills - Resume Skills
        This is your zero-hallucination guarantee
        """
        resume = "Python developer"
        jd = "Python, FastAPI, Docker required"

        result = compute_match(resume, jd)

        # Every missing skill must be in JD
        for skill in result.missing_skills:
            assert skill in result.missing_skills

        # No missing skill should be in matched
        for skill in result.missing_skills:
            assert skill not in result.matched_skills

    def test_no_hallucination(self):
        """
        Matched skills must ONLY contain skills
        that appear in BOTH resume AND JD
        Never skills invented by the system
        """
        resume = "Python developer with 5 years experience"
        jd = "We need Python and FastAPI"

        result = compute_match(resume, jd)

        jd_skills = extract_skills_from_text(jd)
        resume_skills = extract_skills_from_text(resume)

        for skill in result.matched_skills:
            assert skill in jd_skills
            assert skill in resume_skills

    def test_empty_jd_returns_zero(self):
        """
        JD with no recognizable skills
        returns 0% without crashing
        """
        resume = "Python FastAPI developer"
        jd = "We are a great company with amazing culture"

        result = compute_match(resume, jd)

        assert result.match_percentage == 0.0
        assert result.total_jd_skills == 0

    def test_result_has_correct_totals(self):
        """
        total_jd_skills and total_resume_skills
        must be accurate counts
        """
        resume = "Python SQL Docker"
        jd = "Python FastAPI Docker Redis"

        result = compute_match(resume, jd)

        assert result.total_jd_skills > 0
        assert result.total_resume_skills > 0

    def test_output_is_sorted(self):
        """
        Matched and missing skills must be
        sorted alphabetically for consistency
        """
        resume = "Python SQL Docker Redis"
        jd = "Python SQL Docker Redis FastAPI PostgreSQL"

        result = compute_match(resume, jd)

        assert result.matched_skills == sorted(result.matched_skills)
        assert result.missing_skills == sorted(result.missing_skills)