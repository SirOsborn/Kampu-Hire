from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import os

MODEL_DIR = "model/screening_model"

router = APIRouter(prefix="/api/screen", tags=["screening"])

tokenizer = None
model = None
label_classes = None
max_len = 192
DEVICE = None

class ScreenRequest(BaseModel):
    education: str | None = ""
    role: str | None = ""
    skills: str | None = ""
    languages: str | None = ""
    work_experience: str | None = ""
    certifications: str | None = ""
    summary: str | None = ""

class ScreenResponse(BaseModel):
    label: str
    confidence: float
    explanation: list[str]


def load_model():
    global tokenizer, model, label_classes, DEVICE
    if tokenizer is None or model is None:
        if not os.path.exists(MODEL_DIR):
            raise RuntimeError("Model directory not found. Train the model first.")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        # Ensure attentions work well with SDPA backends
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_DIR, attn_implementation="eager"
        )
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            model.to(DEVICE)
        except torch.cuda.OutOfMemoryError:
            DEVICE = "cpu"
            model.to(DEVICE)
        classes_path = os.path.join(MODEL_DIR, "label_encoder.npy")
        if os.path.exists(classes_path):
            label_classes = np.load(classes_path, allow_pickle=True)
        else:
            label_classes = np.array(["not_suitable", "suitable"], dtype=object)


def build_text(payload: ScreenRequest) -> str:
    parts = [
        payload.education or "",
        payload.role or "",
        payload.skills or "",
        payload.languages or "",
        payload.work_experience or "",
        payload.certifications or "",
        payload.summary or "",
    ]
    return " ".join([p.strip() for p in parts if p and p.strip()])


def top_tokens_explanation(text: str, k: int = 8) -> list[str]:
    """Attention-based quick explanation: top-k tokens most attended by CLS.
    Uses averaged attention across layers and heads. Lightweight and no gradients.
    """
    device = model.device
    encoding = tokenizer(text, return_tensors='pt', truncation=True, max_length=max_len)
    encoding = {kk: vv.to(device) for kk, vv in encoding.items()}
    with torch.no_grad():
        outputs = model(**encoding, output_attentions=True)
        attentions = outputs.attentions  # tuple of (layers) each: [bs, heads, seq, seq]
    if not attentions:
        return []
    attn = torch.stack(attentions)  # [layers, bs, heads, seq, seq]
    attn = attn.mean(dim=(0, 2))    # [bs, seq, seq]
    cls_idx = 0  # XLM-R uses <s> at position 0
    scores = attn[0, cls_idx]       # [seq]
    token_ids = encoding['input_ids'][0].tolist()
    tokens = tokenizer.convert_ids_to_tokens(token_ids)
    scores_list = scores.tolist()
    # Aggregate subword pieces into words (SentencePiece uses '▁' for word starts)
    word_scores = []
    cur_word = None
    cur_score = 0.0
    import re as _re
    # Patterns to redact PII and low-signal tokens
    _email_re = _re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    _url_re = _re.compile(r"https?://\S+|www\.\S+")
    _phone_re = _re.compile(r"(?:(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)[\s-]?)?\d{2,4}(?:[\s-]?\d){5,})")
    _digits_re = _re.compile(r"^\d{4,}$")
    def _is_pii(word: str) -> bool:
        if _email_re.search(word) or _url_re.search(word) or _phone_re.fullmatch(word):
            return True
        if _digits_re.match(word):
            return True
        if len(word) > 3 and word.isupper():  # likely names/acronyms in caps
            return True
        return False
    def _flush():
        nonlocal cur_word, cur_score
        if cur_word:
            w = cur_word.strip()
            w_clean = _re.sub(r"^[\W_]+|[\W_]+$", "", w)
            if (
                len(w_clean) >= 2
                and not _re.fullmatch(r"[\W_]+", w_clean)
                and not _is_pii(w_clean)
            ):
                word_scores.append((w_clean, float(cur_score)))
        cur_word, cur_score = None, 0.0
    for tok, sc in zip(tokens, scores_list):
        if tok in ('<s>', '</s>', '<pad>'):
            continue
        is_start = tok.startswith('▁')
        piece = tok[1:] if is_start else tok
        if is_start:
            _flush()
            cur_word = piece
            cur_score = sc
        else:
            if cur_word is None:
                cur_word = piece
                cur_score = sc
            else:
                cur_word += piece
                cur_score += sc
    _flush()
    # Rank by score and return top-k unique words
    word_scores.sort(key=lambda x: x[1], reverse=True)
    seen = set()
    top = []
    for w, _s in word_scores:
        wl = w.lower()
        if wl in seen:
            continue
        seen.add(wl)
        top.append(w)
        if len(top) >= k:
            break
    return top

def _normalize_label_from_classes(pred_idx: int) -> str:
    vals = list(label_classes) if label_classes is not None else None
    if not vals:
        return 'suitable' if pred_idx == 1 else 'not_suitable'
    try:
        # If classes are numeric like [0,1]
        as_ints = [int(x) for x in vals]
        if len(as_ints) == 2 and set(as_ints) == {0, 1}:
            return 'suitable' if int(as_ints[pred_idx]) == 1 else 'not_suitable'
    except Exception:
        pass
    # Otherwise, return the class string
    return str(vals[pred_idx])


def warmup_model():
    """Preload tokenizer/model and run a tiny forward pass to reduce first-request latency."""
    try:
        load_model()
        sample = (
            "Warmup resume: Experienced teacher skilled in English literacy, lesson planning, and classroom management."
        )
        device = model.device
        enc = tokenizer(sample, return_tensors='pt', truncation=True, max_length=min(64, max_len))
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            _ = model(**enc, output_attentions=True)
    except Exception as e:
        print(f"[screening] warmup skipped: {e}")


@router.post("/", response_model=ScreenResponse)
def screen_cv(payload: ScreenRequest):
    try:
        load_model()
        text = build_text(payload)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty content to screen.")
        device = model.device
        enc = tokenizer(text, return_tensors='pt', truncation=True, max_length=max_len)
        try:
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.no_grad():
                logits = model(**enc).logits
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        except torch.cuda.OutOfMemoryError:
            # Fallback to CPU inference
            model.to('cpu')
            enc = {k: v.to('cpu') for k, v in enc.items()}
            with torch.no_grad():
                logits = model(**enc).logits
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        pred_idx = int(np.argmax(probs))
        label = _normalize_label_from_classes(pred_idx)
        confidence = float(probs[pred_idx])
        try:
            explanation = top_tokens_explanation(text)
        except Exception:
            explanation = []
        return ScreenResponse(label=label, confidence=confidence, explanation=explanation)
    except HTTPException:
        raise
    except Exception as e:
        # Minimal logging for debugging
        print(f"[screening] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
