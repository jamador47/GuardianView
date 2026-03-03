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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from google.adk.agents import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types

from guardianview_agent import root_agent

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
                    live_request_queue.send_realtime(
                        types.Blob(data=image_data, mime_type="image/jpeg")
                    )

                elif msg_type == "text":
                    # Text message
                    live_request_queue.send_content(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=msg.get("text", ""))],
                        )
                    )

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
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Audio response
                        if part.inline_data and part.inline_data.mime_type and "audio" in part.inline_data.mime_type:
                            audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                            await websocket.send_text(
                                json.dumps({"type": "audio", "data": audio_b64})
                            )
                        # Text response
                        elif part.text:
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
