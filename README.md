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

## 🧪 Reproducible Testing (For Judges)

Follow these steps to verify GuardianView's core capabilities. Each test can be performed with just a webcam and common household or workshop items.

### Test 1: PPE Detection (Workshop Profile)

1. Start the app with the **Workshop** profile selected (default)
2. Connect camera, microphone, and click **Connect**
3. Sit in front of the camera at a desk or workbench
4. Pick up any tool (screwdriver, drill, soldering iron, etc.) and begin using it **without safety glasses**
5. **Expected:** GuardianView speaks a warning about missing eye protection within a few seconds, citing OSHA 1910.133
6. Put on safety glasses and continue working
7. **Expected:** GuardianView acknowledges the correction or stops warning about eye protection

### Test 2: Kitchen Hazard Detection (Kitchen Profile)

1. Switch to the **Kitchen** profile using the dropdown
2. Reconnect (disconnect and connect again so the new profile takes effect)
3. Stand in front of a kitchen counter with a cutting board and knife
4. Begin cutting food with an improper grip or cutting toward your body
5. **Expected:** GuardianView warns about unsafe knife handling technique
6. Place raw meat next to ready-to-eat food on the same surface
7. **Expected:** GuardianView warns about cross-contamination risk

### Test 3: Voice Interaction (Any Profile)

1. While connected, ask out loud: *"What PPE do I need before using an angle grinder?"*
2. **Expected:** GuardianView responds with a spoken safety checklist (eye protection, face shield, gloves, ear protection)
3. Say: *"Is it safe to mix bleach and ammonia?"*
4. **Expected:** GuardianView warns against mixing these chemicals and may use Google Search to ground its response

### Test 4: Proactive Monitoring (No User Speech)

1. Connect and do **not** speak at all
2. Simply work in front of the camera, deliberately introducing a visible hazard (e.g., removing gloves, reaching near a hot surface)
3. **Expected:** GuardianView speaks up on its own without any user prompt, demonstrating proactive monitoring via the heartbeat mechanism

### Test 5: Profile Switching

1. Note the type of warnings received with the current profile
2. Switch to a different profile (e.g., Workshop → Kitchen) using the dropdown
3. Disconnect and reconnect
4. **Expected:** Warnings now correspond to the new profile's hazard categories (e.g., no longer mentioning PPE, now watching for food safety)

### Troubleshooting

- **No audio from agent:** Make sure your browser has autoplay permissions enabled for localhost. Try clicking anywhere on the page first (browsers require user interaction before playing audio).
- **Agent not responding:** Check the terminal for errors. Verify your `GOOGLE_API_KEY` is valid and has Gemini API access.
- **Camera not showing:** Ensure you've granted camera permissions in your browser. Try using Chrome or Edge.
- **Agent too chatty or too quiet:** The heartbeat ping interval (1 second) and system prompt can be tuned in `app/static/js/app.js` and `app/guardianview_agent/agent.py` respectively.

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
| AI Model | Gemini 2.0 Flash via Live API |
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
