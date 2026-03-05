# 🛡️ GuardianView — Your AI Safety Copilot That Never Blinks

> Real-time AI safety copilot powered by Gemini Live API. Watches your workspace via camera, detects hazards, alerts you by voice, and adapts to any environment in any language.

## 💡 Inspiration

Every 104 minutes, a worker dies from a workplace injury in the United States. In 2024 alone, employers reported 2.5 million workplace injuries and illnesses (U.S. Bureau of Labor Statistics), and experts estimate the true toll is between 5.2 and 7.8 million annually when accounting for widespread underreporting (AFL-CIO, "Death on the Job," 2025). The economic cost reaches up to $348 billion per year.

The problem isn't ignorance. Workers know the rules. But in the moment, when your hands are full, your focus is locked on the task, and you're working under pressure, hazards slip past unnoticed. Safety training happens once; the dangerous moment happens every day.

As a Mechatronics and Biomedical engineer, I've spent years in workshops, labs, and industrial environments. I've seen firsthand how easily safety lapses occur, even among experienced professionals. The idea behind GuardianView was simple: what if you had an expert safety officer who watched your workspace in real-time, never got tired, never looked away, and could talk to you naturally while you worked?

## 🎯 What It Does

GuardianView is a real-time AI safety copilot powered by Google's Gemini Live API. It watches your workspace through a standard camera, understands the context of what you're doing, and speaks up the instant something is wrong.

**Category:** Live Agents 🗣️

### Core Capabilities

- **Real-time hazard detection via vision:** Identifies missing PPE (safety glasses, gloves, ear protection), unsafe tool handling, improper posture, spills, and environmental hazards through continuous video analysis powered by Gemini's multimodal understanding.

- **Proactive voice alerts:** Unlike typical chatbots that wait for user input, GuardianView actively monitors the video feed and initiates spoken warnings when it detects danger, even if the user hasn't said a word.

- **Natural, interruptible voice interaction:** Powered by Gemini Live API, the agent speaks alerts conversationally and can be interrupted at any time. Ask it if a chemical combination is safe, request a pre-task safety checklist, or tell it to stand by—all hands-free.

- **Pre-task safety consultations:** Before starting any task, ask GuardianView for guidance. It will provide a comprehensive safety checklist, recommend proper PPE, identify potential hazards, and suggest safe procedures tailored to your specific work.

- **Session-level contextual awareness:** Within a session, GuardianView leverages Gemini's built-in session memory to track what's happening over time. It remembers that you already put on your safety glasses, knows you're currently soldering, and can escalate warnings if you ignore initial alerts.

- **Dramatic visual alerts:** Critical hazards trigger an instant red flash overlay across the video feed (0.3s duration, semi-transparent) paired with a pulsing border animation, creating an unmissable visual warning that complements the voice alert.

- **Multilingual support:** GuardianView speaks safety in 50+ languages. Configure your preferred alert language in the settings, and the agent will deliver all spoken warnings, pre-task guidance, and recommendations in that language while maintaining full technical accuracy and OSHA compliance.

- **Comprehensive safety reports:** Generate detailed PDF safety reports for any session with a single click. Reports include incident timeline, safety score trends, all detected hazards with severity classifications, timestamps, spoken recommendations, and regulatory citations—ready for compliance documentation.

- **Severity-driven prompt behavior:** The agent's system instruction defines clear severity tiers (critical, high, medium, low) with specific response rules for each. Critical hazards trigger immediate spoken interruptions and visual flashes; minor observations are mentioned conversationally at natural pauses.

- **Configurable safety profiles:** The agent isn't hardcoded for one environment. Load a kitchen profile and it watches for cross-contamination and burns; switch to an industrial workshop profile and it monitors PPE compliance and tool safety; configure a clinical profile and it tracks sterile field integrity. Profiles are defined as Python dictionaries and injected into the system instruction at startup.

- **Regulation-aware through Google Search:** The agent has access to Google Search as a tool, allowing it to look up specific OSHA standards, chemical compatibility information, or Material Safety Data Sheets during a live conversation.

- **Mobile-responsive design:** Fully responsive interface optimized for tablets and mobile devices with touch-friendly controls, adaptive layouts, and proper viewport handling for monitoring on the go.

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

### Test 6: Multilingual Alerts

