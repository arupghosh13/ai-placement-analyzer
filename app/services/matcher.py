# app/services/matcher.py

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# SKILL KEYWORD DICTIONARY
# Option C: keyword list + tokenization
# This is YOUR decision from earlier — enforced here
# Phase 4 will add synonym matching & Levenshtein distance
# ─────────────────────────────────────────


SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "golang", "go", "rust", "ruby", "php", "swift", "kotlin", "scala",
    "r", "matlab", "bash", "shell", "powershell", "perl", ".net" ,

    # Web Frameworks
    "fastapi", "django", "flask", "express", "expressjs", "nextjs",
    "next.js", "react", "reactjs", "react.js", "angular", "vue",
    "vuejs", "vue.js", "spring", "springboot", "spring boot",
    "laravel", "rails", "ruby on rails", "asp.net", "fastify",

    # Databases
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "cassandra", "dynamodb", "elasticsearch", "neo4j", "mariadb",
    "oracle", "mssql", "sql server", "cockroachdb", "supabase",
    "firebase", "firestore", "neon",

    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "k8s", "terraform", "ansible", "jenkins", "github actions",
    "gitlab ci", "circleci", "helm", "prometheus", "grafana",
    "nginx", "apache", "linux", "ubuntu",

    # AI / ML
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "sklearn", "keras",
    "hugging face", "langchain", "llm", "openai", "gemini",
    "pandas", "numpy", "matplotlib", "seaborn", "opencv",
    "rag", "vector database", "pgvector", "embeddings",

    # Backend Concepts
    "rest", "restful", "graphql", "grpc", "websockets", "api",
    "microservices", "message queue", "kafka", "rabbitmq", "celery",
    "arq", "redis queue", "jwt", "oauth", "oauth2", "authentication",
    "authorization", "idempotency", "rate limiting", "caching",

    # Testing
    "pytest", "unittest", "jest", "mocha", "cypress", "selenium",
    "postman", "tdd", "bdd",

    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "agile",
    "scrum", "ci/cd", "devops", "linux", "vim",

    # Data & Analytics
    "sql", "nosql", "etl", "data pipeline", "spark", "airflow",
    "dbt", "snowflake", "bigquery", "tableau", "power bi",

    # Soft Skills (from your spec)
    "communication", "teamwork", "leadership", "problem solving",
    "critical thinking", "collaboration", "time management",
}


# ─────────────────────────────────────────
# RESULT DATA CLASS
# Structured output from the matcher
# ─────────────────────────────────────────

@dataclass
class MatchResult:
    matched_skills: list
    missing_skills: list
    match_percentage: float
    total_jd_skills: int
    total_resume_skills: int


# ─────────────────────────────────────────
# NORMALIZATION
# Lowercase + remove punctuation
# Your Phase 1 decision — enforced here
# ─────────────────────────────────────────

def normalize_token(token: str) -> str:
    """
    Normalize a single token for comparison.
    Converts to lowercase and strips punctuation.

    Examples:
        "Python,"  → "python"
        "FastAPI!" → "fastapi"
        "Node.js"  → "nodejs"
        "C++"      → "c++"   (keeps + intentionally)
    """
    token = token.lower().strip()
    # Remove punctuation except + and # (needed for C++, C#)
    token = re.sub(r"[^\w\s+#.]", "", token)
    return token.strip()


def extract_skills_from_text(text: str) -> set:
    """
    Extract skills from raw text using two strategies (Option C):

    Strategy 1 — Multi-word keyword matching:
        Scan the full text for known multi-word skills
        e.g. "machine learning", "spring boot", "ruby on rails"

    Strategy 2 — Single-word token matching:
        Tokenize the full text and check each word
        against the skill dictionary

    Returns:
        Set of normalized skill strings found in the text
    """
    found_skills = set()
    normalized_text = text.lower()

    # ── Strategy 1: Multi-word phrase matching ──────────
    # Must run BEFORE tokenization to catch "machine learning"
    # before "machine" and "learning" are checked separately
    for skill in SKILLS:
        if " " in skill:  # Only multi-word skills here
            if skill in normalized_text:
                found_skills.add(skill)
                logger.debug(f"Multi-word match found: '{skill}'")

    # ── Strategy 2: Single-word token matching ──────────
    # Split text into individual tokens and check each one
    tokens = re.findall(r"[\w+#.]+", normalized_text)

    for raw_token in tokens:
        normalized = normalize_token(raw_token)
        if normalized in SKILLS:
            found_skills.add(normalized)
            logger.debug(f"Token match found: '{normalized}'")

    logger.info(f"Skills extracted: {len(found_skills)} found")
    return found_skills


# ─────────────────────────────────────────
# CORE MATCHING ENGINE
# This is the zero-hallucination guarantee
# Pure set math — no inference, no guessing
# ─────────────────────────────────────────

def compute_match(
    resume_text: str,
    jd_text: str
) -> MatchResult:
    """
    Deterministic skill gap computation.

    Formula (from your spec):
        Missing Skills = Normalized(JD Skills) - Normalized(Resume Skills)
        Match %        = (Matched / Total JD Skills) * 100

    Args:
        resume_text: Raw extracted text from resume
        jd_text: Raw job description text extracted from job description given by user

    Returns:
        MatchResult with matched, missing, percentage, totals
    """

    # ── Extract skills from both documents ─────────────
    resume_skills = extract_skills_from_text(resume_text)
    jd_skills = extract_skills_from_text(jd_text)

    logger.info(
        f"Resume skills: {len(resume_skills)} | "
        f"JD skills: {len(jd_skills)}"
    )

    # ── Edge case: JD has no recognizable skills ────────
    if not jd_skills:
        logger.warning("No skills extracted from JD — returning zero match")
        return MatchResult(
            matched_skills=[],
            missing_skills=[],
            match_percentage=0.0,
            total_jd_skills=0,
            total_resume_skills=0
        )

    # ── Core set math (your zero-hallucination formula) ─
    matched = resume_skills & jd_skills        # Intersection
    missing = jd_skills - resume_skills        # Difference

    # ── Calculate percentage ────────────────────────────
    match_percentage = round((len(matched) / len(jd_skills)) * 100, 2)

    logger.info(
        f"Match: {match_percentage}% | "
        f"Matched: {len(matched)} | "
        f"Missing: {len(missing)}"
    )

    return MatchResult(
        matched_skills=sorted(list(matched)),   # Sorted = consistent output
        missing_skills=sorted(list(missing)),
        match_percentage=match_percentage,
        total_jd_skills=len(jd_skills),
        total_resume_skills=len(resume_skills)
    )