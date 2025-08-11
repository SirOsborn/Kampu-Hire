from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from app.services.text_utils import anonymize_text

# Transparent skills scorer: counts skills occurrences with boosts; ignores prestige signals by design.
DEFAULT_ALIASES = {
    # Tools
    "ps": ["photoshop", "adobe photoshop"],
    "ai": ["illustrator", "adobe illustrator"],
    "pr": ["premiere", "adobe premiere"],
    "ae": ["after effects", "adobe after effects"],
    # General
    "js": ["javascript"],
    "ts": ["typescript"],
    # Teaching / Education synonyms
    "teacher": ["teaching", "instructor", "lecturer", "tutor"],
    "english": ["esl", "efl", "elt", "eap", "english language"],
    "lesson planning": ["lesson plan", "lesson plans", "planning lessons"],
    "classroom management": ["class management", "behaviour management", "behavior management", "classroom discipline"],
    "curriculum development": ["curriculum design", "syllabus design", "course design", "curriculum planning"],
    "assessment": ["evaluation", "testing", "examination", "grading"],
    "reading": ["reading comprehension"],
    "writing": ["writing skills"],
}

SECTION_HEADS = {
    'skills': re.compile(r'^(skills|technical skills)\b', re.I),
    'experience': re.compile(r'^(experience|work experience|professional experience)\b', re.I),
    'projects': re.compile(r'^(projects?)\b', re.I),
    'summary': re.compile(r'^(summary|profile|objective)\b', re.I),
    'education': re.compile(r'^(education|educational background)\b', re.I),
}

SECTION_WEIGHTS = {
    'skills': 2.0,
    'experience': 1.5,
    'projects': 1.2,
    'summary': 1.0,
    'education': 0.0,  # de-emphasize education by default (skills-first)
    'other': 1.0,
}


def split_sections(text: str):
    lines = [ln.strip() for ln in text.split('\n')]
    sections: List[Tuple[str, str]] = []
    name = 'other'
    buf: List[str] = []
    def push():
        if buf:
            sections.append((name, '\n'.join(buf)))
    for ln in lines:
        matched = None
        for key, pat in SECTION_HEADS.items():
            if pat.match(ln):
                matched = key
                break
        if matched:
            push(); name = matched; buf = []
        else:
            buf.append(ln)
    push()
    return sections if sections else [('other', text)]


def tokenize(txt: str) -> List[str]:
    return re.findall(r'\b\w+\b', txt.lower())


def simple_stem(token: str) -> str:
    t = token.lower()
    for suf in ('ing', 'ers', 'er', 'ed', 's'):
        if len(t) > 4 and t.endswith(suf):
            return t[:-len(suf)]
    return t


def extract_skills(text: str, keywords: List[str], aliases: Dict[str, List[str]] | None = None, section_weights: Dict[str, float] | None = None) -> Dict[str, float]:
    # returns {keyword: weighted_presence in [0..1]}
    aliases = aliases or {}
    sections = split_sections(text)

    # Precompute per-section lowercase text and stemmed token sets
    import re as _re
    sec_data = []
    for name, sec_txt in sections:
        sec_lower = sec_txt.lower()
        # normalize hyphen/underscore/slash sequences to spaces for phrase matching leniency
        sec_norm = _re.sub(r"[-_/]+", " ", sec_lower)
        stoks = set(simple_stem(t) for t in tokenize(sec_txt))
        sec_data.append((name, sec_txt, sec_norm, stoks))

    def phrase_match(phrase: str, sec_norm: str) -> bool:
        parts = _re.findall(r"\w+", phrase.lower())
        if not parts:
            return False
        pat = r"\b" + r"[-_\./,\s]+".join(_re.escape(p) for p in parts) + r"\b"
        return _re.search(pat, sec_norm) is not None

    weights = section_weights or SECTION_WEIGHTS
    max_w = max(weights.values()) if weights else 1.0
    out: Dict[str, float] = {}
    for kw in keywords:
        base = kw.strip()
        if not base:
            out[kw] = 0.0
            continue
        cands = [base] + aliases.get(base.lower(), [])
        best = 0.0
        for sec_name, _sec_txt, sec_norm, stoks in sec_data:
            for cand in cands:
                if ' ' in cand.strip():
                    if phrase_match(cand, sec_norm):
                        best = max(best, weights.get(sec_name, 1.0))
                else:
                    stem = simple_stem(cand)
                    if stem in stoks or any(tok.startswith(stem) for tok in stoks if len(stem) >= 3):
                        best = max(best, weights.get(sec_name, 1.0))
        out[kw] = best / max_w if max_w else 0.0
    return out


def transparent_score(text: str, position: str, keywords: List[str], *, skill_only: bool = False, section_weights: Dict[str, float] | None = None) -> Dict:
    # anonymize first to remove sensitive signals
    text = anonymize_text(text)
    sw = dict(SECTION_WEIGHTS)
    if skill_only:
        sw['education'] = 0.0
        sw['summary'] = min(sw['summary'], 0.8)
    if section_weights:
        sw.update(section_weights)
    skills = extract_skills(text, keywords, aliases=DEFAULT_ALIASES, section_weights=sw)
    coverage = sum(skills.values()) / max(len(keywords), 1)
    reasons = []
    present = [k for k, v in skills.items() if v > 0]
    missing = [k for k, v in skills.items() if v == 0]
    if present:
        reasons.append(f"Matched: {', '.join(present)}")
    if missing:
        reasons.append(f"Missing: {', '.join(missing)}")
    return {
        'position': position,
        'coverage': coverage,
        'skills': skills,
        'reasons': reasons,
    }
