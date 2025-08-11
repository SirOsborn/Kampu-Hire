from __future__ import annotations
import json
import requests
from typing import List, Dict, Optional
from app.core.config import settings

PROMPT_SYS = (
    "You are a fair hiring assistant. Score how well a resume fits a target position and skills."
    " Avoid bias: ignore names, gender, ethnicity, and schools unless directly relevant to skills."
    " Return JSON with fields: score (0..1), verdict ('hire'|'do_not_hire'), reasons (array)."
)


def build_prompt(position: str, keywords: List[str], resume_text: str, model_top: Optional[List[Dict]] = None) -> str:
    obj = {
        'position': position,
        'keywords': keywords,
        'model_top': model_top or [],
        'resume': resume_text[:12000],
    }
    return json.dumps(obj)


def call_llm(position: str, keywords: List[str], resume_text: str, model_top: Optional[List[Dict]] = None, timeout: float = 45.0) -> Dict:
    payload_user = build_prompt(position, keywords, resume_text, model_top)
    provider = (settings.LLM_PROVIDER or '').lower()
    # Auto-select provider if not explicitly configured
    if not provider:
        if settings.GEMINI_API_KEY:
            provider = 'gemini'
        elif settings.OPENAI_API_KEY:
            provider = 'openai'
        else:
            provider = 'ollama'

    try:
        if provider == 'openai':
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise RuntimeError('OPENAI_API_KEY not set')
            url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
            data = {
                'model': settings.OPENAI_MODEL,
                'temperature': 0,
                'response_format': {'type':'json_object'},
                'messages': [
                    {'role':'system','content':PROMPT_SYS},
                    {'role':'user','content':payload_user}
                ]
            }
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            r = requests.post(url, headers=headers, json=data, timeout=timeout)
            r.raise_for_status()
            content = r.json()['choices'][0]['message']['content']
            return json.loads(content)

        if provider == 'gemini':
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise RuntimeError('GEMINI_API_KEY not set')
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
            data = {
                'system_instruction': {'role': 'system', 'parts': [{'text': PROMPT_SYS}]},
                'contents': [{'role': 'user', 'parts': [{'text': payload_user}]}],
                'generationConfig': {'temperature': 0, 'response_mime_type': 'application/json'}
            }
            r = requests.post(url, json=data, timeout=timeout)
            r.raise_for_status()
            res = r.json()
            parts = res['candidates'][0]['content']['parts']
            txt = ''.join(p.get('text','') for p in parts)
            return json.loads(txt)

        if provider == 'ollama':
            url = f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat"
            data = {
                'model': settings.OLLAMA_MODEL,
                'stream': False,
                'options': {'temperature': 0},
                'messages': [
                    {'role':'system','content':PROMPT_SYS},
                    {'role':'user','content':payload_user}
                ]
            }
            r = requests.post(url, json=data, timeout=timeout)
            r.raise_for_status()
            msg = r.json().get('message', {}).get('content', '{}')
            try:
                return json.loads(msg)
            except Exception:
                import re
                m = re.findall(r'\{[\s\S]*\}', msg)
                if m:
                    return json.loads(m[-1])
                raise RuntimeError('LLM did not return JSON')

    except Exception as e:
        return {'score': 0.0, 'verdict': 'do_not_hire', 'reasons': [f'LLM error: {e}']}

    return {'score': 0.0, 'verdict': 'do_not_hire', 'reasons': ['LLM not configured: set LLM_PROVIDER or provide a valid API key in .env']}
