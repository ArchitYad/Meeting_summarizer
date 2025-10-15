import os
import tempfile
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai
import imageio_ffmpeg as ffmpeg
from pydub import AudioSegment

# Force pydub to use ffmpeg from imageio-ffmpeg
AudioSegment.converter = ffmpeg.get_ffmpeg_exe()

# Load API keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "transcript": None, "summary": None}
    )


@app.post("/process", response_class=HTMLResponse)
async def process_audio(request: Request, file: UploadFile):
    transcript_text = ""
    summary_text = ""

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # Convert to WAV if needed
        if not temp_path.endswith(".wav"):
            sound = AudioSegment.from_file(temp_path)
            wav_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            sound.export(wav_temp.name, format="wav")
            os.remove(temp_path)  # Delete original temp file
            temp_path = wav_temp.name

        # --- Split audio into chunks (2 minutes each) ---
        audio = AudioSegment.from_wav(temp_path)
        chunk_length_ms = 2 * 60 * 1000  # 2 minutes
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

        # Transcribe each chunk
        transcripts = []
        for idx, chunk in enumerate(chunks):
            chunk_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            chunk.export(chunk_file.name, format="wav")
            try:
                with open(chunk_file.name, "rb") as f:
                    transcription = groq_client.audio.transcriptions.create(
                        file=(f.name, f.read()),
                        model="whisper-large-v3"
                    )
                transcripts.append(transcription.text)
            finally:
                os.remove(chunk_file.name)  # Delete chunk temp file after processing

        # Aggregate full transcript
        transcript_text = "\n".join(transcripts)

        # Summarize aggregated transcript
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

        # Delete main temp WAV file
        os.remove(temp_path)

    except Exception as e:
        summary_text = f"❌ Error: {str(e)}"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "transcript": transcript_text, "summary": summary_text}
    )
