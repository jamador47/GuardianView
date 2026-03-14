"""GuardianView - FastAPI server with ADK Bidi-streaming via WebSocket.

Real-time AI safety copilot that monitors workspaces through camera
and provides spoken safety alerts using Gemini Live API.
"""

import os
import sys

# Load .env FIRST — before any google.* imports
# This must happen before agent.py is imported since it triggers google.adk
from dotenv import load_dotenv

# Try multiple .env locations
env_loaded = load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
if not env_loaded:
    env_loaded = load_dotenv()  # fallback: current working directory

# Verify the key is loaded
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    print(f"[GuardianView] API key loaded (starts with {api_key[:10]}...)")
else:
    print("[GuardianView] WARNING: GOOGLE_API_KEY not found in environment!")
    print(f"[GuardianView] Searched .env at: {os.path.join(os.path.dirname(__file__), '.env')}")
    print(f"[GuardianView] CWD: {os.getcwd()}")

import asyncio
import base64
import json
import traceback
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fpdf import FPDF

from google.adk.agents import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types

from guardianview_agent import root_agent
from guardianview_agent import agent as guardianview_agent_module

# --- Application Setup ---

app = FastAPI(title="GuardianView Safety Copilot")

# Serve static files (frontend)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ADK Components (initialized once at startup) ---

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="guardianview",
    session_service=session_service,
)


def _is_native_audio_model(model_name: str) -> bool:
    """Check if the model supports native audio output."""
    native_keywords = ["native-audio", "native_audio"]
    return any(kw in model_name for kw in native_keywords)



def _build_run_config(
    enable_proactivity: bool = True,
    enable_affective_dialog: bool = False,
) -> RunConfig:
    """
    Builds RunConfig using the strict Google GenAI Enum types 
    to prevent Pydantic serialization warnings.
    """
    
    # FIX: Use the actual Enum object, not the string "AUDIO"
    # This matches the schema expected by the pydantic_serializer
    modalities = [types.Modality.AUDIO]

    config_kwargs = {
        "response_modalities": modalities,
        "streaming_mode": StreamingMode.BIDI,
        # Required for the Live API to handle audio-in and audio-out
        "output_audio_transcription": types.AudioTranscriptionConfig(),
        "input_audio_transcription": types.AudioTranscriptionConfig(),
        "realtime_input_config": types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
            )
        ),
    }

    # FIX: Only pass 'proactive_audio'. 
    # Do not include 'enabled': True as it is 'extra_forbidden' in this version.
    if enable_proactivity:
        try:
            config_kwargs["proactivity"] = {"proactive_audio": True}
            print("[GuardianView] Proactivity config: proactive_audio enabled")
        except Exception as e:
            print(f"[GuardianView] Proactivity config failed: {e}")

    run_config = RunConfig(**config_kwargs)
    print(f"[GuardianView] RunConfig built successfully: {run_config}")
    return run_config

