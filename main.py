import os
import tempfile
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai
from pydub import AudioSegment
# Load API keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Init clients
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-pro")

# FastAPI init
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "transcript": None, "summary": None})

from pydub import AudioSegment

@app.post("/process", response_class=HTMLResponse)
async def process_audio(request: Request, file: UploadFile):
    transcript_text = ""
    summary_text = ""

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # --- Convert to WAV if needed ---
        if not temp_path.endswith(".wav"):
            sound = AudioSegment.from_file(temp_path)
            wav_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            sound.export(wav_temp.name, format="wav")
            temp_path = wav_temp.name  # Update path to WAV

        # 1️⃣ Transcribe with Whisper (Groq)
        with open(temp_path, "rb") as f:
            transcription = groq_client.audio.transcriptions.create(
                file=(f.name, f.read()),
                model="whisper-large-v3"
            )
        transcript_text = transcription.text

        # 2️⃣ Summarize with Gemini
        prompt = f"""
        You are a professional meeting assistant.
        Summarize this transcript into:
        -  Key Decisions
        -  Action Items
        -  Discussion Points

        Transcript:
        {transcript_text}
        """

        response = gemini_model.generate_content(prompt)
        summary_text = response.text

    except Exception as e:
        summary_text = f"❌ Error: {str(e)}"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "transcript": transcript_text,
        "summary": summary_text
    })
