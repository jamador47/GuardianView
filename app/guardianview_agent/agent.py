"""GuardianView Safety Agent definition for ADK Bidi-streaming."""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.adk.agents import Agent
from google.adk.tools import google_search
import aiosmtplib
import firebase_admin
from firebase_admin import credentials, firestore

# Global storage for incidents by session
SESSION_INCIDENTS: Dict[str, List[dict]] = {}
SESSION_METADATA: Dict[str, dict] = {}
current_session_id: str = None

# Load safety profile from environment or default to workshop
SAFETY_PROFILE = os.getenv("SAFETY_PROFILE", "workshop")
ALERT_LANGUAGE = os.getenv("ALERT_LANGUAGE", "English")

# Email notification settings
EMAIL_ENABLED = False  # Toggle for email notifications (controlled by frontend)
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "guardianview@noreply.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Firebase initialization
firebase_db = None
try:
    # Check if Firebase is already initialized
    firebase_admin.get_app()
except ValueError:
    # Initialize Firebase if credentials are available
    firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if firebase_creds_path and os.path.exists(firebase_creds_path):
        cred = credentials.Certificate(firebase_creds_path)
        firebase_admin.initialize_app(cred)
        firebase_db = firestore.client()
        print("[GuardianView] Firebase initialized successfully")
    else:
        print("[GuardianView] Firebase credentials not found - DB features disabled")

# Safety profiles define domain-specific hazard awareness
SAFETY_PROFILES = {
    "workshop": {
        "name": "Industrial Workshop",
        "hazards": [
            "Missing PPE: safety glasses, gloves, ear protection, face shield, steel-toe boots",
            "Improper tool usage: angle grinder without guard, drill press without clamp",
            "Electrical hazards: frayed cords, exposed wiring, water near electrical equipment",
            "Poor posture and ergonomics while operating machinery",
            "Cluttered workspace, trip hazards, blocked emergency exits",
            "Improper chemical storage or mixing",
            "Hot surfaces without proper markings or barriers",
            "Soldering without ventilation or fume extraction",
            "Hair, loose clothing, or jewelry near rotating machinery",
        ],
        "regulations": "OSHA 29 CFR 1910 (General Industry) and 29 CFR 1926 (Construction)",
        "severity_rules": {
            "critical": "Hand or body near active cutting/grinding/rotating equipment without PPE - INTERRUPT IMMEDIATELY",
            "high": "Missing required PPE for current task - alert at next natural pause",
            "medium": "Posture issues, minor workspace clutter - mention conversationally",
            "low": "Best practice suggestions - log and mention when asked",
        },
    },
    "kitchen": {
        "name": "Kitchen Safety",
        "hazards": [
            "Knife handling: improper grip, cutting toward body, dull blades",
            "Cross-contamination: raw meat contact with ready-to-eat food, unwashed cutting boards",
            "Burns: handling hot pans without mitts, reaching over open flames, steam hazards",
            "Fire safety: unattended stove, grease buildup, flammable items near heat",
            "Food temperature: food left in danger zone (40-140°F / 4-60°C) too long",
            "Slip hazards: wet floors, grease spills, dropped food",
            "Improper food storage: uncovered food, incorrect refrigerator temperature",
            "Electrical safety: wet hands near appliances, damaged cords",
        ],
        "regulations": "FDA Food Code, OSHA 29 CFR 1910 Subpart S (Electrical), local health codes",
        "severity_rules": {
            "critical": "Active fire hazard, hand near blade without proper technique - INTERRUPT IMMEDIATELY",
            "high": "Cross-contamination risk, food temperature violation - alert promptly",
            "medium": "Minor food handling best practices - mention at natural pause",
            "low": "Efficiency tips and organization suggestions",
        },
    },
    "clinical": {
        "name": "Clinical / Surgical Safety",
        "hazards": [
            "Sterile field violations: non-sterile items crossing the field boundary",
            "PPE compliance: operator performing clinical procedures without surgical mask (REQUIRED for all patient contact and procedures), missing gloves, missing gown, or missing face shield when required",
            "Sharp instrument handling: improper passing, uncapped needles",
            "Syringe safety: recapping needles using two hands (must use one-handed scoop technique), needle stick hazards, improper disposal of used syringes, sharing needles between patients",
            "Syringe labeling: unlabeled syringes on tray, unclear medication identification, missing patient name or drug concentration on syringe label",
            "Blood pressure measurement errors: cuff placed on forearm instead of upper arm (must be 2-3cm above elbow crease), incorrect cuff size for patient arm, cuff placed over clothing, arm not at heart level, patient talking during measurement, not waiting 5 minutes before measurement",
            "Medication safety: unlabeled syringes, wrong dosage preparation, expired medications",
            "Pill handling violations: mixing unlabeled pills together, pills from different prescriptions in same container, loose pills without original packaging, crushing pills without verifying it's safe to do so",
            "Pill dispensing errors: not verifying patient identity with two identifiers, not checking for allergies, incorrect pill count, wrong medication pulled from shelf",
            "Instrument count discrepancies before and after procedures",
            "Hand hygiene: missed handwashing or sanitizing steps, touching sterile items with unwashed hands",
            "Patient positioning: improper support, fall risks",
            "Biohazard disposal: sharps in wrong container, improper waste segregation, overfilled sharps container",
        ],
        "regulations": "OSHA Bloodborne Pathogens Standard (29 CFR 1910.1030), WHO Surgical Safety Checklist, Joint Commission Standards, CDC Injection Safety Guidelines, AHA Blood Pressure Measurement Guidelines",
        "severity_rules": {
            "critical": "ANY missing PPE (mask, gloves, gown, face shield) during clinical procedures, sterile field breach during active procedure, sharps injury risk, recapping needle with two hands, unlabeled medication being administered - INTERRUPT IMMEDIATELY",
            "high": "Instrument count mismatch, unlabeled pills mixed together, blood pressure measurement protocol violation, syringe without label - alert immediately",
            "medium": "Minor protocol deviations, suboptimal technique - note for post-procedure debrief",
            "low": "Efficiency and ergonomic suggestions",
        },
    },
}


