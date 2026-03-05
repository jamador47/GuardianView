# GuardianView — Your AI Safety Copilot That Never Blinks

## Inspiration

Every 104 minutes, a worker dies from a workplace injury in the United States. In 2024 alone, employers reported 2.5 million workplace injuries and illnesses (U.S. Bureau of Labor Statistics), and experts estimate the true toll is between 5.2 and 7.8 million annually when accounting for widespread underreporting (AFL-CIO, "Death on the Job," 2025). The economic cost reaches up to $348 billion per year.

The problem isn't ignorance. Workers know the rules. But in the moment, when your hands are full, your focus is locked on the task, and you're working under pressure, hazards slip past unnoticed. Safety training happens once; the dangerous moment happens every day.

As a Mechatronics and Biomedical engineer, I've spent years in workshops, labs, and industrial environments. I've seen firsthand how easily safety lapses occur, even among experienced professionals. The idea behind GuardianView was simple: what if you had an expert safety officer who watched your workspace in real-time, never got tired, never looked away, and could talk to you naturally while you worked?

## What It Does

GuardianView is a real-time AI safety copilot powered by Google's Gemini Live API. It watches your workspace through a standard camera, understands the context of what you're doing, and speaks up the instant something is wrong.

### Core Capabilities

**Real-time hazard detection via vision:** Identifies missing PPE (safety glasses, gloves, ear protection), unsafe tool handling, improper posture, spills, and environmental hazards, all through continuous video analysis powered by Gemini's multimodal understanding.

**Proactive voice alerts:** Unlike a typical chatbot that waits for the user to speak, GuardianView actively monitors the video feed and initiates spoken warnings when it detects danger, even if the user hasn't said a word. The system analyzes every frame (once per second) and speaks up immediately when critical hazards are detected.

**Natural, interruptible voice interaction:** Powered by Gemini Live API, the agent speaks alerts conversationally and can be interrupted at any time. Ask it if a chemical combination is safe, request a pre-task safety checklist, or tell it to stand by—all hands-free.

**Pre-task safety consultations:** Before starting any task, ask GuardianView for guidance. It will provide a comprehensive safety checklist, recommend proper PPE, identify potential hazards, and suggest safe procedures tailored to your specific work. Whether you're about to weld, use a table saw, or handle chemicals, GuardianView acts as your safety advisor before the work even begins.

**Session-level contextual awareness:** Within a session, GuardianView leverages Gemini's built-in session memory to track what's happening over time. It remembers that you already put on your safety glasses, knows you're currently soldering, and can escalate warnings if you ignore initial alerts.

**Dramatic visual alerts:** Critical hazards trigger an instant red flash overlay across the video feed (0.3 seconds, semi-transparent) paired with a pulsing border animation, creating an unmissable visual warning that complements the voice alert. The coordinated multimodal approach—visual flash, border pulse, and voice warning—ensures you can't miss a critical safety issue even in noisy environments.

**Multilingual support:** GuardianView speaks safety in 50+ languages. Configure your preferred alert language in the settings (Spanish, French, German, Japanese, Mandarin, Arabic, Hindi, Portuguese, and dozens more), and the agent delivers all spoken warnings, pre-task guidance, and recommendations in that language while maintaining full technical accuracy and OSHA compliance. Language barriers no longer compromise workplace safety.

**Comprehensive safety reports:** Generate detailed PDF safety reports for any session with a single click. Reports include session metadata, safety score trends, complete incident timeline with timestamps, all detected hazards with severity classifications, spoken recommendations, and regulatory citations—ready for compliance documentation and safety audits.

**Severity-driven prompt behavior:** The agent's system instruction defines clear severity tiers (critical, high, medium, low) with specific response rules for each. Critical hazards trigger immediate spoken interruptions and visual flashes; minor observations are mentioned conversationally at natural pauses.

