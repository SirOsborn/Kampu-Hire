import os
import json
import re
import inspect
import pandas as pd
import numpy as np
import torch
import scipy.special
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import Labedef explain_model(model, tokenizer, X_val, output_dir):
    """Generate SHAP explanations for model predictions"""
    def predict_proba(texts):
        enc = tokenizer(
            list(texts),
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=MAX_LEN
        ).to(model.device)
        with torch.no_grad():
            out = model(**enc).logits
        return torch.softmax(out, dim=1).cpu().numpy()

    masker = shap.maskers.Text(tokenizer)
    explainer = shap.Explainer(predict_proba, masker)
    sample_texts = list(X_val[:10])
    shap_values = explainer(sample_texts)
    np.save(output_dir / 'shap_values.npy', shap_values.values)

def load_model_version(version=None):
    """Load a specific model version or the latest one"""
    if version is None:
        version = get_next_version() - 1
        if version < 1:
            raise FileNotFoundError("No model versions found")
    
    model_dir, _ = get_version_dirs(version)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model version {version} not found")
    
    # Load metadata
    with open(model_dir / 'metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # Load model components
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    label_encoder = np.load(model_dir / 'label_encoder.npy')
    
    return model, tokenizer, label_encoder, metadatap
from pathlib import Path
from nlpaug.augmenter.word import SynonymAug

# Configuration
MODEL_NAME = 'xlm-roberta-base'
MAX_LEN = 192
MODEL_BASE_DIR = Path('model')
MODEL_VERSIONS_DIR = MODEL_BASE_DIR / 'transformer_models'
RESULTS_BASE_DIR = MODEL_BASE_DIR / 'results'

# Define bias-prone features to exclude
DROP_COLS = [
    'name', 'gender', 'nationality', 'email', 'phone', 'address', 'age', 
    'date_of_birth', 'dob', 'university_name', 'school_name', 'college_name',
    'institution_name', 'location', 'marital_status', 'photo',
    'religion', 'race', 'ethnicity', 'social_media'
]

# Define skill-focused columns
SKILL_COLS = [
    'work_experience', 
    'project_details',
    'technical_skills',
    'achievements',
    'responsibilities',
    'problem_solving',
    'practical_experience',
    'portfolio_links',
    'github_projects',
    'certifications_with_projects',
    'soft_skills',
    'leadership_experience',
    'measurable_impacts',
    'tools_used',
    'methodologies'
]

def find_dataset():
    """Locate the dataset file"""
    candidates = [
        'datasets/Preprocessed_Data.csv',
        'datasets/synthetic_cvs.csv'
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError('No dataset found. Place Preprocessed_Data.csv in dataset/ or datasets/.')

def get_next_version():
    """Get the next available version number"""
    if not MODEL_VERSIONS_DIR.exists():
        return 1
        
    existing_versions = [
        int(d.name.split('v')[1]) 
        for d in MODEL_VERSIONS_DIR.glob('v*') 
        if d.is_dir() and d.name.startswith('v')
    ]
    return max(existing_versions, default=0) + 1

def get_version_dirs(version):
    """Get model and results directories for given version"""
    model_dir = MODEL_VERSIONS_DIR / f'v{version}'
    results_dir = RESULTS_BASE_DIR / f'v{version}'
    return model_dir, results_dir

def save_model_metadata(output_dir, version, config_data):
    """Save model metadata and configuration"""
    metadata = {
        'version': version,
        'model_name': MODEL_NAME,
        'max_length': MAX_LEN,
        'configuration': config_data,
        'skill_columns': SKILL_COLS,
        'dropped_columns': DROP_COLS
    }
    
    metadata_path = output_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def create_skill_based_label(text):
    """Generate labels based on practical skills and experience"""
    # Project experience indicators
    has_projects = bool(re.search(r'project|implemented|developed|built|created|designed', text, re.I))
    
    # Practical skills indicators
    practical_exp = bool(re.search(r'deployed|debugged|optimized|maintained|solved|improved', text, re.I))
    
    # Problem-solving indicators
    problem_solving = bool(re.search(r'resolved|automated|innovated|streamlined|enhanced', text, re.I))
    
    # Collaboration indicators
    team_work = bool(re.search(r'team|collaborated|coordinated|led|managed', text, re.I))
    
    # Calculate score based on practical indicators
    score = sum([has_projects, practical_exp, problem_solving, team_work])
    return int(score >= 2)  # Suitable if shows practical experience in at least 2 areas

def augment_underrepresented(texts, labels):
    """Balance dataset by augmenting underrepresented examples"""
    aug = SynonymAug()
    unique_labels, counts = np.unique(labels, return_counts=True)
    max_count = max(counts)
    
    augmented_texts = texts.copy()
    augmented_labels = labels.copy()
    
    for label in unique_labels:
        curr_count = (labels == label).sum()
        if curr_count < max_count:
            idx = np.where(labels == label)[0]
            n_aug = max_count - curr_count
            
            for i in range(n_aug):
                text = texts[idx[i % len(idx)]]
                aug_text = aug.augment(text)[0]
                augmented_texts = np.append(augmented_texts, aug_text)
                augmented_labels = np.append(augmented_labels, label)
    
    return augmented_texts, augmented_labels

class CVScreeningDataset(torch.utils.data.Dataset):
    """Custom Dataset for CV Screening"""
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = list(texts)
        self.labels = list(labels)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            padding='max_length',
            truncation=True,
            max_length=self.max_len,
            return_tensors='pt'
        )
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

def compute_metrics(eval_pred):
    """Calculate model performance metrics"""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    
    # Basic accuracy
    acc = (preds == labels).mean()
    
    # Confidence distribution
    probs = scipy.special.softmax(logits, axis=1)
    avg_confidence = probs.max(axis=1).mean()
    
    # Prediction stability
    stability = 1 - (np.abs(probs - 0.5) * 2).mean()
    
    # Fairness metrics
    demographic_parity = np.abs(probs.mean(axis=0).max() - probs.mean(axis=0).min())
    
    return {
        'accuracy': acc,
        'avg_confidence': float(avg_confidence),
        'stability': float(stability),
        'demographic_parity': float(demographic_parity)
    }

def main():
    # Load dataset
    data_path = find_dataset()
    df = pd.read_csv(data_path)
    
    # Preprocess data
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    
    # Determine or create labels
    label_candidates = ['label', 'target', 'hired', 'suitable', 'is_suitable', 'y']
    label_col = next((c for c in label_candidates if c in df.columns), None)
    
    if label_col is not None:
        y = df[label_col]
    else:
        # Create labels using skill-based heuristics
        available_cols = [c for c in SKILL_COLS if c in X.columns]
        if not available_cols:
            available_cols = [c for c in X.columns if X[c].dtype == 'object'][:5]
        
        tmp_text = X[available_cols].astype(str).fillna('').agg(' '.join, axis=1)
        y = tmp_text.apply(create_skill_based_label)

    # Prepare text data
    text_cols = [c for c in SKILL_COLS if c in X.columns]
    if not text_cols:
        text_cols = [c for c in X.columns if X[c].dtype == 'object']
    X_text = X[text_cols].astype(str).fillna('').agg(' '.join, axis=1)

    # Encode labels
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Split data
    X_train, X_val, y_train, y_val = train_test_split(
        X_text, y_enc, test_size=0.2, stratify=y_enc, random_state=42
    )

    # Data augmentation
    X_train_aug, y_train_aug = augment_underrepresented(X_train, y_train)

    # Initialize tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(le.classes_)
    ).to(device)

    # Enable memory optimizations
    if device == 'cuda':
        torch.set_float32_matmul_precision('high')
    try:
        model.gradient_checkpointing_enable()
    except Exception:
        pass

    # Create datasets
    train_ds = CVScreeningDataset(X_train_aug, y_train_aug, tokenizer, MAX_LEN)
    val_ds = CVScreeningDataset(X_val, y_val, tokenizer, MAX_LEN)

    # Get next version number and create directories
    version = get_next_version()
    model_dir, results_dir = get_version_dirs(version)
    model_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(results_dir),
        evaluation_strategy='epoch',
        save_strategy='epoch',
        learning_rate=1e-5,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        num_train_epochs=20,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model='eval_loss',
        save_total_limit=1,
        fp16=torch.cuda.is_available()
    )

    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics
    )

    # Train
    trainer.train()
    
    # Save model and tokenizer
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)
    
    # Save label encoder
    np.save(model_dir / 'label_encoder.npy', le.classes_)
    
    # Save training configuration
    config_data = {
        'training_args': training_args.to_dict(),
        'performance_metrics': trainer.state.best_metric,
        'num_labels': len(le.classes_),
        'device_used': device,
    }
    
    # Save metadata
    save_model_metadata(model_dir, version, config_data)
    
    # Generate SHAP explanations
    try:
        explain_model(model, tokenizer, X_val, model_dir)
    except Exception as e:
        with open(model_dir / 'shap_error.txt', 'w') as f:
            f.write(str(e))

    print(f'Training complete. Model v{version} saved to: {model_dir}')
    np.save(os.path.join(MODEL_OUT, 'label_encoder.npy'), le.classes_)

    # Generate SHAP explanations
    try:
        explain_model(model, tokenizer, X_val, MODEL_OUT)
    except Exception as e:
        with open(os.path.join(MODEL_OUT, 'shap_error.txt'), 'w') as f:
            f.write(str(e))

    print('Training complete. Model saved to:', MODEL_OUT)

def explain_model(model, tokenizer, X_val, output_dir):
    """Generate SHAP explanations for model predictions"""
    def predict_proba(texts):
        enc = tokenizer(
            list(texts),
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=MAX_LEN
        ).to(model.device)
        with torch.no_grad():
            out = model(**enc).logits
        return torch.softmax(out, dim=1).cpu().numpy()

    masker = shap.maskers.Text(tokenizer)
    explainer = shap.Explainer(predict_proba, masker)
    sample_texts = list(X_val[:10])
    shap_values = explainer(sample_texts)
    np.save(os.path.join(output_dir, 'shap_values.npy'), shap_values.values)

if __name__ == '__main__':
    main()