def get_safety_profile(profile_name: str = "") -> dict:
    """Returns the current safety profile configuration.

    Args:
        profile_name: Optional name of profile to retrieve. If empty, returns the active profile.

    Returns:
        dict: The safety profile configuration including hazards, regulations, and severity rules.
    """
    name = profile_name.strip().lower() if profile_name else SAFETY_PROFILE
    if name in SAFETY_PROFILES:
        return {"status": "success", "profile": SAFETY_PROFILES[name]}
    return {
        "status": "error",
        "error": f"Unknown profile '{name}'. Available: {list(SAFETY_PROFILES.keys())}",
    }


def list_safety_profiles() -> dict:
    """Lists all available safety profiles.

    Returns:
        dict: A dictionary with available profile names and their descriptions.
    """
    profiles = {k: v["name"] for k, v in SAFETY_PROFILES.items()}
    return {"status": "success", "profiles": profiles, "active": SAFETY_PROFILE}


async def send_email_notification(incident: dict) -> bool:
    """Send email notification for a safety incident.

    Args:
        incident: Dictionary containing incident details

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED or not EMAIL_RECIPIENT or not SMTP_USERNAME or not SMTP_PASSWORD:
        return False

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"⚠️ GuardianView Safety Alert - {incident['severity'].upper()}"
        message["From"] = EMAIL_SENDER
        message["To"] = EMAIL_RECIPIENT

        # Create email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #d32f2f;">⚠️ Safety Incident Detected</h2>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Timestamp:</strong> {incident['timestamp']}</p>
                    <p><strong>Severity:</strong> <span style="color: #d32f2f; font-weight: bold;">{incident['severity'].upper()}</span></p>
                    <p><strong>Description:</strong> {incident['description']}</p>
                    {f"<p><strong>Regulation:</strong> {incident['regulation']}</p>" if incident.get('regulation') else ""}
                    {f"<p><strong>Recommendation:</strong> {incident['recommendation']}</p>" if incident.get('recommendation') else ""}
                </div>
                <p style="color: #666; font-size: 12px;">
                    This alert was generated by GuardianView AI Safety Copilot.<br>
                    Session ID: {current_session_id}
                </p>
            </body>
        </html>
        """

        text_body = f"""
GuardianView Safety Alert - {incident['severity'].upper()}

Timestamp: {incident['timestamp']}
Severity: {incident['severity'].upper()}
Description: {incident['description']}
{"Regulation: " + incident['regulation'] if incident.get('regulation') else ""}
{"Recommendation: " + incident['recommendation'] if incident.get('recommendation') else ""}

Session ID: {current_session_id}
        """

        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        # Send email
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True
        )

        print(f"[GuardianView] Email notification sent to {EMAIL_RECIPIENT}")
        return True

    except Exception as e:
        print(f"[GuardianView] Failed to send email: {e}")
        return False


