import re
from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
NAMES_DIR = DATA_DIR / 'names'

_NAME_CACHE: list[str] | None = None
_NAME_RE: re.Pattern | None = None


def _load_names_from_disk() -> list[str]:
    names: set[str] = set()
    if not NAMES_DIR.exists():
        return []
    for p in NAMES_DIR.glob('*.json'):
        try:
            arr = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(arr, list):
                for n in arr:
                    if isinstance(n, str) and n.strip():
                        names.add(n.strip())
        except Exception:
            continue
    return sorted(names)


def get_name_list() -> list[str]:
    global _NAME_CACHE
    if _NAME_CACHE is None:
        _NAME_CACHE = _load_names_from_disk()
    return _NAME_CACHE


def get_name_pattern() -> re.Pattern:
    global _NAME_RE
    if _NAME_RE is None:
        names = [re.escape(n) for n in get_name_list()]
        if names:
            _NAME_RE = re.compile(r"\b(" + "|".join(names) + r")\b", flags=re.IGNORECASE)
        else:
            _NAME_RE = re.compile(r"a^")  # never matches
    return _NAME_RE

def anonymize_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    t = text
    t = re.sub(r'(?i)name\s*[:\-].*?(\n|$)', ' ', t)
    t = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', ' ', t)
    t = re.sub(r'\b\+?\d[\d\s().-]{6,}\b', ' ', t)
    t = re.sub(r'(?i)education\s*[:\-].*?(\n|$)', ' ', t)
    pat = get_name_pattern()
    t = pat.sub(' name_token ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def load_role_keywords(role: str) -> list[str]:
    # Load presets from YAML, map best match by role name if available
    import yaml
    data_path = Path(__file__).resolve().parents[1]/'data'/'roles.yaml'
    if not data_path.exists():
        return []
    try:
        obj = yaml.safe_load(data_path.read_text(encoding='utf-8')) or {}
        # flatten sectors
        role_lower = role.lower()
        for sector, roles in obj.items():
            for rname, skills in (roles or {}).items():
                if rname.lower() == role_lower:
                    return list(skills)
        # fallback: partial contains
        for sector, roles in obj.items():
            for rname, skills in (roles or {}).items():
                if role_lower in rname.lower() or rname.lower() in role_lower:
                    return list(skills)
    except Exception:
        return []
    return []