1. While connected, open the **Settings** panel in the sidebar
2. Change the **Alert Language** dropdown to Spanish (Español)
3. Introduce a safety hazard (e.g., pick up a tool without safety glasses)
4. **Expected:** GuardianView issues the warning in Spanish ("No veo protección para los ojos...")
5. Switch to another language (French, German, Japanese, etc.)
6. **Expected:** Subsequent warnings are delivered in the newly selected language

### Test 7: Visual Alert Flash

1. Connect and position yourself in front of the camera with a clear view of the video feed
2. Deliberately create a critical safety hazard (e.g., use power tools without eye protection, reach toward a hot surface)
3. **Expected:** When the agent detects the critical hazard, you'll see a dramatic red semi-transparent flash overlay across the entire video feed (0.3 seconds), accompanied by the pulsing red border and spoken alert
4. Observe the coordinated multimodal alert: visual flash + border pulse + voice warning

### Test 8: Pre-Task Safety Consultation

1. Connect with camera and microphone active
2. Before starting work, ask out loud: *"I'm about to weld some metal. What should I know?"*
3. **Expected:** GuardianView provides a comprehensive pre-task safety briefing including required PPE (welding helmet, gloves, fire-resistant clothing, ventilation), potential hazards (UV radiation, fumes, fire risk), and safe procedures
4. Ask: *"What safety steps should I take before using a table saw?"*
5. **Expected:** Detailed checklist covering blade guards, push sticks, eye protection, hearing protection, proper stance, and kickback prevention

### Test 9: Safety Report Generation

1. Complete a monitoring session with several incidents logged (introduce 3-4 different hazards during the session)
2. Click the **Generate Report** button in the sidebar
3. **Expected:** A comprehensive PDF safety report downloads automatically, containing:
   - Session metadata (date, duration, profile)
   - Safety score summary
   - Full incident timeline with timestamps
   - Each hazard description, severity level, and spoken recommendation
   - Regulatory citations where applicable
4. Open the PDF and verify all incidents are documented with proper formatting

### Troubleshooting

- **No audio from agent:** Make sure your browser has autoplay permissions enabled for localhost. Try clicking anywhere on the page first (browsers require user interaction before playing audio).
- **Agent not responding:** Check the terminal for errors. Verify your `GOOGLE_API_KEY` is valid and has Gemini API access.
- **Camera not showing:** Ensure you've granted camera permissions in your browser. Try using Chrome or Edge.
- **Agent too chatty or too quiet:** The heartbeat ping interval (1 second) and system prompt can be tuned in `app/static/js/app.js` and `app/guardianview_agent/agent.py` respectively.

## 🔨 How I Built It

The foundation of GuardianView is Google's Agent Development Kit (ADK) with the Gemini 2.0 Flash model, connected through the Live API for real-time bidirectional audio and video streaming.

### Backend Architecture

The backend is a Python FastAPI server that manages WebSocket connections between the browser and the ADK runner. When a user connects, the server creates a `LiveRequestQueue` and spins up two concurrent async tasks:

- **Upstream task:** Receives camera frames (base64 JPEG at 1 FPS) and microphone audio (PCM16) from the client and forwards them to the Gemini Live session
- **Downstream task:** Listens for agent events (audio responses, text, transcriptions) and streams them back to the browser in real-time

### Frontend Implementation

The frontend is a single-page web application that captures the user's camera feed at 1 frame per second (optimized for the Live API's processing rate), encodes each frame as base64 JPEG, and sends it over WebSocket alongside PCM16 audio from the microphone. On the receiving end, it decodes the agent's audio responses from base64 PCM back into Float32 samples and plays them through the Web Audio API for real-time spoken alerts.

### Configurable Safety Intelligence

The safety intelligence lives in a configurable profile system. Each profile (workshop, kitchen, clinical) is a Python dictionary that defines:
- Hazards to monitor
- Applicable regulations and standards
- Severity-based response rules
- Alert language and terminology

These profiles are injected directly into the agent's system instruction at startup, meaning the same agent codebase adapts to completely different environments simply by loading a different profile. Adding a new environment is as simple as writing a new profile dictionary—no code changes required.

### Multilingual Support

Language support is implemented through dynamic system prompt injection. When a user selects a language from the settings dropdown (50+ languages supported), the agent's system instruction is updated to include: `**LANGUAGE RULE:** You MUST speak all safety alerts, warnings, and recommendations in {selected_language}. Technical terms and OSHA citations may remain in English, but all conversational speech must be in {selected_language}.`

This approach leverages Gemini's native multilingual capabilities while ensuring safety-critical information remains accurate and grounded in regulations.

### Visual Alert System

