from __future__ import annotations
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.services.skills_scorer import transparent_score
from app.services.llm_scorer import call_llm
from app.services.text_utils import load_role_keywords
import io

router = APIRouter()


def clean_text(txt: str) -> str:
    if not txt:
        return ''
    txt = txt.replace('\r', '\n')
    import re
    txt = re.sub(r'(\w)-\n(\w)', r'\1\2', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()


def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == '.pdf':
        try:
            from pdfminer.high_level import extract_text
            return clean_text(extract_text(str(path)) or '')
        except Exception:
            try:
                import fitz
                doc = fitz.open(str(path))
                return clean_text('\n'.join(p.get_text('text') for p in doc))
            except Exception:
                return ''
    if ext == '.docx':
        try:
            import docx
            doc = docx.Document(str(path))
            return clean_text('\n'.join(p.text for p in doc.paragraphs))
        except Exception:
            return ''
    try:
        return clean_text(path.read_text(encoding='utf-8'))
    except Exception:
        return ''


@router.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return HTMLResponse((Path(__file__).resolve().parents[1]/'templates'/'index.html').read_text(encoding='utf-8'))


@router.post('/score', response_class=HTMLResponse)
async def score(request: Request,
                position: str = Form(...),
                keywords: str = Form(''),
                skill_only: bool = Form(False),
                file: UploadFile = File(...)):
    # Save upload to temp
    tmp = Path('uploads')
    tmp.mkdir(exist_ok=True)
    p = tmp / file.filename
    p.write_bytes(await file.read())

    raw = extract_text_from_file(p)
    # Multi-role support: allow multiple roles separated by newlines or semicolons
    roles = [r.strip() for r in position.replace(';', '\n').split('\n') if r.strip()]
    kw_groups = [g.strip() for g in keywords.split('\n') if g.strip()] if '\n' in keywords else [keywords]
    # if one keyword line, apply to all roles
    if len(kw_groups) == 1 and len(roles) > 1:
        kw_groups = kw_groups * len(roles)

    def combine_decision(model_ok: bool | None, llm_verdict: str, llm_score: float, coverage: float, fit: float) -> bool:
        llm_ok = (llm_verdict or '').lower().strip() == 'hire'
        # If no keyword signal, rely on LLM confidence
        if model_ok is None:
            return llm_score >= 0.55 and llm_ok
        # Agreement
        if model_ok and llm_ok:
            return True
        if (not model_ok) and (not llm_ok):
            return False
        # Disagreement: require strong evidence
        if llm_ok:
            return (llm_score >= 0.70 and coverage >= 0.45) or fit >= 0.65
        else:
            return not (coverage < 0.40 and llm_score < 0.55)

    results = []
    for i, role in enumerate(roles):
        kline = kw_groups[i] if i < len(kw_groups) else ''
        kw_list = [s.strip() for s in kline.replace(';', ',').split(',') if s.strip()]
        if not kw_list:
            kw_list = load_role_keywords(role)
        # Transparent scorer
        tscore = transparent_score(raw, role, kw_list, skill_only=skill_only)
        coverage = float(tscore['coverage'])
        # LLM scorer
        lout = call_llm(role, kw_list, raw, model_top=None)
        llm_score = float(lout.get('score', 0))
        # Auto fit (balanced blend) and model decision based on skill hits
        fit = 0.5 * coverage + 0.5 * llm_score
        skills_map = tscore.get('skills', {})
        kw_count = len(kw_list)
        hits = sum(1 for v in skills_map.values() if v > 0)
        model_required = None
        model_ok: bool | None
        if kw_count == 0:
            model_ok = None
        else:
            # Require at least 60% of skills or minimum of 2 for small lists
            import math
            model_required = max(2, math.ceil(0.6 * kw_count))
            model_ok = hits >= model_required
        final_ok = combine_decision(model_ok, lout.get('verdict', ''), llm_score, coverage, fit)
        decision = 'Hire' if final_ok else 'Do not hire'
        results.append({
            'role': role,
            'fit': fit,
            'decision': decision,
            'coverage': coverage,
            'llm': llm_score,
            'reasons': tscore['reasons'] + lout.get('reasons', [])[:5],
            'hits': hits,
            'kw_count': kw_count,
            'model_required': model_required,
            'llm_verdict': lout.get('verdict', '')
        })

    # Choose the single best role and render a single decision
    best = max(results, key=lambda r: r['fit']) if results else None
    detail = best or {'role': '', 'fit': 0, 'decision': 'Do not hire', 'coverage': 0, 'llm': 0, 'reasons': [], 'hits': 0, 'kw_count': 0, 'model_required': None}
    html = (Path(__file__).resolve().parents[1]/'templates'/'result.html').read_text(encoding='utf-8')
    html = html.replace('{{POSITION}}', detail['role'])
    html = html.replace('{{FIT}}', f"{detail['fit']:.3f}")
    html = html.replace('{{DECISION}}', detail['decision'])
    html = html.replace('{{REASONS}}', '<br>'.join(detail['reasons']))
    html = html.replace('{{COVERAGE}}', f"{detail['coverage']:.3f}")
    html = html.replace('{{LLM_SCORE}}', f"{detail['llm']:.3f}")
    html = html.replace('{{SKILL_HITS}}', f"{detail['hits']} / {detail['kw_count']}" if detail['kw_count'] else 'N/A')
    html = html.replace('{{MODEL_RULE}}', f">= {detail['model_required']} skills" if detail.get('model_required') else 'LLM-only (no skills provided)')
    return HTMLResponse(html)