**Configurable safety profiles:** The agent isn't hardcoded for one environment. Load a kitchen profile and it watches for cross-contamination and burns; switch to an industrial workshop profile and it monitors PPE compliance and tool safety; configure a clinical profile and it tracks sterile field integrity. Profiles are defined as Python dictionaries and injected into the system instruction at startup. Adding a new environment is as simple as writing a new profile dictionary—no code changes required.

**Regulation-aware through Google Search:** The agent has access to Google Search as a tool, allowing it to look up specific OSHA standards, chemical compatibility information, or Material Safety Data Sheets during a live conversation.

**Mobile-responsive design:** Fully responsive interface optimized for tablets and mobile devices with touch-friendly controls, adaptive layouts, and proper viewport handling for monitoring on the go.

## How I Built It

The foundation of GuardianView is Google's Agent Development Kit (ADK) with the Gemini 2.0 Flash model, connected through the Live API for real-time bidirectional audio and video streaming.

### Backend Architecture

The backend is a Python FastAPI server that manages WebSocket connections between the browser and the ADK runner. When a user connects, the server creates a `LiveRequestQueue` and spins up two concurrent async tasks:

- **Upstream task:** Receives camera frames (base64 JPEG at 1 frame per second) and microphone audio (PCM16) from the client and forwards them to the Gemini Live session
- **Downstream task:** Listens for agent events (audio responses, text, transcriptions) and streams them back to the browser in real-time

The WebSocket connection maintains a persistent bidirectional stream, enabling the low-latency interaction required for safety monitoring.

### Frontend Implementation

The frontend is a single-page web application that captures the user's camera feed at 1 frame per second (optimized for the Live API's processing rate), encodes each frame as base64 JPEG, and sends it over the WebSocket alongside PCM16 audio from the microphone.

On the receiving end, it decodes the agent's audio responses from base64 PCM back into Float32 samples and plays them through the Web Audio API for real-time spoken alerts with minimal latency.

### Configurable Safety Intelligence

The safety intelligence lives in a configurable profile system. Each profile (workshop, kitchen, clinical) is a Python dictionary that defines:

- Hazards to monitor
- Applicable regulations and standards
- Severity-based response rules
- Alert language and terminology

These profiles are injected directly into the agent's system instruction at startup, meaning the same agent codebase adapts to completely different environments simply by loading a different profile. Adding a new environment is as simple as writing a new profile dictionary—no code changes required.

### Multilingual Support Implementation

Language support is implemented through dynamic system prompt injection. When a user selects a language from the settings dropdown (50+ languages supported), the agent's system instruction is updated to include:

```
**LANGUAGE RULE:** You MUST speak all safety alerts, warnings, and
recommendations in {selected_language}. Technical terms and OSHA
citations may remain in English, but all conversational speech must
be in {selected_language}.
```

This approach leverages Gemini's native multilingual capabilities while ensuring safety-critical information remains accurate and grounded in regulations. The system instruction change takes effect immediately upon language selection.

### Visual Alert System

The dramatic red flash overlay is implemented using CSS animations and JavaScript DOM manipulation:

- **CSS:** A `::after` pseudo-element on the video container with `@keyframes` animation (0.3s duration, 0 to 70% opacity for critical alerts, 0 to 50% for high severity)
- **JavaScript:** When the backend sends a safety incident event, the frontend adds a `flash-critical` or `flash-high` class to the video container to trigger the animation
- **Coordination:** The flash, border pulse, and voice alert fire simultaneously for maximum impact and unmissable presence

The timing was carefully tuned—0.3 seconds is long enough to be noticed but short enough not to obscure the video feed unnecessarily.

### Report Generation

Safety reports are generated client-side using jsPDF, eliminating the need for a separate backend reporting service:

1. When the user clicks "Generate Report," JavaScript collects all incident data stored during the session
2. jsPDF constructs a formatted PDF with sections for session metadata, safety score history, and a complete incident timeline
3. Each incident includes timestamp, severity badge (color-coded: red for critical, orange for high, yellow for medium), description, and the agent's spoken recommendation
4. The PDF is automatically downloaded with a filename containing the session date

This client-side approach makes report generation instant and reduces backend complexity and costs.