The dramatic red flash overlay is implemented using CSS animations and JavaScript DOM manipulation:

- **CSS:** A `::after` pseudo-element on the video container with `@keyframes` animation (0.3s duration, 0 to 70% opacity for critical, 0 to 50% for high severity)
- **JavaScript:** When the backend sends a safety incident event, the frontend adds a `flash-critical` or `flash-high` class to trigger the animation
- **Coordination:** The flash, border pulse, and voice alert fire simultaneously for maximum impact

### Report Generation

Safety reports are generated client-side using jsPDF, eliminating the need for a separate backend reporting service:

1. When the user clicks "Generate Report," JavaScript collects all incident data from the session
2. jsPDF constructs a formatted PDF with sections for metadata, safety score, and incident timeline
3. Each incident includes timestamp, severity badge (color-coded), description, and recommendation
4. The PDF is automatically downloaded with a filename containing the session date

### Proactive Monitoring

**Making the agent truly proactive was the hardest challenge.** The Gemini Live API is designed for conversational turn-taking, where the user speaks and the model responds. But a safety copilot needs to do the opposite: it needs to speak first when it sees danger, even when the user hasn't said anything.

The solution was a lightweight client-side heartbeat: the frontend sends a `[SAFETY_CHECK]` prompt every second alongside the continuous video frames. This keeps the model's attention on the incoming visual stream and gives it a consistent trigger point to generate spoken alerts when it detects hazards. Combined with the `proactive_audio` flag in `RunConfig` and an aggressive system prompt ("DO NOT WAIT", "INTERRUPT IMMEDIATELY"), this transforms GuardianView from a passive assistant into an active watchdog.

### Grounding and Knowledge

For grounding, the agent has access to Google Search as a built-in ADK tool, allowing it to verify specific OSHA regulations or look up safety information in real-time. Custom function tools handle:
- Incident logging (currently to server console, Cloud Firestore integration planned)
- Profile management
- Session state tracking

### Deployment

The entire application is containerized with Docker and deployed to Google Cloud Run using an automated deployment script, making the backend fully managed and scalable. The stateless design allows multiple concurrent user sessions without resource contention.

### Tech Stack Summary

- **AI Model:** Gemini 2.0 Flash (via Gemini Live API for real-time multimodal streaming)
- **Agent Framework:** Google Agent Development Kit (ADK)
- **Backend:** Python, FastAPI, WebSockets
- **Deployment:** Google Cloud Run (Docker container, automated via deploy script)
- **Grounding:** Google Search (ADK built-in tool) for OSHA regulation lookup
- **Frontend:** HTML, CSS, JavaScript, Web Audio API
- **Report Generation:** jsPDF (client-side PDF generation)

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

## 🚧 Challenges I Faced

### 1. Making the Agent Truly Proactive

**The biggest technical challenge:** The Gemini Live API is designed for conversational turn-taking, where the user speaks and the model responds. But a safety copilot needs to do the opposite—it must speak first when it sees danger, even when the user is silent.

The ADK's `ProactivityConfig` wasn't available in the version I was using, so I engineered a workaround: a lightweight client-side heartbeat that sends a `[SAFETY_CHECK]` prompt every second alongside video frames. This keeps the model's attention on the visual stream and provides a consistent trigger for alerts. Combined with the `proactive_audio` flag and an aggressive system prompt ("DO NOT WAIT", "INTERRUPT IMMEDIATELY"), this transformed GuardianView from a passive assistant into an active watchdog that genuinely interrupts you when danger is detected.

### 2. Balancing Responsiveness with False Positives

Real-time vision analysis of a busy workspace produces noise. A hand briefly passing near a hot surface isn't the same as reaching for it without protection. I spent significant time tuning the system prompt and severity classification to reduce unnecessary interruptions while maintaining zero tolerance for genuinely critical hazards. The solution was explicit severity tiers with different behavioral rules: critical hazards interrupt immediately, while minor observations wait for natural conversational pauses.

### 3. Making Voice Interaction Feel Natural, Not Annoying

A safety agent that constantly talks is one that gets turned off. The biggest design challenge was alert cadence—ensuring GuardianView speaks at the right moment with the right urgency. Too chatty and users ignore it; too quiet and hazards slip through. The solution was severity-driven prompts combined with context awareness, allowing the agent to escalate warnings if initial alerts are ignored.

### 4. Grounding in Real Regulations Without Overwhelming the User