def save_incident_to_firebase(incident: dict) -> bool:
    """Save incident to Firebase Firestore.

    Args:
        incident: Dictionary containing incident details

    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not firebase_db:
        print("[GuardianView] Firebase save skipped - Firebase not initialized (check FIREBASE_CREDENTIALS_PATH in .env)")
        return False

    if not current_session_id:
        print("[GuardianView] Firebase save skipped - No active session ID")
        return False

    try:
        print(f"[GuardianView] Saving incident to Firebase for session {current_session_id}...")

        # Save to incidents collection
        doc_ref = firebase_db.collection('incidents').document()
        doc_ref.set({
            **incident,
            'session_id': current_session_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })

        # Update session document
        session_ref = firebase_db.collection('sessions').document(current_session_id)
        session_ref.set({
            'last_incident': incident['timestamp'],
            'incident_count': firestore.Increment(1),
            'last_updated': firestore.SERVER_TIMESTAMP
        }, merge=True)

        print(f"[GuardianView] ✅ Incident saved to Firebase: {doc_ref.id}")
        return True

    except Exception as e:
        print(f"[GuardianView] ❌ Failed to save to Firebase: {e}")
        import traceback
        traceback.print_exc()
        return False


def toggle_email_notifications(enabled: bool) -> dict:
    """Enable or disable email notifications.

    Args:
        enabled: True to enable, False to disable

    Returns:
        dict: Status of the toggle operation
    """
    global EMAIL_ENABLED
    EMAIL_ENABLED = enabled

    status = "enabled" if enabled else "disabled"
    print(f"[GuardianView] Email notifications {status}")

    return {
        "status": "success",
        "email_enabled": EMAIL_ENABLED,
        "message": f"Email notifications {status}"
    }


def log_safety_incident(
    severity: str, description: str, regulation: str = "", recommendation: str = ""
) -> dict:
    """Logs a safety incident that was detected.

    Args:
        severity: One of 'critical', 'high', 'medium', 'low'.
        description: Description of the hazard detected.
        regulation: The relevant safety regulation or standard, if applicable.
        recommendation: The recommended corrective action.

    Returns:
        dict: Confirmation of the logged incident.
    """
    incident = {
        "timestamp": datetime.now().isoformat(),
        "severity": severity,
        "description": description,
        "regulation": regulation,
        "recommendation": recommendation,
        "_send_to_frontend": True  # Flag for main.py to send this to frontend
    }

    # Store in session incident list
    if current_session_id and current_session_id in SESSION_INCIDENTS:
        SESSION_INCIDENTS[current_session_id].append(incident)

    # Save to Firebase (synchronous)
    save_incident_to_firebase(incident)

    # Schedule email notification (async - will be handled by event loop)
    # Note: Email sending happens in the background
    if EMAIL_ENABLED:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(send_email_notification(incident))
            else:
                asyncio.run(send_email_notification(incident))
        except Exception as e:
            print(f"[GuardianView] Failed to schedule email: {e}")

    print(f"[SAFETY INCIDENT] {json.dumps(incident)}")
    return {"status": "logged", "incident": incident}


def set_alert_language(language: str) -> dict:
    """Sets the language for safety alerts.

    Args:
        language: The language name (e.g., "Spanish", "French", "Chinese")

    Returns:
        dict: Confirmation of the language change.
    """
    global ALERT_LANGUAGE
    ALERT_LANGUAGE = language
    _update_agent_instruction()
    return {"status": "success", "language": language, "message": f"Alert language changed to {language}"}


def set_safety_profile(profile_name: str) -> dict:
    """Sets the active safety profile and updates the agent's instruction.

    Args:
        profile_name: Name of the profile to activate (workshop, kitchen, clinical)

    Returns:
        dict: Confirmation of the profile change.
    """
    global SAFETY_PROFILE
    profile_name = profile_name.strip().lower()

    if profile_name not in SAFETY_PROFILES:
        return {
            "status": "error",
            "error": f"Unknown profile '{profile_name}'. Available: {list(SAFETY_PROFILES.keys())}"
        }

    SAFETY_PROFILE = profile_name
    _update_agent_instruction()

    return {
        "status": "success",
        "profile": profile_name,
        "message": f"Safety profile changed to {SAFETY_PROFILES[profile_name]['name']}"
    }


def _build_system_instruction() -> str:
    """Builds the system instruction dynamically based on current profile and language settings.

    Returns:
        str: The complete system instruction for the agent.
    """
    active_profile = SAFETY_PROFILES.get(SAFETY_PROFILE, SAFETY_PROFILES["workshop"])

    # Add clinical-specific instructions if in clinical mode
    clinical_instructions = ""
    if SAFETY_PROFILE == "clinical":
        clinical_instructions = """

