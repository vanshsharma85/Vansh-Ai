# Vansh AI 🎙️

**A human-like, hands-free AI voice avatar — built by [Vansh Sharma](https://github.com/).**
## For Live - **(https://vansh-ai.netlify.app/?backend=https://vansh-ai.onrender.com)**

Say *"Hey Vansh AI"* and just start talking. It listens, thinks, replies out loud, and its
animated face reacts with expression and lip-sync — in whatever language you speak to it in.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75B2)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- 🎙️ **Wake-word activation** — say "Hey Vansh AI" and it starts listening, no button needed
- 🔁 **Hands-free conversation loop** — keeps listening after every reply, no re-clicking the mic
- 🌐 **Automatic language detection** — speak Hindi, Hinglish, English, or mix them; it replies in kind and switches its own voice language to match
- 🧠 **Real AI brain** — powered by Google Gemini (free API tier, no credit card)
- 😊 **Emotionally expressive avatar** — an animated SVG face with live lip-sync, blinking, and emotion-reactive expressions (happy, concerned, excited, empathetic, and more)
- 🔊 **Realistic voice, upgradeable for free** — falls back to the browser's built-in speech synthesis by default, or plug in a free ElevenLabs key for studio-quality multilingual voice with true audio-driven lip-sync
- 📄 **Document Q&A (RAG)** — upload a `.txt`/`.md`/`.pdf` and ask questions grounded in it
- 🖥️ **Runs entirely on your machine** — no cloud account required except a free Gemini key

## 🎬 Demo

![Demo](Login_page.jpg)

## 🧱 Tech Stack

| Layer | Tech |
|---|---|
| AI brain | [Google Gemini API](https://aistudio.google.com/) (free tier) |
| Backend | Python, FastAPI, Uvicorn |
| Voice input | Web Speech API (built into Chrome/Edge, free) |
| Voice output | Browser SpeechSynthesis (free) → [ElevenLabs](https://elevenlabs.io/) (optional upgrade) |
| Frontend | Vanilla HTML/CSS/JS — zero build step, one file |
| Document search | Dependency-free pure-Python TF-IDF |

## 🏗️ Architecture

```
 ┌─────────────┐   voice / text    ┌──────────────┐   Gemini API    ┌───────────┐
 │  Browser     │ ─────────────────▶│  FastAPI      │────────────────▶│  Google   │
 │  (index.html)│                   │  backend      │                 │  Gemini   │
 │              │◀───────────────── │  main.py      │◀──────────────── └───────────┘
 │  Web Speech  │  reply + emotion  │               │
 │  API (STT)   │                   │  /api/chat    │
 │  SVG avatar  │                   │  /api/speak ──┼──▶ ElevenLabs (optional)
 │  + lip-sync  │                   │  /api/upload ─┼──▶ TF-IDF RAG index (in-memory)
 └─────────────┘                    └──────────────┘
```

## 📁 Project Structure

```
vansh-ai/
├── backend/
│   ├── main.py             # FastAPI server — the AI brain, TTS bridge, RAG
│   ├── rag_utils.py         # Document chunking + text extraction for RAG
│   ├── requirements.txt
│   ├── .env.example
│   ├── install.bat          # Windows one-click setup
│   └── run.bat               # Windows one-click start
├── frontend/
│   ├── index.html            # The entire app — avatar, chat, voice engine
│   └── run.bat                 # Windows one-click start
├── LICENSE
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- Chrome or Edge (required for free voice input/output)
- A free [Gemini API key](https://aistudio.google.com/apikey) (no credit card needed)

### Windows — one-click setup
```
backend\install.bat      # creates venv, installs deps, creates .env
# open backend\.env and paste your GEMINI_API_KEY
backend\run.bat           # starts the backend
frontend\run.bat            # starts and opens the frontend
```

### macOS / Linux
```bash
# backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your GEMINI_API_KEY
uvicorn main:app --reload --port 8000

# frontend (in a second terminal)
cd frontend
python3 -m http.server 5500
```
Open **http://localhost:5500** in Chrome or Edge.

### Environment variables (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | – | Defaults to `gemini-3.5-flash` |
| `ELEVENLABS_API_KEY` | – | Optional — enables realistic voice + true audio lip-sync |
| `ELEVENLABS_VOICE_ID` | – | Optional — which ElevenLabs voice to use |

## 🎯 Usage

- Say **"Hey Vansh AI"** any time to start talking hands-free
- Or tap the mic button to start/stop a conversation manually
- Or just type in the chat box
- Click the **knowledge base** pill to upload a document and ask questions about it

## 🗺️ Roadmap

- [ ] Swap the SVG avatar for a photoreal streaming avatar (HeyGen / D-ID)
- [ ] Token-by-token streaming responses for lower latency
- [ ] Persistent memory across sessions (currently resets on server restart)
- [ ] Webcam-based emotion detection so it can read the user's mood too
- [ ] Cloud deployment guide (Render + Netlify)

## ⚠️ Known Limitations

This is a working prototype, not a production system:
- Conversation memory is in-memory only and resets when the backend restarts
- Document search (RAG) uses simple TF-IDF, not vector embeddings — fine for a few files, not a large knowledge base
- No authentication/login layer
- Browser SpeechSynthesis voice quality varies by OS; ElevenLabs is recommended for a polished demo

## 📄 License

Released under the [MIT License](LICENSE).

## 👤 Author

**Vansh Sharma**
Built as a personal AI assistant project.
