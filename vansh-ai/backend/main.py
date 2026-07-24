"""
Vansh AI — Backend
=====================
The "AI Brain" for the human-avatar assistant, built by Vansh Sharma.

Endpoints
---------
GET  /api/health            -> liveness check
POST /api/chat               -> {message, session_id, language} -> {reply, emotion, language}
POST /api/speak               -> {text} -> audio/mpeg bytes (ElevenLabs) OR 204 if no key set
                                  (frontend falls back to free browser TTS on 204)
POST /api/upload               -> multipart file (.txt/.pdf) -> indexes it for RAG
GET  /api/knowledge            -> lists what's currently indexed for RAG
POST /api/knowledge/clear      -> wipes the RAG index

Run:
    uvicorn main:app --reload --port 8000
"""

import math
import os
import re
import time
import uuid
from collections import Counter
from typing import Optional

import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from rag_utils import chunk_text, extract_text_from_upload

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # "Rachel" default
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
        "and add your free key from https://aistudio.google.com/apikey"
    )

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Vansh AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before deploying past localhost
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# In-memory state (swap for Redis/Postgres before production — see README)
# --------------------------------------------------------------------------

SESSIONS: dict[str, list[dict]] = {}        # session_id -> [{role, content}, ...]
RAG_CHUNKS: list[str] = []                  # flat store of indexed text chunks
RAG_SOURCES: list[str] = []                 # filename each chunk came from
MAX_TURNS_KEPT = 16                         # rolling memory window per session

EMOTION_TAG_RE = re.compile(r"@@EMOTION:(\w+)@@\s*$")
VALID_EMOTIONS = {"happy", "neutral", "concerned", "excited", "empathetic", "serious", "encouraging"}

SYSTEM_PROMPT = """You are Vansh AI, a warm, encouraging AI companion built by Vansh Sharma. You \
speak naturally and conversationally, like a close human friend — not a formal assistant or a \
document.

Rules:
1. LANGUAGE: Reply in the exact same language as the student's CURRENT message — judged only by
that message, not by earlier turns in this conversation. If they write in plain English, reply in
plain English only — do NOT slip into Hindi or Hinglish words. If they write in Hindi (Devanagari)
or Hinglish (Romanized Hindi/Hindi-English mix), reply in that same style. The language can change
turn to turn — always follow the latest message, never assume from history or from the student's
apparent background.
2. HUMAN WARMTH: When the student greets you or makes casual small talk (e.g. "kya chal raha hai",
"kaise ho", "what's up", "long time no see"), respond exactly like a close human friend catching up
— not like an assistant. React naturally and warmly first (e.g. "bas badhiya chal raha hai yaar,
bahut din baad yaad kiya!"), then ask something back about them — how they're doing, what's going
on, how their family/studies/work is — the way real friends check in on each other. Do NOT jump
straight into offering help or asking "how can I assist you" unless they've actually asked for
something specific. Save the assistant tone for when they ask a real question.
3. LENGTH: Keep spoken-aloud responses concise (2-5 sentences) unless the student is asking for \
a detailed explanation, list, or step-by-step walkthrough — this response will be spoken out loud \
by a voice avatar, so avoid dense text walls, markdown, or long bullet lists in normal chat.
4. PROACTIVE: Don't just answer and stop. When natural, ask one short, relevant follow-up question \
to keep the conversation going, the way a real friend or tutor checks in.
5. KNOWLEDGE CONTEXT: If a block of "Reference material" is provided below, ground your answer in \
it when relevant and say so naturally (e.g. "From what you uploaded..."). If it's not relevant to \
the question, ignore it.
6. EMOTION TAG: On the very last line of every reply, output exactly one tag with no other text on \
that line, choosing whichever best matches the emotional tone of your reply: \
@@EMOTION:happy@@ @@EMOTION:neutral@@ @@EMOTION:concerned@@ @@EMOTION:excited@@ \
@@EMOTION:empathetic@@ @@EMOTION:serious@@ @@EMOTION:encouraging@@ \
This tag is stripped before the student sees or hears your reply, so it must never affect grammar \
of the sentence before it.
"""
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_HINGLISH_MARKERS = re.compile(
    r"\b(hai|hain|kya|kyu|kyun|kaise|kaisi|kaisa|nahi|nahin|mujhe|tumhe|aap|apko|"
    r"mera|meri|mere|tera|teri|tere|uska|uski|accha|acha|theek|thik|karo|karna|"
    r"kar|bata|batao|matlab|yaar|bhai|nahi|haan|han|toh|hoga|hogi|chahiye|wala|"
    r"wali|kaha|kahan|abhi|isse|usse|inko|unko|krna|krte|kro|krdo)\b",
    re.IGNORECASE,
)


def _detect_language_label(text: str) -> str:
    """Best-effort per-message language detection so we can explicitly force the reply
    language each turn, rather than letting the model drift based on conversation history."""
    if _DEVANAGARI_RE.search(text):
        return "Hindi (Devanagari script)"
    if _HINGLISH_MARKERS.search(text):
        return "Hinglish (Romanized Hindi-English mix)"
    return "plain English"

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    emotion: str
    session_id: str


