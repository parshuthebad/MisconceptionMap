# MisconceptionMap

**Students don't need answers - they need to know *why* they're wrong.**

Photograph handwritten work (maths, physics, chemistry), optionally explain your thinking by voice, and a multimodal model:
1. reads the handwriting and crossed-out attempts (vision),
2. finds the **first step where reasoning breaks**,
3. names the **underlying misconception**,
4. gives a hint (not the answer), a practice question, and spoken feedback in Hindi, Telugu, Tamil, Bengali, Marathi or English.

Teachers get a **class misconception heatmap** so they know what to re-teach tomorrow.

Built for the Multimodal AI Hackathon 2026 (Education track).

## Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY (leave empty for demo mode)
uvicorn app:app --reload
```
Open http://localhost:8000. With no API key it runs in **demo mode** using a canned analysis.

## Architecture
`static/index.html` (camera, mic, TTS, teacher view) -> `POST /api/analyze` (FastAPI) -> vision LLM returns structured JSON -> SQLite log -> `GET /api/dashboard`.

## Evaluation
Add 30-50 labelled photos to `eval/samples/`, fill `eval/labels.csv`, run `python eval/run_eval.py` to report first-error-step accuracy.

## Limitations
Very messy handwriting, ambiguous errors, and multiple valid solution paths can reduce accuracy; the app flags low legibility. Speech recognition depends on browser support (Chrome works best).
