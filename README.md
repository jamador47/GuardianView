# 🛡️ GuardianView — AI Safety Copilot That Never Blinks

> Real-time AI safety copilot powered by Gemini Live API. Watches your workspace via camera, detects hazards, and alerts you by voice. Configurable for any environment.

## 🎯 Overview

GuardianView is a real-time AI safety agent that monitors workspaces through a standard camera, understands the context of what you're doing, and speaks up the instant something is wrong. Built with Google's Agent Development Kit (ADK) and powered by Gemini's Live API for low-latency, bidirectional voice and video streaming.

**Category:** Live Agents 🗣️

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Browser Frontend                       │
│         Camera + Microphone → WebSocket Stream           │
└──────────────────────┬──────────────────────────────────┘
                       │ Video frames (JPEG) + Audio (PCM16)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               Google Cloud Run                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │         GuardianView Agent (ADK)                  │  │
│  │                                                   │  │
│  │  ┌─────────────┐  ┌──────────────────────────┐   │  │
│  │  │   Safety     │  │  Gemini Live API         │   │  │
│  │  │   Profile    │  │  (Bidi Audio + Vision)   │   │  │
│  │  │   Engine     │  │                          │   │  │
│  │  └─────────────┘  └──────────────────────────┘   │  │
│  │                                                   │  │
│  │  ┌─────────────┐  ┌──────────────────────────┐   │  │
│  │  │   Incident   │  │  Google Search           │   │  │
│  │  │   Logger     │  │  (OSHA Grounding)        │   │  │
│  │  └─────────────┘  └──────────────────────────┘   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.10+
- A Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/guardianview.git
cd guardianview

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp app/.env.example app/.env
# Edit app/.env and add your GOOGLE_API_KEY

# 5. Run the application
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Usage

1. Open `http://localhost:8000` in your browser
2. Select a safety profile (Workshop, Kitchen, or Clinical)
3. Click **Start Camera** to begin video feed
4. Click **Start Mic** for voice interaction
5. Click **Connect** to start real-time safety monitoring
6. GuardianView will watch your workspace and alert you to hazards

> **Note:** Use headphones to prevent the model from hearing its own audio output.

## ☁️ Google Cloud Deployment

### Automated Deployment

```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

### Manual Deployment

```bash
# Build and deploy to Cloud Run
gcloud run deploy guardianview \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-central1"
```

## 🔧 Safety Profiles

GuardianView supports configurable safety profiles:

| Profile | Use Case | Key Hazards |
|---------|----------|-------------|
| 🔧 **Workshop** | Industrial, lab, maker space | PPE compliance, tool safety, electrical hazards |
| 🍳 **Kitchen** | Commercial/home kitchen | Cross-contamination, burns, knife safety |
| 🏥 **Clinical** | Medical, surgical settings | Sterile field, sharps, instrument count |

Set the active profile via the `SAFETY_PROFILE` environment variable or the UI dropdown.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Gemini 2.5 Flash (Native Audio) via Live API |
| Agent Framework | Google Agent Development Kit (ADK) |
| Backend | Python, FastAPI, WebSockets |
| Frontend | HTML, CSS, JavaScript, Web Audio API |
| Cloud | Google Cloud Run |
| Grounding | Google Search (OSHA regulations) |

## 📁 Project Structure

```
guardianview/
├── app/
│   ├── guardianview_agent/
│   │   ├── __init__.py
│   │   └── agent.py          # Agent definition, tools, safety profiles
│   ├── static/
│   │   ├── index.html         # Main UI
│   │   ├── css/style.css      # Styling
│   │   └── js/app.js          # WebSocket, camera, audio handling
│   ├── main.py                # FastAPI server with WebSocket bidi-streaming
│   └── .env.example           # Environment configuration template
├── requirements.txt
├── Dockerfile
├── deploy.sh                  # Automated Cloud Run deployment
└── README.md
```

## 📊 Data Sources

- **U.S. Bureau of Labor Statistics** — Census of Fatal Occupational Injuries 2024
- **OSHA** — 29 CFR 1910 (General Industry), 29 CFR 1926 (Construction)
- **AFL-CIO** — "Death on the Job: The Toll of Neglect" 2025
- **FDA Food Code** — Kitchen safety regulations
- **WHO** — Surgical Safety Checklist

## 📜 License

MIT License
