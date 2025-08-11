import random
import re
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

# Roles aligned with Kaggle dataset categories (subset)
ROLES = [
    'Data Science','Python Developer','Data Analyst','Web Designing','Sales',
    'DevOps Engineer','Java Developer','Mechanical Engineer','HR','Testing',
    'Business Analyst','Operations Manager'
]

KM_UNIS = [
    'Royal University of Phnom Penh','Institute of Technology of Cambodia',
    'National University of Management','Cambodia Academy of Digital Technology',
    'CamTech University','Paññāsāstra University of Cambodia'
]

WEST_UNIS = [
    'Massachusetts Institute of Technology','Stanford University','University of Washington',
    'Harvard University','Carnegie Mellon University','University of Oxford'
]

SKILLS: Dict[str,List[str]] = {
    'Data Science': ['python','pandas','numpy','scikit-learn','tensorflow','pytorch','sql','data analysis'],
    'Python Developer': ['python','flask','django','docker','git','testing','rest','sql'],
    'Data Analyst': ['excel','sql','tableau','powerbi','statistics','visualization','communication'],
    'Web Designing': ['html','css','javascript','react','figma','responsive','accessibility'],
    'Sales': ['communication','negotiation','crm','excel','lead generation'],
    'DevOps Engineer': ['docker','kubernetes','linux','aws','terraform','ci/cd'],
    'Java Developer': ['java','spring','hibernate','rest','maven','junit'],
    'Mechanical Engineer': ['cad','autocad','solidworks','manufacturing','matlab'],
    'HR': ['recruiting','onboarding','hris','communication','payroll','compliance'],
    'Testing': ['selenium','pytest','automation','test cases','regression'],
    'Business Analyst': ['requirements','stakeholder','sql','viz','documentation'],
    'Operations Manager': ['process','kpi','scheduling','budget','excel']
}

UNDERSERVED = [
    'first-generation','refugee','immigrant','single-parent','rural','low-income',
    'underrepresented','underserved','orphan','scholarship','community leader',
    'cambodia','khmer','phnom penh','siem reap','battambang'
]

NAMES_KH = ['Sokha','Dara','Sreyneang','Heng','Sreyna','Sophea','Chanthy','Vannak']
NAMES_WEST = ['John','Mary','David','Susan','James','Emily','Michael','Sarah']


def sentence_case(s: str) -> str:
    return re.sub(r'(^|[\.!?]\s+)([a-z])', lambda m: m.group(1)+m.group(2).upper(), s)


def make_resume(role: str, locale: str) -> str:
    name = random.choice(NAMES_KH if locale == 'kh' else NAMES_WEST)
    uni = random.choice(KM_UNIS if locale == 'kh' else WEST_UNIS)
    years = random.randint(0, 10)
    base_skills = SKILLS.get(role, [])
    extra = random.sample(list(set(sum(SKILLS.values(), [])) - set(base_skills)), k=min(3, max(0, len(set(sum(SKILLS.values(), [])) - set(base_skills)))))
    skills = list(set(random.sample(base_skills, k=min(len(base_skills), random.randint(3, len(base_skills))))) | set(extra))
    community_flags = random.sample(UNDERSERVED, k=random.randint(0,2))
    txt = f"Name: {name}\nEducation: {uni}\nExperience: {years} years\nSkills: {', '.join(skills)}\nCommunity: {'; '.join(community_flags)}\n"
    return sentence_case(txt)


@dataclass
class GenConfig:
    n_per_role: int = 300
    locales: List[str] = None  # e.g., ['kh','west']


def generate_dataframe(cfg: GenConfig) -> pd.DataFrame:
    if cfg.locales is None:
        cfg.locales = ['kh','west']
    rows = []
    for role in ROLES:
        for _ in range(cfg.n_per_role):
            locale = random.choice(cfg.locales)
            txt = make_resume(role, locale)
            rows.append({'Category': role, 'Resume': txt})
    return pd.DataFrame(rows)
