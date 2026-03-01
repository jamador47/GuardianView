"""GuardianView Safety Agent definition for ADK Bidi-streaming."""

import os
import json
from google.adk.agents import Agent
from google.adk.tools import google_search

# Load safety profile from environment or default to workshop
SAFETY_PROFILE = os.getenv("SAFETY_PROFILE", "workshop")

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
            "PPE compliance: missing gloves, mask, gown, or face shield",
            "Sharp instrument handling: improper passing, uncapped needles",
            "Instrument count discrepancies before and after procedures",
            "Hand hygiene: missed handwashing or sanitizing steps",
            "Medication safety: unlabeled syringes, wrong dosage preparation",
            "Patient positioning: improper support, fall risks",
            "Biohazard disposal: sharps in wrong container, improper waste segregation",
        ],
        "regulations": "OSHA Bloodborne Pathogens Standard (29 CFR 1910.1030), WHO Surgical Safety Checklist, Joint Commission Standards",
        "severity_rules": {
            "critical": "Sterile field breach during active procedure, sharps injury risk - INTERRUPT IMMEDIATELY",
            "high": "Missing PPE, instrument count mismatch - alert immediately",
            "medium": "Minor protocol deviations - note for post-procedure debrief",
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
        "severity": severity,
        "description": description,
        "regulation": regulation,
        "recommendation": recommendation,
    }
    # In production, this would write to Cloud Firestore
    print(f"[SAFETY INCIDENT] {json.dumps(incident)}")
    return {"status": "logged", "incident": incident}


# Load the active profile for the system instruction
active_profile = SAFETY_PROFILES.get(SAFETY_PROFILE, SAFETY_PROFILES["workshop"])

SYSTEM_INSTRUCTION = f"""You are GuardianView, an autonomous AI safety watchdog. 
Your role is to monitor the user's workspace via live video and provide INSTANT voice interventions.

## Your Active Safety Profile: {active_profile['name']}

## CRITICAL OPERATIONAL RULES:
1. **VOICE-FIRST INTERVENTION**: If you see a CRITICAL or HIGH hazard (like a drill without glasses), you must GENERATE SPOKEN AUDIO IMMEDIATELY. 
2. **DO NOT WAIT**: Do not wait for the user to speak. You have permission to interrupt the silence.
3. **TOOL USAGE**: When you detect an incident, call `log_safety_incident`, but you MUST ALSO speak the warning in the same turn.
4. **URGENCY**: For CRITICAL/HIGH hazards, use a firm, urgent tone. Example: "Stop! Put on your safety glasses before using that drill."

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

# Ensure you are using the latest native-audio model
MODEL = os.getenv("GUARDIANVIEW_MODEL", "gemini-2.0-flash-exp")

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
    ],
)
