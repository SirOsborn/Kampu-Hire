"""
Job requirements extractor:
- Given a job title and description, extract required skills and evaluation criteria.
- Uses SEA-LION AI plus local ontology to produce a reusable requirement profile.
"""
from __future__ import annotations
from typing import Dict, Any
from dataclasses import dataclass

from app.services.sealion_skill_extractor import extract_skills_with_sealion
from app.services.local_skill_miner import mine_skills_locally


@dataclass
class JobRequirementProfile:
    job_title: str
    description: str
    required_skills: list[str]
    key_technologies: list[str]
    criteria_weights: Dict[str, float]
    notes: str


DEFAULT_CRITERIA_WEIGHTS = {
    'technical_skills': 0.30,
    'experience_relevance': 0.25,
    'experience_depth': 0.15,
    'education_relevance': 0.10,
    'problem_solving': 0.10,
    'communication': 0.05,
    'learning_ability': 0.05,
}


def extract_job_requirements(job_title: str, description: str) -> Dict[str, Any]:
    """Extract job requirements using both LLM and local ontology."""
    # Use LLM to parse description for technologies and competencies (fallback to local only)
    llm_keys = []
    try:
        llm_profile = extract_skills_with_sealion(description, job_title)
        llm_skills = llm_profile.get('skills', {})
        llm_keys = [s.lower() for s in llm_skills.get('key_technologies', [])]
    except Exception:
        llm_keys = []

    # Use local miner to map title to ontology and expand synonyms
    local = mine_skills_locally(description, job_title)
    local_keys = [s.lower() for s in local.get('key_technologies', [])]

    # Merge + de-duplicate
    merged = sorted({*llm_keys, *local_keys})

    # Produce a compact requirement profile
    profile = JobRequirementProfile(
        job_title=job_title,
        description=description,
        required_skills=merged,
        key_technologies=merged[:20],
        criteria_weights=DEFAULT_CRITERIA_WEIGHTS,
        notes='Auto-generated from job description using SEA-LION + ontology'
    )

    return {
        'job_title': profile.job_title,
        'description': profile.description,
        'required_skills': profile.required_skills,
        'key_technologies': profile.key_technologies,
        'criteria_weights': profile.criteria_weights,
        'notes': profile.notes
    }