OSHA regulations are dense and technical. The challenge was surfacing the relevant standard when it matters ("That's an OSHA 1910.133 violation, eye protection is required for grinding operations") without turning every alert into a legal lecture. Google Search integration provides grounding, but the prompt engineering ensures regulatory citations enhance rather than dominate the conversation.

### 5. Multilingual Accuracy for Safety-Critical Information

Implementing multilingual support wasn't just translation—it required ensuring safety-critical terminology remained accurate across 50+ languages while maintaining natural conversational flow. The solution was dynamic prompt injection that explicitly separates technical terms (which may remain in English for precision) from conversational speech (which must be in the user's language).

### 6. Coordinating Multimodal Alerts

Synchronizing the visual flash overlay, border pulse animation, and voice alert required careful timing coordination between the backend event stream, frontend JavaScript DOM manipulation, and CSS animation triggers. Getting all three modalities to fire simultaneously for maximum impact took iterative refinement.

## 📚 What I Learned

- **Gemini's Live API handles real-time multimodal streams remarkably well**—the latency between seeing a hazard and producing a spoken alert is fast enough to be genuinely useful in safety applications.

- **Building proactive AI agents within a conversational framework requires creative engineering.** The heartbeat pattern I developed could be a useful technique for anyone building monitoring or surveillance agents on top of conversational APIs.

- **The configurable profile approach proved more powerful than expected.** Different environments don't just need different hazard lists; they need fundamentally different alert behaviors and severity thresholds. The profile-as-data pattern makes the system highly extensible.

- **Voice UX for safety applications is a distinct design problem.** Unlike chatbots where the user initiates, a safety copilot must initiate intelligently, and getting that wrong makes the tool useless. Context-aware severity escalation is critical.

- **Prompt-driven severity rules work surprisingly well for this use case.** While a hardcoded classifier would be more deterministic, the model follows severity instructions consistently enough to be practical, especially when the prompt is explicit about expected behavior for each level.

- **Client-side report generation with jsPDF eliminates backend complexity** and enables instant document creation without additional API calls or server-side processing, making the system more scalable and cost-effective.

- **Responsive design for safety monitoring applications requires special consideration** for touch targets, viewport management, and ensuring critical information (alerts, HUD elements) remains accessible across all device sizes.

## 🔮 What's Next

- **Persistent incident logging:** Connect the incident logging tool to Cloud Firestore for durable, queryable safety records across sessions and users.

- **Externalized profiles:** Move safety profiles from in-code dictionaries to Cloud Storage JSON files, enabling dynamic profile loading and user-created custom profiles without code deployments.

- **OSHA knowledge base:** Index OSHA regulations in Vertex AI Search for more precise, grounded safety citations without relying on general web search.

- **Wearable integration:** Support for smart glasses (Google Glass Enterprise, RealWear, Vuzix) and body-worn cameras for true hands-free operation in industrial settings.

- **Multi-camera support:** Monitor an entire workshop or factory floor with multiple camera feeds, not just a single viewpoint. Aggregate hazard detection across all cameras with spatial awareness.

- **Team dashboards:** Aggregate safety data across shifts and workers for safety managers. Real-time fleet monitoring, trend analysis, and team-wide safety score tracking.

- **Compliance reporting:** Auto-generate OSHA-compliant incident reports from logged events, including Form 300 (Log of Work-Related Injuries and Illnesses) export.

- **Incident replay and training:** Save video clips of detected incidents for post-session review and safety training materials. Build a library of real-world hazards for onboarding.

- **Integration with IoT sensors:** Combine camera vision with environmental sensors (gas detectors, temperature, noise levels) for comprehensive workspace monitoring.

- **Custom hazard training:** Allow organizations to train custom hazard detection models on their specific workplace environments and equipment.

## 📊 Data Sources

- **U.S. Bureau of Labor Statistics** — Census of Fatal Occupational Injuries 2024 ([bls.gov/iif](https://www.bls.gov/iif/))
- **U.S. Bureau of Labor Statistics** — Survey of Occupational Injuries and Illnesses 2024 ([bls.gov/news.release/osh.htm](https://www.bls.gov/news.release/osh.htm))
- **AFL-CIO** — "Death on the Job: The Toll of Neglect" 2025 ([aflcio.org/reports/dotj-2025](https://aflcio.org/reports/dotj-2025))
- **OSHA** — 29 CFR 1910 (General Industry), 29 CFR 1926 (Construction)
- **FDA Food Code** — Kitchen safety regulations
- **WHO** — Surgical Safety Checklist

## 📜 License

MIT License