### Proactive Monitoring - The Technical Challenge

**Making the agent truly proactive was the hardest challenge.** The Gemini Live API is designed for conversational turn-taking, where the user speaks and the model responds. But a safety copilot needs to do the opposite: it needs to speak first when it sees danger, even when the user hasn't said anything.

The ADK's `ProactivityConfig` was not available in the version I was working with, so I had to engineer a workaround. The solution was a lightweight client-side heartbeat: the frontend sends a `[SAFETY_CHECK]` prompt every second alongside the continuous video frames. This keeps the model's attention on the incoming visual stream and gives it a consistent trigger point to generate spoken alerts when it detects hazards.

It's a simple hack, but it transformed GuardianView from a passive assistant that only responded when spoken to into an active watchdog that genuinely interrupts you when your hand is too close to the grinder without safety glasses. I also configured the `proactive_audio` flag in the `RunConfig` to signal to the model that it should initiate speech, which combined with an aggressive system prompt ("DO NOT WAIT", "INTERRUPT IMMEDIATELY") made the proactive behavior reliable.

The optimization to check every frame (instead of every 2 frames) cut detection latency in half, from 2 seconds to 1 second—a critical improvement for time-sensitive hazards.

### Grounding and Knowledge

For grounding, the agent has access to Google Search as a built-in ADK tool, allowing it to verify specific OSHA regulations or look up safety information in real-time. Custom function tools handle:

- Incident logging (currently to server console, Cloud Firestore integration planned)
- Profile management
- Session state tracking

### Deployment

The entire application is containerized with Docker and deployed to Google Cloud Run using an automated deployment script, making the backend fully managed, scalable, and globally accessible. The stateless design allows multiple concurrent user sessions without resource contention.

### Tech Stack Summary

- **AI Model:** Gemini 2.0 Flash (via Gemini Live API for real-time multimodal streaming)
- **Agent Framework:** Google Agent Development Kit (ADK)
- **Backend:** Python, FastAPI, WebSockets
- **Deployment:** Google Cloud Run (Docker container, automated via deploy script)
- **Grounding:** Google Search (ADK built-in tool) for OSHA regulation lookup
- **Frontend:** HTML, CSS, JavaScript, Web Audio API
- **Report Generation:** jsPDF (client-side PDF generation)

## Challenges I Faced

### 1. Making the Agent Truly Proactive

**The biggest technical challenge:** The Gemini Live API is designed for conversational turn-taking, where the user speaks and the model responds. But a safety copilot needs to do the opposite—it must speak first when it sees danger, even when the user is silent.

The ADK's `ProactivityConfig` wasn't available in the version I was using, so I engineered a workaround: a lightweight client-side heartbeat that sends a `[SAFETY_CHECK]` prompt every second alongside video frames. This keeps the model's attention on the visual stream and provides a consistent trigger for alerts. Combined with the `proactive_audio` flag and an aggressive system prompt ("DO NOT WAIT", "INTERRUPT IMMEDIATELY"), this transformed GuardianView from a passive assistant into an active watchdog that genuinely interrupts you when danger is detected.

The key insight was that the model needed a regular "invitation" to respond, but one that didn't interfere with the user experience. The `[SAFETY_CHECK]` prompt is invisible to the user but critical to the agent's behavior.

### 2. Balancing Responsiveness with False Positives

Real-time vision analysis of a busy workspace produces noise. A hand briefly passing near a hot surface isn't the same as reaching for it without protection. I spent significant time tuning the system prompt and severity classification to reduce unnecessary interruptions while maintaining zero tolerance for genuinely critical hazards.

The solution was explicit severity tiers with different behavioral rules: critical hazards interrupt immediately with multimodal alerts (voice + visual flash + border pulse), high-severity issues trigger voice warnings, and medium/low observations are mentioned conversationally only if relevant. The model learned to distinguish between transient motion and sustained unsafe behavior through careful prompt engineering.

### 3. Making Voice Interaction Feel Natural, Not Annoying

