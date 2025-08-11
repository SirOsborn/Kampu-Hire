## Kampu‑Hire — Skills‑first, transparent resume screening (Web app)

Kampu‑Hire is a FastAPI web app that blends an explainable, skills‑first scorer with an LLM judge to produce one unbiased decision: Hire or Do not hire. Resumes are anonymized (names/emails/phones stripped) to reduce bias.

What you get
- Single combined decision: transparent skills coverage + LLM verdict, with clear signals.
- Multi‑sector role presets: auto‑fill skills for common roles across industries.
- Strong anonymization: configurable name lists per region/gender loaded from data files.

Project layout
- app/
	- main.py — FastAPI entry
	- routers/web.py — UI and scoring route (file upload; combined decision)
	- services/
		- skills_scorer.py — explainable, section‑aware keyword coverage
		- llm_scorer.py — calls Gemini/OpenAI/Ollama with bias guardrails
		- text_utils.py — anonymization + role presets + names loader
	- templates/ — index.html (form), result.html (decision page)
	- data/
		- roles.yaml — role presets per sector (editable)
		- names/ — JSON files with names per region/gender (you add 200+ lists here)

Setup
1) Install dependencies
```powershell
python -m pip install -r requirements.txt
```

2) Configure environment (.env at repo root)
- LLM_PROVIDER=openai | gemini | ollama (optional; auto‑detects by available keys)
- OPENAI_API_KEY=... (for OpenAI‑compatible)
- OPENAI_BASE_URL=https://api.openai.com/v1 (or compatible endpoint)
- OPENAI_MODEL=gpt-4o-mini (or your model)
- GEMINI_API_KEY=... (for Google Generative Language)
- GEMINI_MODEL=gemini-1.5-flash
- OLLAMA_HOST=http://localhost:11434
- OLLAMA_MODEL=llama3.1:8b

3) Add names (optional but recommended)
- Put JSON arrays of names into app/data/names (e.g., khmer_male.json, khmer_female.json, vietnam_male.json, etc.).
- The anonymizer loads every *.json and masks matches as name_token.
- See app/data/names/README.txt for examples.

Run the app
```powershell
python -m uvicorn app.main:app --reload --port 8000
```
Open http://127.0.0.1:8000 and upload a resume (PDF/DOCX/TXT). Provide a role and optional skills. If skills are left blank, role presets from app/data/roles.yaml will be used.

How scoring works
- Transparent scorer: section‑aware, phrase‑tolerant keyword matching. Produces coverage (0..1) and reasons (matched/missing).
- LLM scorer: prompts a model to return JSON {score (0..1), verdict (hire|do_not_hire), reasons} with bias guardrails.
- Combined decision: we merge skill hits and the LLM verdict to output a single Hire/Do not hire with signals displayed.

Customize roles and skills
- Edit app/data/roles.yaml to add your sectors/roles/skills.
- If keywords are blank, the app auto‑loads skills from this file for the role name you enter.

Bias reduction
- Anonymize: remove names, emails, phones, and de‑emphasize education signals.
- Skills‑only toggle: further reduces weight of non‑skill sections.
- Regional names: load 200+ names per gender per region (Khmer, neighboring ASEAN, Japanese, Chinese, Korean, Western) into app/data/names for robust masking.

Troubleshooting
- If PDF text is empty, try a different extractor (PyMuPDF is a fallback). For scanned PDFs, enable OCR deps in requirements.txt and add Tesseract on your OS.
- If no LLM keys are set, the app attempts local Ollama. Configure .env to use your provider.

License
Open‑source. Use responsibly and ensure hiring decisions comply with local laws and ethical standards.
