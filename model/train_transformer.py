"""
Train a fair, explainable CV screening model using XLM-RoBERTa and SHAP.
- Excludes bias-prone features (name, gender, nationality)
- Fine-tunes transformer on job-relevant fields
- Saves model and tokenizer for inference
"""
import os
import json
import re
import inspect
import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import shap


MODEL_NAME = 'xlm-roberta-base'
# Prefer the user's provided Preprocessed_Data.csv; fallback to common paths
_candidates = [
    'datasets/Preprocessed_Data.csv',
    'datasets/synthetic_cvs.csv'
]
DATA_PATH = None
for p in _candidates:
    if os.path.exists(p):
        DATA_PATH = p
        break
if DATA_PATH is None:
    raise FileNotFoundError('No dataset found. Place Preprocessed_Data.csv in dataset/ or datasets/.')
MODEL_OUT = 'model/screening_model'
MAX_LEN = 192  # shorter seq length to reduce GPU memory

# 1. Load and preprocess data
df = pd.read_csv(DATA_PATH)

# Exclude bias-prone features
drop_cols = ['name', 'gender', 'nationality', 'email', 'phone', 'address', 'age', 'date_of_birth', 'dob']
X = df.drop(columns=[c for c in drop_cols if c in df.columns])

# For demo: create a binary label (suitable/not suitable) if not present
# Determine label column if present; otherwise, create a weak heuristic label safely
label_candidates = ['label', 'target', 'hired', 'suitable', 'is_suitable', 'y']
label_col = next((c for c in label_candidates if c in df.columns), None)
if label_col is not None:
    y = df[label_col]
else:
    # Generic heuristic on combined text: years of experience and key skills
    # Build a temporary text field using available columns first
    pref_fields = [
        'summary', 'experience', 'work_experience', 'work history', 'employment',
        'skills', 'education', 'role', 'certifications', 'languages', 'projects', 'achievements', 'objective'
    ]
    available = [c for c in pref_fields if c in X.columns]
    if not available:
        # If nothing matches, just use the first text-like columns
        available = [c for c in X.columns if X[c].dtype == 'object'][:5]
    tmp_text = X[available].astype(str).fillna('').agg(' '.join, axis=1)
    years = tmp_text.str.extract(r'(\d+)\s*(?:\+?\s*)?(?:years?|yrs?)', flags=re.IGNORECASE)[0]
    years = pd.to_numeric(years, errors='coerce').fillna(0)
    has_keywords = tmp_text.str.contains(r'Python|Project Management|Data|Engineer|Leadership|ML|AI', case=False, na=False)
    y = ((years > 5) & has_keywords).astype(int)

# Concatenate job-relevant fields into a single text (select only columns that exist)
preferred_cols = ['summary', 'experience', 'work_experience', 'skills', 'education', 'role', 'languages', 'certifications', 'projects', 'achievements', 'responsibilities', 'objective']
text_cols = [c for c in preferred_cols if c in X.columns]
if not text_cols:
    # Fallback to any text columns
    text_cols = [c for c in X.columns if X[c].dtype == 'object']
if not text_cols:
    raise ValueError('No suitable text columns found to train the model.')
X_text = X[text_cols].astype(str).fillna('').agg(' '.join, axis=1)

# Encode labels
le = LabelEncoder()
y_enc = le.fit_transform(y)

# Train/val split
X_train, X_val, y_train, y_val = train_test_split(X_text, y_enc, test_size=0.2, stratify=y_enc, random_state=42)

# Tokenization
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(batch):
    return tokenizer(batch, padding='max_length', truncation=True, max_length=MAX_LEN)

class CVScreeningDataset(torch.utils.data.Dataset):
    def __init__(self, texts, labels):
        self.texts = list(texts)
        self.labels = list(labels)
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, idx):
        enc = tokenizer(self.texts[idx], padding='max_length', truncation=True, max_length=MAX_LEN, return_tensors='pt')
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

train_ds = CVScreeningDataset(X_train, y_train)
val_ds = CVScreeningDataset(X_val, y_val)

# Model
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}; cuda_available={torch.cuda.is_available()}")
if device == 'cuda':
    try:
        torch.set_float32_matmul_precision('high')
    except Exception:
        pass
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(le.classes_)).to(device)
# Enable gradient checkpointing to save memory if supported
try:
    model.gradient_checkpointing_enable()