class SpeakRequest(BaseModel):
    text: str


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "elevenlabs_configured": bool(ELEVENLABS_API_KEY),
        "rag_chunks_indexed": len(RAG_CHUNKS),
    }


_TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _tfidf_vector(tf: Counter, idf: dict[str, float]) -> dict[str, float]:
    return {term: count * idf.get(term, 0.0) for term, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = a.keys() & b.keys()
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values())) or 1e-9
    norm_b = math.sqrt(sum(v * v for v in b.values())) or 1e-9
    return dot / (norm_a * norm_b)


def _retrieve_context(query: str, top_k: int = 3) -> str:
    """Dependency-free TF-IDF retrieval over whatever's been uploaded (pure Python — no
    scikit-learn/numpy, so it never needs a C compiler on the user's machine). Good enough
    for a demo; see README for the swap-in path to Pinecone/Chroma + real embeddings
    (handbook Day 16-17)."""
    if not RAG_CHUNKS:
        return ""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return ""

    docs_tokens = [_tokenize(c) for c in RAG_CHUNKS] + [query_tokens]
    n_docs = len(docs_tokens)
    df: Counter = Counter()
    for toks in docs_tokens:
        df.update(set(toks))
    idf = {term: math.log((n_docs + 1) / (count + 1)) + 1 for term, count in df.items()}

    query_vec = _tfidf_vector(Counter(query_tokens), idf)
    scored = []
    for chunk, toks in zip(RAG_CHUNKS, docs_tokens[:-1]):
        chunk_vec = _tfidf_vector(Counter(toks), idf)
        scored.append((_cosine(query_vec, chunk_vec), chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    picked = [chunk for score, chunk in scored[:top_k] if score > 0.05]
    return "\n\n---\n\n".join(picked)


def _to_gemini_contents(history: list[dict]) -> list[dict]:
    """Gemini expects role 'model' where Anthropic used 'assistant', and a parts-list shape."""
    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    return contents


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    history = SESSIONS.setdefault(session_id, [])

    context = _retrieve_context(req.message)
    lang_label = _detect_language_label(req.message)
    system = SYSTEM_PROMPT
    if lang_label == "plain English":
        system += (
            "\n\nIMPORTANT: The student's current message is in plain English. Reply strictly in "
            "English for this turn, regardless of what language earlier messages in this "
            "conversation were in."
        )
    else:
        system += (
            "\n\nIMPORTANT: The student's current message is in Hindi or Hinglish. Reply in warm, "
            "natural spoken Hindi using proper Devanagari script only — never Romanized Hindi or "
            "Hinglish spelling — regardless of what script the student themselves used or what "
            "language earlier messages in this conversation were in. Correct Devanagari script is "
            "required so the reply can be pronounced correctly by a text-to-speech engine."
        )
    if context:
        system += f"\n\nReference material (from uploaded documents):\n{context}"

    history.append({"role": "user", "content": req.message})

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_to_gemini_contents(history[-MAX_TURNS_KEPT:]),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=600,
            ),
        )
    except Exception as exc:  # surfaces API key / rate-limit / network issues to the frontend
        raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}") from exc

    raw_reply = (response.text or "").strip()

    emotion_match = EMOTION_TAG_RE.search(raw_reply)
    if emotion_match and emotion_match.group(1).lower() in VALID_EMOTIONS:
        emotion = emotion_match.group(1).lower()
        clean_reply = EMOTION_TAG_RE.sub("", raw_reply).strip()
    else:
        emotion = "neutral"
        clean_reply = raw_reply

    history.append({"role": "assistant", "content": raw_reply})

    return ChatResponse(reply=clean_reply, emotion=emotion, session_id=session_id)


@app.post("/api/speak")
def speak(req: SpeakRequest):
    """Returns real TTS audio if ElevenLabs is configured. Otherwise returns 204 and the
    frontend transparently falls back to the browser's free built-in speech synthesis."""
    if not ELEVENLABS_API_KEY:
        return Response(status_code=204)

    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": req.text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
            },
            timeout=30,
        )
        r.raise_for_status()
        return Response(content=r.content, media_type="audio/mpeg")
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"ElevenLabs error: {exc}") from exc


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = extract_text_from_upload(file.filename, raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = chunk_text(text)
    RAG_CHUNKS.extend(chunks)
    RAG_SOURCES.extend([file.filename] * len(chunks))

    return {"filename": file.filename, "chunks_added": len(chunks), "total_chunks": len(RAG_CHUNKS)}


@app.get("/api/knowledge")
def knowledge():
    sources = sorted(set(RAG_SOURCES))
    return {"sources": sources, "total_chunks": len(RAG_CHUNKS)}


@app.post("/api/knowledge/clear")
def clear_knowledge():
    RAG_CHUNKS.clear()
    RAG_SOURCES.clear()
    return {"status": "cleared"}