# --- WebSocket Endpoint ---


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
):
    """Handle WebSocket connections for real-time bidi-streaming."""
    await websocket.accept()
    print(f"[GuardianView] Client connected: user={user_id}, session={session_id}")

    # Initialize session storage for incidents
    if session_id not in guardianview_agent_module.SESSION_INCIDENTS:
        guardianview_agent_module.SESSION_INCIDENTS[session_id] = []
        guardianview_agent_module.SESSION_METADATA[session_id] = {
            "start_time": datetime.now().isoformat(),
            "user_id": user_id,
            "safety_profile": guardianview_agent_module.SAFETY_PROFILE,
        }
        print(f"[GuardianView] Initialized session storage for {session_id}")

    # Set current session ID for the agent
    guardianview_agent_module.current_session_id = session_id

    # Create or resume session
    session = await session_service.get_session(
        app_name="guardianview", user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name="guardianview", user_id=user_id, session_id=session_id
        )

    # Create LiveRequestQueue for this connection
    live_request_queue = LiveRequestQueue()

    # Parse connection options
    try:
        initial_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        options = json.loads(initial_msg)
        enable_proactivity = options.get("enable_proactivity", True)
        enable_affective_dialog = options.get("enable_affective_dialog", False)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        enable_proactivity = True
        enable_affective_dialog = False

    run_config = _build_run_config(enable_proactivity, enable_affective_dialog)

    async def upstream_task():
        """Receive messages from client and forward to LiveRequestQueue."""
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "audio":
                    # Audio data from microphone (base64 encoded PCM16 @ 16kHz)
                    audio_data = base64.b64decode(msg["data"])
                    live_request_queue.send_realtime(
                        types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                    )

                elif msg_type == "image":
                    # Video frame from camera (base64 JPEG)
                    image_data = base64.b64decode(msg["data"])
                    # Send image as content (not realtime) so it persists in context for [SAFETY_CHECK]
                    live_request_queue.send_content(
                        types.Content(
                            role="user",
                            parts=[types.Part(inline_data=types.Blob(data=image_data, mime_type="image/jpeg"))],
                        )
                    )
                    print(f"[GuardianView] Sent image frame ({len(image_data)} bytes)")

                elif msg_type == "text":
                    # Text message
                    text_content = msg.get("text", "")
                    print(f"[GuardianView] Sending text prompt: {text_content[:50]}...")
                    live_request_queue.send_content(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=text_content)],
                        )
                    )

                elif msg_type == "interrupt":
                    # User interrupted - just clear frontend playback queue
                    # The continued audio stream will naturally interrupt the agent
                    print("[GuardianView] User interrupted agent (client-side handled)")

                elif msg_type == "toggle_email":
                    # Toggle email notifications
                    enabled = msg.get("enabled", False)
                    guardianview_agent_module.toggle_email_notifications(enabled)
                    print(f"[GuardianView] Email notifications {'enabled' if enabled else 'disabled'}")

                elif msg_type == "activity_start":
                    live_request_queue.send_activity_start()

                elif msg_type == "activity_end":
                    live_request_queue.send_activity_end()

                elif msg_type == "close":
                    break

        except WebSocketDisconnect:
            print(f"[GuardianView] Client disconnected (upstream): {user_id}")
        except Exception as e:
            print(f"[GuardianView] Upstream error: {e}")
            traceback.print_exc()
        finally:
            live_request_queue.close()

    async def downstream_task():
        """Receive events from ADK runner and forward to client."""
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Check for tool calls/results (safety incidents)
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Function response (tool result)
                        if hasattr(part, 'function_response') and part.function_response:
                            func_name = part.function_response.name
                            if func_name == "log_safety_incident":
                                result = part.function_response.response
                                if isinstance(result, dict) and "incident" in result:
                                    incident = result["incident"]
                                    print(f"[GuardianView] Sending safety incident to frontend: {incident}")
                                    await websocket.send_text(
                                        json.dumps({"type": "safety_incident", "data": incident})
                                    )

                        # Audio response
                        if part.inline_data and part.inline_data.mime_type and "audio" in part.inline_data.mime_type:
                            audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                            await websocket.send_text(
                                json.dumps({"type": "audio", "data": audio_b64})
                            )
                        # Text response
                        elif part.text:
                            print(f"[GuardianView] Agent response (text): {part.text[:100]}...")
                            await websocket.send_text(
                                json.dumps({"type": "text", "data": part.text})
                            )

                # Transcription events
                if hasattr(event, "server_content"):
                    sc = event.server_content
                    if sc and hasattr(sc, "output_transcription") and sc.output_transcription:
                        await websocket.send_text(
                            json.dumps({
                                "type": "output_transcription",
                                "data": sc.output_transcription.text,
                            })
                        )
                    if sc and hasattr(sc, "input_transcription") and sc.input_transcription:
                        await websocket.send_text(
                            json.dumps({
                                "type": "input_transcription",
                                "data": sc.input_transcription.text,
                            })
                        )

                # Turn completion
                if event.turn_complete:
                    await websocket.send_text(
                        json.dumps({"type": "turn_complete"})
                    )

                # Interruption
                if event.interrupted:
                    await websocket.send_text(
                        json.dumps({"type": "interrupted"})
                    )

        except WebSocketDisconnect:
            print(f"[GuardianView] Client disconnected (downstream): {user_id}")
        except Exception as e:
            print(f"[GuardianView] Downstream error: {e}")
            traceback.print_exc()

    # Run upstream and downstream concurrently
    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except Exception as e:
        print(f"[GuardianView] Session error: {e}")
    finally:
        print(f"[GuardianView] Session ended: user={user_id}, session={session_id}")