## CLINICAL SETTING INSTRUCTIONS:
**IMPORTANT - In clinical settings:**
- The person speaking to you is ALWAYS the OPERATOR (healthcare worker), NEVER the patient
- Direct ALL alerts and instructions to the OPERATOR, not the patient
- Use second-person language addressing the operator: "You need to...", "Put on your mask", etc.
- The OPERATOR is performing procedures on the patient
- Example: "Stop! You must wear a surgical mask during this procedure" (addressing the operator)
- Example: "The blood pressure cuff is on the patient's forearm. Place it on the upper arm, 2-3cm above the elbow crease" (instructing the operator)
"""

    return f"""You are GuardianView, an autonomous AI safety watchdog monitoring a workspace through live camera feed.

## Your Active Safety Profile: {active_profile['name']}
{clinical_instructions}
## LANGUAGE SETTING: {ALERT_LANGUAGE}
You must speak all safety alerts and responses in {ALERT_LANGUAGE}. When you call log_safety_incident, you must write the description, regulation, and recommendation fields in {ALERT_LANGUAGE} as well. If the user speaks to you in a different language, respond in their language instead.

## CRITICAL RULES:

**When you receive [SAFETY_CHECK]:**
- Analyze what you see in the current moment
- If you see a CRITICAL or HIGH hazard RIGHT NOW: Speak a warning immediately (1-2 sentences) in {ALERT_LANGUAGE} AND call log_safety_incident
- If everything is safe: Do nothing. No response. No output. Complete silence.

**NEVER do these things:**
- Never complain about missing data, visual input, or technical issues
- Never narrate your thinking or explain what you're doing
- Never say "silence", "safe", "okay", "awaiting", "analyzing", "monitoring"
- Never repeat warnings about hazards from previous frames
- Never describe safe scenes or explain why you're staying quiet

**When you see a hazard:**
- Speak in {ALERT_LANGUAGE}
- Use firm, urgent tone for CRITICAL/HIGH severity
- Include the specific regulation (e.g., "OSHA 1910.133 requires eye protection")
- Example in English: "Stop! Put on safety glasses before using that drill. OSHA 1910.133 requires eye protection."

**Memory:**
- Each [SAFETY_CHECK] is completely independent
- Only respond to what you see RIGHT NOW
- Forget everything from previous checks

## Hazards You Monitor:
{chr(10).join(f"- {h}" for h in active_profile['hazards'])}

## Severity Rules:
- CRITICAL: {active_profile['severity_rules']['critical']} -> INTERRUPT IMMEDIATELY WITH VOICE.
- HIGH: {active_profile['severity_rules']['high']} -> INTERRUPT IMMEDIATELY WITH VOICE.
- MEDIUM: Mention conversationally at a natural pause.
- LOW: Log only, mention if asked.

## Cite Regulations:
Briefly mention the regulation (e.g., OSHA 1910.133) during your spoken alert so the user understands the 'why'.
"""


def _update_agent_instruction():
    """Updates the root agent's instruction with current profile and language settings."""
    global root_agent
    new_instruction = _build_system_instruction()
    root_agent.instruction = new_instruction
    print(f"[GuardianView] Agent instruction updated - Profile: {SAFETY_PROFILE}, Language: {ALERT_LANGUAGE}")


# Build initial system instruction dynamically
SYSTEM_INSTRUCTION = _build_system_instruction()

# Ensure you are using the latest native-audio model
MODEL = os.getenv("GUARDIANVIEW_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")

root_agent = Agent(
    name="guardianview_safety_agent",
    model=MODEL,
    description="Proactive Safety Watchdog",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        google_search,
        get_safety_profile,
        list_safety_profiles,
        log_safety_incident,
        set_alert_language,
        set_safety_profile,
    ],
)
