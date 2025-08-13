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

### To run the web app
```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Integrations
- The old `kampu_hire` package is deprecated. Use `app/services` utilities.

Notes
- This is anti‑blackbox by design: linear model + explicit features + exported weights.
- Extend fairness with your own checks and ethically sourced annotations.