A safety agent that constantly talks is one that gets turned off. The biggest design challenge was alert cadence—ensuring GuardianView speaks at the right moment with the right urgency. Too chatty and users ignore it; too quiet and hazards slip through.

The solution was severity-driven prompts combined with context awareness. The agent can escalate warnings if initial alerts are ignored, but it doesn't nag about minor issues. Critical hazards get immediate interruptions; minor observations wait for natural conversational pauses or are logged silently. This balance makes the agent feel like a helpful colleague rather than an annoying alarm system.

### 4. Grounding in Real Regulations Without Overwhelming the User

OSHA regulations are dense and technical. The challenge was surfacing the relevant standard when it matters ("That's an OSHA 1910.133 violation, eye protection is required for grinding operations") without turning every alert into a legal lecture.

Google Search integration provides grounding, but the prompt engineering ensures regulatory citations enhance rather than dominate the conversation. The agent mentions the specific regulation when it adds credibility or actionability, but focuses primarily on clear, actionable safety guidance in plain language.

### 5. Multilingual Accuracy for Safety-Critical Information

Implementing multilingual support wasn't just translation—it required ensuring safety-critical terminology remained accurate across 50+ languages while maintaining natural conversational flow.

The solution was dynamic prompt injection that explicitly separates technical terms (which may remain in English for precision, especially OSHA citations) from conversational speech (which must be in the user's language). This prevents dangerous mistranslations while making the agent accessible to non-English speakers. Testing across multiple languages revealed that Gemini's native multilingual capabilities are remarkably strong when given clear instructions.

### 6. Coordinating Multimodal Alerts

Synchronizing the visual flash overlay, border pulse animation, and voice alert required careful timing coordination between the backend event stream, frontend JavaScript DOM manipulation, and CSS animation triggers. Getting all three modalities to fire simultaneously for maximum impact took iterative refinement.

The final implementation uses event-driven architecture: when the backend detects a critical incident, it sends a single `safety_incident` message over the WebSocket. The frontend JavaScript immediately adds both the `flash-critical` and `alert-critical` CSS classes, triggering both animations simultaneously while the voice alert plays through the Web Audio API. The result is a perfectly synchronized multimodal warning.

### 7. Optimizing Detection Speed

Initially, the system sent a safety check every 2 frames (every 2 seconds at 1 FPS). This created a noticeable delay between hazard appearance and alert. Users reported the detection felt "a bit slow."

The solution was straightforward but impactful: change the safety check to run on every frame instead of every 2 frames. This cut detection latency in half (from 2 seconds to 1 second) at the cost of doubling API calls. For safety applications, the reduced latency is worth the increased cost—catching a critical hazard 1 second earlier can prevent injuries.

## What I Learned

**Gemini's Live API handles real-time multimodal streams remarkably well.** The latency between seeing a hazard and producing a spoken alert is fast enough to be genuinely useful in safety applications. The model can process video frames, maintain conversation context, search the web for regulations, and generate natural speech responses all within a latency budget that feels immediate to users.

**Building proactive AI agents within a conversational framework requires creative engineering.** The heartbeat pattern I developed could be a useful technique for anyone building monitoring or surveillance agents on top of conversational APIs. When the API doesn't natively support "push" notifications or proactive alerts, you can simulate it with regular lightweight prompts that invite the model to speak up when necessary.

**The configurable profile approach proved more powerful than expected.** Different environments don't just need different hazard lists; they need fundamentally different alert behaviors and severity thresholds. A kitchen's "critical" (knife injury, fire) looks different from a workshop's "critical" (missing eye protection, exposed wiring). The profile-as-data pattern makes the system highly extensible without code changes.

**Voice UX for safety applications is a distinct design problem.** Unlike chatbots where the user initiates, a safety copilot must initiate intelligently, and getting that wrong makes the tool useless. Context-aware severity escalation is critical. The agent needs to distinguish between "I should mention this" and "I must interrupt immediately," and the prompt engineering to achieve that distinction is subtle and domain-specific.

**Prompt-driven severity rules work surprisingly well for this use case.** While a hardcoded classifier would be more deterministic, the model follows severity instructions consistently enough to be practical, especially when the prompt is explicit about expected behavior for each level. The flexibility of prompt-based classification also makes it easier to tune behavior without retraining models.

**Client-side report generation with jsPDF eliminates backend complexity** and enables instant document creation without additional API calls or server-side processing. For an already complex real-time streaming application, keeping report generation client-side reduces operational costs and architectural complexity significantly.

**Responsive design for safety monitoring applications requires special consideration** for touch targets, viewport management, and ensuring critical information (alerts, HUD elements) remains accessible across all device sizes. Mobile workers need the same level of safety monitoring as desk-bound workers, and that requires thoughtful responsive CSS and touch-optimized interactions.

**Multimodal alerts are more effective than any single modality.** The combination of voice alert + visual flash + border pulse ensures users notice critical hazards even if they're not looking at the screen, have the sound muted, or are in a noisy environment. Redundancy in safety systems is a feature, not a bug.

**Optimizing for the right metrics matters.** Initially I focused on reducing API costs by checking safety every 2 frames. But for safety applications, detection latency is the critical metric, not cost per session. Halving the detection time from 2 seconds to 1 second meaningfully improves the system's effectiveness, and the increased API cost is justified.

## What's Next

**Persistent incident logging:** Connect the incident logging tool to Cloud Firestore for durable, queryable safety records across sessions and users. This enables longitudinal safety analysis, trend detection, and compliance auditing.

**Externalized profiles:** Move safety profiles from in-code dictionaries to Cloud Storage JSON files, enabling dynamic profile loading and user-created custom profiles without code deployments. Organizations could define their own environment-specific hazards and regulations.

**OSHA knowledge base:** Index OSHA regulations in Vertex AI Search for more precise, grounded safety citations without relying on general web search. This would provide faster, more accurate regulatory grounding.

**Wearable integration:** Support for smart glasses (Google Glass Enterprise, RealWear, Vuzix) and body-worn cameras for true hands-free operation in industrial settings. Workers could receive safety guidance through AR overlays while keeping both hands free.

**Multi-camera support:** Monitor an entire workshop or factory floor with multiple camera feeds, not just a single viewpoint. Aggregate hazard detection across all cameras with spatial awareness, tracking workers as they move between zones.

**Team dashboards:** Aggregate safety data across shifts and workers for safety managers. Real-time fleet monitoring, trend analysis, and team-wide safety score tracking. Identify training gaps and systemic hazards across the organization.

**Compliance reporting:** Auto-generate OSHA-compliant incident reports from logged events, including Form 300 (Log of Work-Related Injuries and Illnesses) export. Streamline regulatory reporting and reduce administrative burden.

**Incident replay and training:** Save video clips of detected incidents for post-session review and safety training materials. Build a library of real-world hazards from your organization for onboarding and continuous education.

**Integration with IoT sensors:** Combine camera vision with environmental sensors (gas detectors, temperature monitors, noise level meters) for comprehensive workspace monitoring. Vision + sensor fusion provides richer context for safety analysis.

**Custom hazard training:** Allow organizations to train custom hazard detection models on their specific workplace environments and equipment. Fine-tune the base model on organization-specific hazards that might not be covered by generic safety profiles.

## Sources

- U.S. Bureau of Labor Statistics, Census of Fatal Occupational Injuries 2024 — [bls.gov/iif](https://www.bls.gov/iif/)
- U.S. Bureau of Labor Statistics, Survey of Occupational Injuries and Illnesses 2024 — [bls.gov/news.release/osh.htm](https://www.bls.gov/news.release/osh.htm)
- AFL-CIO, "Death on the Job: The Toll of Neglect" 2025 — [aflcio.org/reports/dotj-2025](https://aflcio.org/reports/dotj-2025)
- OSHA — 29 CFR 1910 (General Industry), 29 CFR 1926 (Construction)
- Google Agent Development Kit (ADK) Documentation
- Gemini Live API Documentation