# --- PDF Report Generation ---


def generate_safety_report_pdf(session_id: str) -> bytes:
    """Generate a PDF safety report for the given session.

    Args:
        session_id: The session ID to generate the report for.

    Returns:
        bytes: The PDF file content as bytes.
    """
    # Get session data
    incidents = guardianview_agent_module.SESSION_INCIDENTS.get(session_id, [])
    metadata = guardianview_agent_module.SESSION_METADATA.get(session_id, {})

    # Calculate session duration
    start_time_str = metadata.get("start_time", datetime.now().isoformat())
    start_time = datetime.fromisoformat(start_time_str)
    duration = datetime.now() - start_time
    duration_str = f"{int(duration.total_seconds() // 3600):02d}:{int((duration.total_seconds() % 3600) // 60):02d}:{int(duration.total_seconds() % 60):02d}"

    # Count incidents by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for incident in incidents:
        severity = incident.get("severity", "low").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1

    # Create PDF with proper margins
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(left=20, top=20, right=20)

    # Header
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 15, "GuardianView Safety Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Session Metadata Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Session Information", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Session ID: {session_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Date: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Duration: {duration_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Safety Profile: {metadata.get('safety_profile', 'Unknown').upper()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Summary Statistics Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Summary Statistics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Total Incidents: {len(incidents)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Critical: {severity_counts['critical']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - High: {severity_counts['high']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Medium: {severity_counts['medium']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Low: {severity_counts['low']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Incident Table Section
    if incidents:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Incident Details", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for idx, incident in enumerate(incidents, 1):
            # Incident header
            severity = incident.get("severity", "low").upper()
            timestamp = incident.get("timestamp", "Unknown")
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, f"Incident #{idx} - {severity} - {time_str}", new_x="LMARGIN", new_y="NEXT")

            # Incident details
            pdf.set_font("Helvetica", "", 10)

            # Description
            description = incident.get("description", "No description")
            pdf.set_x(20)  # Reset X position to left margin
            pdf.multi_cell(0, 5, f"Description: {description}")

            # Regulation
            regulation = incident.get("regulation", "")
            if regulation:
                pdf.set_x(20)
                pdf.multi_cell(0, 5, f"Regulation: {regulation}")

            # Recommendation
            recommendation = incident.get("recommendation", "")
            if recommendation:
                pdf.set_x(20)
                pdf.multi_cell(0, 5, f"Recommendation: {recommendation}")

            pdf.ln(3)

    # Recommendations Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "General Recommendations", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    if severity_counts['critical'] > 0 or severity_counts['high'] > 0:
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Immediate action required: Address all CRITICAL and HIGH severity incidents before resuming work.")
    if severity_counts['medium'] > 0:
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Review and address MEDIUM severity incidents to improve workplace safety.")
    if len(incidents) == 0:
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Excellent! No safety incidents were detected during this session.")
    else:
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Continue monitoring your workspace for potential hazards.")
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Ensure all required PPE is worn and properly maintained.")
        pdf.set_x(20)
        pdf.multi_cell(0, 5, "- Review safety protocols regularly with your team.")

    # Footer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "GuardianView - AI Safety Copilot", align="C", new_x="LMARGIN", new_y="NEXT")

    # Return PDF as bytes
    return bytes(pdf.output())


@app.post("/api/report/{session_id}")
async def generate_report(session_id: str):
    """Generate and download a PDF safety report for the given session."""
    try:
        pdf_bytes = generate_safety_report_pdf(session_id)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=guardianview_report_{session_id}.pdf"
            }
        )
    except Exception as e:
        print(f"[GuardianView] Error generating report: {e}")
        traceback.print_exc()
        return {"error": str(e)}, 500


# --- Static Routes ---


@app.get("/")
async def serve_index():
    """Serve the main GuardianView UI."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "agent": "guardianview", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
