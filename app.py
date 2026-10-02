"""MisconceptionMap - finds WHERE and WHY a student's handwritten reasoning broke."""
import base64, json, os, re, sqlite3, time
from collections import Counter

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
DB = os.getenv("DB_PATH", "misconceptions.db")
LANGS = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "bn": "Bengali", "mr": "Marathi"}

PROMPT = """You are a patient teacher marking a student's handwritten solution (photo attached).
The student may also have explained their thinking aloud (transcript below).
1. Transcribe the work into numbered steps; ignore crossed-out text unless it shows reasoning.
2. Check each step. Find the FIRST step that is wrong (or null if all correct).
3. Name the underlying misconception as a short kebab-case tag (e.g. "sign-error-when-moving-terms").
4. Do NOT just give the final answer. Give a hint that lets the student find the error.
Write 'spoken_feedback' (max 3 sentences, warm, simple) in {language}.
Return ONLY JSON with keys:
subject, problem, steps:[{n:int,text:str,correct:bool}], first_error_step:int|null,
misconception_tag:str|null, misconception_explanation:str, hint:str,
practice_question:str, spoken_feedback:str, legible:bool, confidence:number(0-1)
Student transcript: {transcript}"""

DEMO = {
    "subject": "Maths", "problem": "Solve x^2 - 5x + 6 = 0",
    "steps": [{"n": 1, "text": "x^2 - 5x + 6 = 0", "correct": True},
              {"n": 2, "text": "(x - 2)(x - 3) = 0", "correct": True},
              {"n": 3, "text": "x = -2 or x = -3", "correct": False}],
    "first_error_step": 3, "misconception_tag": "sign-flip-when-reading-factors",
    "misconception_explanation": "The factors are correct, but the roots were read off with the signs of the factors instead of setting each factor to zero.",
    "hint": "Set (x - 2) = 0 on its own. What number makes that true?",
    "practice_question": "Solve x^2 - 7x + 12 = 0 and check both roots by substituting.",
    "spoken_feedback": "Great factoring in step 2! Look at step 3 again: if x - 2 equals zero, what must x be?",
    "legible": True, "confidence": 0.9, "demo": True,
}

app = FastAPI(title="MisconceptionMap")


def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, ts REAL, subject TEXT, tag TEXT, step INT)")
    return c


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("model returned no JSON")
    return json.loads(m.group(0))


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...), language: str = Form("en"), transcript: str = Form("")):
    data = await image.read()
    if not data or len(data) > 8_000_000:
        raise HTTPException(400, "Upload a photo under 8 MB.")
    if not KEY:
        result = dict(DEMO)
    else:
        import anthropic
        mt = image.content_type if image.content_type in ("image/jpeg", "image/png", "image/webp") else "image/jpeg"
        client = anthropic.Anthropic(api_key=KEY)
        prompt = PROMPT.replace("{language}", LANGS.get(language, "English")).replace("{transcript}", transcript or "(none)")
        try:
            msg = client.messages.create(model=MODEL, max_tokens=1500, messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(data).decode()}},
                {"type": "text", "text": prompt}]}])
            result = parse_json(msg.content[0].text)
        except Exception as e:
            raise HTTPException(502, f"Analysis failed: {e}")
    if result.get("misconception_tag"):
        with db() as c:
            c.execute("INSERT INTO logs(ts,subject,tag,step) VALUES(?,?,?,?)",
                      (time.time(), result.get("subject", "?"), result["misconception_tag"], result.get("first_error_step")))
    return result


@app.get("/api/dashboard")
def dashboard():
    with db() as c:
        rows = c.execute("SELECT subject, tag FROM logs").fetchall()
    total = len(rows)
    tags = Counter(t for _, t in rows)
    return {"total": total, "top": [{"tag": t, "count": n, "pct": round(100 * n / total)} for t, n in tags.most_common(8)]}


@app.post("/api/demo-seed")
def seed():
    """Fill the teacher dashboard with sample class data for demos."""
    sample = [("sign-flip-when-reading-factors", 9), ("forgot-to-distribute-negative", 6),
              ("unit-conversion-skipped", 4), ("mixed-up-mass-and-weight", 3)]
    with db() as c:
        for tag, n in sample:
            c.executemany("INSERT INTO logs(ts,subject,tag,step) VALUES(?,?,?,?)", [(time.time(), "Maths", tag, 2)] * n)
    return {"seeded": sum(n for _, n in sample)}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
