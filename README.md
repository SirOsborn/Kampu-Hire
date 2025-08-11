# Kampu‑Hire: Transparent, unbiased hiring model

Open-source base model for AI-powered resume screening that is transparent, auditable, and bias-aware.

What’s inside
- PyTorch model on simple BoW vectors for transparency
- Anonymization: removes names, emails, phones, and dampens prestige cues
- Exported vocab + labels for reproducible scoring

Project layout
- `dataset/UpdatedResumeDataSet.csv` — Kaggle dataset
- Web app in `app/` (LLM + transparent skills scoring)
	- `data/dataset.py` — anonymization + dataset + vectorizer
	- `models/mlp.py` — simple transparent multi layer perceptrons
	- `train/trainer.py` — training loop and artifact export
- `scripts/` — runners
	- `train_pytorch.py` — train and save artifacts
	- `score_pytorch.py` — score text or file with saved artifacts
- `artifacts/` — saved model.pt, vocab.json, labels.json (created after training)

Install
```powershell
python -m pip install -r requirements.txt
```

Train (PyTorch)
```powershell
# uses dataset/UpdatedResumeDataSet.csv
python ./scripts/train_pytorch.py
```

Score a resume (PyTorch)
```powershell
# from text
python ./scripts/score_pytorch.py --text "Python, pandas, ML, SQL..."

# from file
python ./scripts/score_pytorch.py --file c:/path/to/resume.txt
```

Audit fairness
```powershell
python ./src/audit_fairness.py
```

Artifacts
- `artifacts/model.pt`: trained PyTorch weights
- `artifacts/vocab.json`: Bag of words vocabulary mapping
- `artifacts/labels.json`: class index to name mapping

Integrations
- The old `kampu_hire` package is deprecated. Use `app/services` utilities.

Notes
- This is anti‑blackbox by design: linear model + explicit features + exported weights.
- Extend fairness with your own checks and ethically sourced annotations.