except Exception:
    pass

# Training
# Build TrainingArguments kwargs and filter to those supported by the installed version
train_args_kwargs = {
    'output_dir': './results',
    'evaluation_strategy': 'epoch',
    'save_strategy': 'epoch',
    'learning_rate': 2e-5,
    'per_device_train_batch_size': 4,
    'per_device_eval_batch_size': 4,
    'num_train_epochs': 2,
    'weight_decay': 0.01,
    'load_best_model_at_end': True,
    'metric_for_best_model': 'eval_loss',
    'save_total_limit': 1,
}
# Enable mixed precision on CUDA if supported
if torch.cuda.is_available():
    if 'fp16' in inspect.signature(TrainingArguments.__init__).parameters:
        train_args_kwargs['fp16'] = True
    elif 'bf16' in inspect.signature(TrainingArguments.__init__).parameters and torch.cuda.is_available():
        train_args_kwargs['bf16'] = True
supported_params = set(inspect.signature(TrainingArguments.__init__).parameters.keys())
filtered_kwargs = {k: v for k, v in train_args_kwargs.items() if k in supported_params}

# If evaluation_strategy isn't supported, disable features that depend on it
if 'evaluation_strategy' not in supported_params:
    filtered_kwargs.pop('save_strategy', None)
    filtered_kwargs.pop('metric_for_best_model', None)
    if 'load_best_model_at_end' in supported_params:
        filtered_kwargs['load_best_model_at_end'] = False
    # Some older versions use do_eval flag
    if 'do_eval' in supported_params:
        filtered_kwargs['do_eval'] = True

args = TrainingArguments(**filtered_kwargs)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    acc = (preds == labels).mean()
    return {'accuracy': acc}

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
)

trainer.train()

# Save model and tokenizer
os.makedirs(MODEL_OUT, exist_ok=True)
model.save_pretrained(MODEL_OUT)
tokenizer.save_pretrained(MODEL_OUT)
le_path = os.path.join(MODEL_OUT, 'label_encoder.npy')
np.save(le_path, le.classes_)

# Save basic metrics on the validation set
model.eval()
with torch.no_grad():
    val_texts = list(X_val)
    labels_np = np.array(y_val)
    preds_all = []
    bs = 16 if torch.cuda.is_available() else 32
    for i in range(0, len(val_texts), bs):
        chunk = val_texts[i:i+bs]
        enc = tokenizer(chunk, return_tensors='pt', padding=True, truncation=True, max_length=MAX_LEN)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        logits = model(**enc).logits
        preds = logits.argmax(dim=1).cpu().numpy().tolist()
        preds_all.extend(preds)
        del enc, logits
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    preds_all = np.array(preds_all[:len(labels_np)])
    acc = float((preds_all == labels_np).mean())
    metrics = {'accuracy': acc, 'num_val_samples': int(len(labels_np)), 'data_path': DATA_PATH, 'text_columns': text_cols, 'max_len': MAX_LEN}
    with open(os.path.join(MODEL_OUT, 'metrics.json'), 'w', encoding='utf-8') as mf:
        json.dump(metrics, mf, ensure_ascii=False, indent=2)

# SHAP explainability (fit on a small sample; safe wrapper)
try:
    import re
    from shap.maskers import Text as TextMasker

    def predict_proba(texts):
        enc = tokenizer(list(texts), return_tensors='pt', padding=True, truncation=True, max_length=MAX_LEN).to(model.device)
        with torch.no_grad():
            out = model(**enc).logits
        return torch.softmax(out, dim=1).cpu().numpy()

    masker = TextMasker(tokenizer)
    explainer = shap.Explainer(predict_proba, masker)
    sample_texts = list(X_val[:10])
    shap_values = explainer(sample_texts)
    shap_path = os.path.join(MODEL_OUT, 'shap_values.npy')
    np.save(shap_path, shap_values.values)
except Exception as e:
    with open(os.path.join(MODEL_OUT, 'shap_error.txt'), 'w', encoding='utf-8') as ef:
        ef.write(str(e))

print('Training complete. Artifacts saved to', MODEL_OUT)
