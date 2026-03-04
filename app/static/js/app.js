/**
 * GuardianView - AI Safety Copilot
 * Main application JavaScript for WebSocket bidi-streaming with ADK
 */

// --- State ---
let websocket = null;
let mediaStream = null;
let audioContext = null;
let audioWorkletNode = null;
let isRecordingAudio = false;
let isCameraOn = false;
let isConnected = false;
let frameInterval = null;
let framesPerSecond = 1;

const userId = "guardianview-user";
const sessionId = "gv-session-" + Math.random().toString(36).substring(7);

// --- DOM Elements ---
const videoPreview = document.getElementById("videoPreview");
const videoOverlay = document.getElementById("videoOverlay");
const alertBanner = document.getElementById("alertBanner");
const alertText = document.getElementById("alertText");
const transcriptLog = document.getElementById("transcriptLog");
const incidentLog = document.getElementById("incidentLog");
const statusDot = document.querySelector(".status-dot");
const statusText = document.querySelector(".status-text");
const textInput = document.getElementById("textInput");
const btnCamera = document.getElementById("btnCamera");
const btnMic = document.getElementById("btnMic");
const btnConnect = document.getElementById("btnConnect");
const btnSend = document.getElementById("btnSend");

// --- Audio Playback ---
let playbackAudioContext = null;
let playbackQueue = [];
let isPlaying = false;

function initPlaybackAudio() {
    if (!playbackAudioContext) {
        playbackAudioContext = new AudioContext({ sampleRate: 24000 });
    }
}

async function playAudioChunk(base64Data) {
    initPlaybackAudio();
    
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Convert PCM16 to Float32
    const pcm16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768.0;
    }
    
    const audioBuffer = playbackAudioContext.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);
    
    playbackQueue.push(audioBuffer);
    if (!isPlaying) {
        playNextChunk();
    }
}

function playNextChunk() {
    if (playbackQueue.length === 0) {
        isPlaying = false;
        return;
    }
    
    isPlaying = true;
    const buffer = playbackQueue.shift();
    const source = playbackAudioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(playbackAudioContext.destination);
    source.onended = playNextChunk;
    source.start();
}

function clearPlaybackQueue() {
    playbackQueue = [];
    isPlaying = false;
}

// --- Camera ---

async function toggleCamera() {
    if (isCameraOn) {
        stopCamera();
    } else {
        await startCamera();
    }
}

async function startCamera() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: "environment" },
            audio: false,
        });
        videoPreview.srcObject = mediaStream;
        videoOverlay.classList.add("hidden");
        isCameraOn = true;
        btnCamera.textContent = "📷 Stop Camera";
        btnCamera.classList.add("active");
        btnMic.disabled = false;
        btnConnect.disabled = false;
        addSystemMessage("Camera started. You can now connect to begin monitoring.");
    } catch (err) {
        addSystemMessage("Error accessing camera: " + err.message);
    }
}

function stopCamera() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }
    videoPreview.srcObject = null;
    videoOverlay.classList.remove("hidden");
    isCameraOn = false;
    btnCamera.textContent = "📷 Start Camera";
    btnCamera.classList.remove("active");
    
    if (isConnected) {
        disconnectWebSocket();
    }
    stopFrameCapture();
    btnMic.disabled = true;
    btnConnect.disabled = true;
}

// --- Frame Capture (send video frames to server) ---

function startFrameCapture() {
    if (frameInterval) return;

    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");

    const intervalMs = 1000 / framesPerSecond;

    let frameCount = 0;

    frameInterval = setInterval(() => {
        if (!isCameraOn || !isConnected || !websocket) return;

        ctx.drawImage(videoPreview, 0, 0, 640, 480);
        canvas.toBlob((blob) => {
            if (!blob) return;
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(",")[1];
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    // Always send the camera frame
                    websocket.send(JSON.stringify({ type: "image", data: base64 }));

                    // Every 2 frames (2 seconds at 1fps), trigger a safety check
                    frameCount++;
                    console.log(`[GuardianView] Frame count: ${frameCount}`);
                    if (frameCount >= 2) {
                        frameCount = 0;
                        console.log("[GuardianView] Sending [SAFETY_CHECK] prompt");
                        websocket.send(JSON.stringify({
                            type: "text",
                            text: "[SAFETY_CHECK]"
                        }));
                    }
                }
            };
            reader.readAsDataURL(blob);
        }, "image/jpeg", 0.7);
    }, intervalMs);
}

function stopFrameCapture() {
    if (frameInterval) {
        clearInterval(frameInterval);
        frameInterval = null;
    }
}

function updateFps() {
    const slider = document.getElementById("fpsSlider");
    framesPerSecond = parseFloat(slider.value);
    document.getElementById("fpsValue").textContent = framesPerSecond;
    
    if (frameInterval) {
        stopFrameCapture();
        startFrameCapture();
    }
}

// --- Microphone ---

async function toggleMicrophone() {
    if (isRecordingAudio) {
        stopMicrophone();
    } else {
        await startMicrophone();
    }
}

async function startMicrophone() {
    try {
        const audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
        });

        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(audioStream);

        // Interrupt detection state
        let consecutiveHighAudioChunks = 0;
        const CHUNKS_REQUIRED_FOR_INTERRUPT = 3; // Require 3 consecutive chunks ~300-400ms of speech
        const AUDIO_THRESHOLD = 5; // Increased threshold to avoid noise

        // Use ScriptProcessor as fallback (AudioWorklet requires HTTPS)
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
            if (!isConnected || !websocket) return;

            const inputData = e.inputBuffer.getChannelData(0);

            // Calculate audio level to detect if user is speaking
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
            }
            const rms = Math.sqrt(sum / inputData.length);
            const audioLevel = rms * 100; // Scale to 0-100

            // Require sustained speech before interrupting (prevent false positives from bumps/noise)
            if (isPlaying && audioLevel > AUDIO_THRESHOLD) {
                consecutiveHighAudioChunks++;
                if (consecutiveHighAudioChunks >= CHUNKS_REQUIRED_FOR_INTERRUPT) {
                    console.log(`[GuardianView] Interrupt triggered - completely discarding agent's message`);

                    // Clear audio playback immediately
                    clearPlaybackQueue();

                    // Clear the agent's text message to prevent resuming
                    if (currentAgentMessage) {
                        currentAgentMessage.remove();
                        currentAgentMessage = null;
                    }
                    agentIsActuallySpeaking = false;

                    // Send interrupt to backend
                    if (websocket && websocket.readyState === WebSocket.OPEN) {
                        websocket.send(JSON.stringify({ type: "interrupt" }));
                    }

                    consecutiveHighAudioChunks = 0; // Reset after interrupt
                }
            } else {
                // Reset counter if audio drops below threshold or agent not playing
                consecutiveHighAudioChunks = 0;
            }

            // Convert Float32 to PCM16
            const pcm16 = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
            }

            const base64 = arrayBufferToBase64(pcm16.buffer);
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({ type: "audio", data: base64 }));
            }
        };
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        isRecordingAudio = true;
        btnMic.textContent = "🎤 Stop Mic";
        btnMic.classList.add("active");
        addSystemMessage("Microphone active. You can speak to GuardianView.");
    } catch (err) {
        addSystemMessage("Error accessing microphone: " + err.message);
    }
}

function stopMicrophone() {
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    isRecordingAudio = false;
    btnMic.textContent = "🎤 Start Mic";
    btnMic.classList.remove("active");
}

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// --- WebSocket Connection ---

function toggleConnection() {
    if (isConnected) {
        disconnectWebSocket();
    } else {
        connectWebSocket();
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/${userId}/${sessionId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
    // Send initial configuration
    const config = {
        enable_proactivity: document.getElementById("enableProactivity").checked,
        enable_affective_dialog: document.getElementById("enableAffectiveDialog").checked,
    };
    websocket.send(JSON.stringify(config));

    setConnected(true);
    startFrameCapture();

    addSystemMessage("Connected to GuardianView. Safety monitoring is active.");
};
    
    websocket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleServerMessage(msg);
    };
    
    websocket.onclose = () => {
        setConnected(false);
        stopFrameCapture();
        addSystemMessage("Disconnected from GuardianView.");
    };
    
    websocket.onerror = (err) => {
        console.error("WebSocket error:", err);
        addSystemMessage("Connection error. Please try again.");
    };
}

function disconnectWebSocket() {
    if (websocket) {
        websocket.send(JSON.stringify({ type: "close" }));
        websocket.close();
        websocket = null;
    }
    setConnected(false);
    stopFrameCapture();
    clearPlaybackQueue();
}

function setConnected(connected) {
    isConnected = connected;
    statusDot.classList.toggle("connected", connected);
    statusText.textContent = connected ? "Monitoring" : "Disconnected";
    btnConnect.textContent = connected ? "🔗 Disconnect" : "🔗 Connect";
    btnConnect.classList.toggle("active", connected);
    textInput.disabled = !connected;
    btnSend.disabled = !connected;
}

// --- Message Handling ---

function handleServerMessage(msg) {
    switch (msg.type) {
        case "audio":
            console.log("[GuardianView] Received audio chunk - agent IS speaking");
            agentIsActuallySpeaking = true; // Agent is sending audio, so it's actually speaking
            playAudioChunk(msg.data);
            break;

        case "safety_incident":
            console.log("[GuardianView] 🚨 Received safety incident from backend:", msg.data);
            // Backend detected an incident - trigger alert immediately
            const incident = msg.data;
            const alertText = `${incident.description}\n\n${incident.recommendation}`.trim();
            showAlert(alertText, incident.severity || "high");
            break;

        case "text":
            console.log("[GuardianView] Received text message:", msg.data.substring(0, 50));
            addAgentMessage(msg.data);
            break;

        case "output_transcription":
            console.log("[GuardianView] Received output transcription:", msg.data.substring(0, 50));
            addAgentMessage(msg.data);
            break;

        case "input_transcription":
            addUserMessage(msg.data);
            break;

        case "turn_complete":
            console.log("[GuardianView] Turn complete - agentIsActuallySpeaking:", agentIsActuallySpeaking);
            // Turn is done, agent finished speaking
            break;

        case "interrupted":
            clearPlaybackQueue();
            // Clear the current agent message to prevent resuming old speech
            if (currentAgentMessage) {
                currentAgentMessage.remove();
                currentAgentMessage = null;
            }
            agentIsActuallySpeaking = false;
            break;
    }
}

// --- Text Input ---

function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text || !isConnected) return;
    
    websocket.send(JSON.stringify({ type: "text", text: text }));
    addUserMessage(text);
    textInput.value = "";
}

function handleTextKeypress(event) {
    if (event.key === "Enter") {
        sendTextMessage();
    }
}

// --- UI Updates ---

function addSystemMessage(text) {
    const div = document.createElement("div");
    div.className = "system-message";
    div.textContent = text;
    transcriptLog.appendChild(div);
    transcriptLog.scrollTop = transcriptLog.scrollHeight;
}

function addUserMessage(text) {
    const div = document.createElement("div");
    div.className = "user-message";
    div.textContent = text;
    transcriptLog.appendChild(div);
    transcriptLog.scrollTop = transcriptLog.scrollHeight;
}

let currentAgentMessage = null;
let agentIsActuallySpeaking = false; // Track if agent sent audio (is actually speaking)

function addAgentMessage(text) {
    console.log(`[GuardianView] addAgentMessage() called with text: "${text.substring(0, 100)}"`);
    console.log(`[GuardianView] agentIsActuallySpeaking flag: ${agentIsActuallySpeaking}`);

    // Filter out unwanted words and phrases
    const lower = text.toLowerCase();
    const unwantedPatterns = [
        "silence",
        "awaiting visual data",
        "awaiting visual input",
        "analyzing current frame",
        "analyzing immediate hazard",
        "analyzing the setting",
        "analyzing the hazard",
        "assuming implicit safety check",
        "analyzing implicit hazard",
        "i am still awaiting",
        "i'm currently focused on",
        "i'm analyzing",
        "no new image data",
        "waiting for visual data",
        "without a visual input",
        "i have nothing to process",
        "remaining silent",
        "adhering to rule",
        "assessing the immediate risk",
        "the user's positioning",
        "profile highlights this",
        "indicates a critical hazard"
    ];

    // Check if message contains any unwanted patterns
    for (const pattern of unwantedPatterns) {
        if (lower.includes(pattern)) {
            console.log("[GuardianView] ❌ FILTERED unwanted message:", text.substring(0, 100));
            return; // Don't display this message at all
        }
    }

    if (lower.trim() === "safe" || lower.trim() === "okay" || lower.trim() === "ok") {
        console.log("[GuardianView] ❌ FILTERED unwanted message:", text);
        return;
    }

    console.log("[GuardianView] ✅ Message NOT filtered - proceeding to display");

    // Accumulate streaming text into current message
    if (!currentAgentMessage) {
        currentAgentMessage = document.createElement("div");
        currentAgentMessage.className = "agent-message";
        currentAgentMessage._fullText = ""; // Track full accumulated text
        transcriptLog.appendChild(currentAgentMessage);
    }

    currentAgentMessage._fullText += text;
    currentAgentMessage.textContent = currentAgentMessage._fullText;
    transcriptLog.scrollTop = transcriptLog.scrollHeight;

    // Reset after a pause
    clearTimeout(currentAgentMessage._resetTimer);
    currentAgentMessage._resetTimer = setTimeout(() => {
        console.log(`[GuardianView] ⏰ 2-second timer fired - message complete`);
        console.log(`[GuardianView] Message text: ${currentAgentMessage ? currentAgentMessage._fullText.substring(0, 100) : 'null'}`);

        // NOTE: We DO NOT trigger alerts based on speech anymore
        // Alerts are ONLY triggered by backend safety_incident messages (from log_safety_incident tool)
        // This prevents verbose "thinking" messages from triggering false alerts

        currentAgentMessage = null;
        agentIsActuallySpeaking = false; // Reset speaking flag
        console.log(`[GuardianView] Reset flags - agentIsActuallySpeaking now: ${agentIsActuallySpeaking}`);
    }, 2000);
}

function summarizeText(text, maxSentences = 3) {
    // Split text into sentences
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];

    // Take only the first maxSentences
    const summary = sentences.slice(0, maxSentences).join(' ').trim();

    return summary;
}

function showAlert(text, severity) {
    console.log(`[GuardianView] showAlert() called - severity: ${severity}, text: ${text.substring(0, 50)}...`);
    alertBanner.style.display = "flex";
    alertBanner.className = "alert-banner " + severity;
    alertText.textContent = summarizeText(text, 3); // Limit to 3 sentences

    // Pause safety score recovery while alert is active
    pauseSafetyScoreRecovery();

    // Auto-hide after 8 seconds
    clearTimeout(alertBanner._hideTimer);
    alertBanner._hideTimer = setTimeout(() => {
        alertBanner.style.display = "none";
        console.log("[GuardianView] Alert cleared - resuming safety score recovery");
        // Resume safety score recovery when alert is cleared
        resumeSafetyScoreRecovery();
    }, 8000);

    // Add to incident log with summary
    addIncident(severity, summarizeText(text, 3));
}

function addIncident(severity, description) {
    console.log(`[GuardianView] addIncident() called - severity: ${severity}`);
    const noIncidents = incidentLog.querySelector(".no-incidents");
    if (noIncidents) noIncidents.remove();

    const time = new Date().toLocaleTimeString();
    const div = document.createElement("div");
    div.className = "incident-item " + severity;
    div.innerHTML = `<strong>${time}</strong> ${description}`;
    incidentLog.prepend(div);

    // CRITICAL: Every incident MUST trigger these UI updates
    console.log("[GuardianView] Incident logged - dropping safety score to 0");
    updateSafetyScoreUI(); // Drop score to 0
    triggerVideoBorderPulse(severity); // Pulse video border

    // Ensure alert banner is visible for this incident
    if (alertBanner.style.display !== "flex") {
        console.log("[GuardianView] Alert banner not visible - showing it now");
        alertBanner.style.display = "flex";
        alertBanner.className = "alert-banner " + severity;
        alertText.textContent = description;

        // Pause recovery and auto-hide
        pauseSafetyScoreRecovery();
        clearTimeout(alertBanner._hideTimer);
        alertBanner._hideTimer = setTimeout(() => {
            alertBanner.style.display = "none";
            console.log("[GuardianView] Alert cleared - resuming safety score recovery");
            resumeSafetyScoreRecovery();
        }, 8000);
    }
}

// ===== UI-ONLY ENHANCEMENTS =====

// --- Safety Score System (Visual Only) ---
let currentSafetyScore = 100;
let scoreRecoveryInterval = null;

function updateSafetyScoreUI() {
    console.log("[GuardianView] updateSafetyScoreUI() called - dropping score to 0");
    const scoreElement = document.getElementById("safetyScore");
    const gaugeFill = document.getElementById("gaugeFill");

    if (!scoreElement || !gaugeFill) {
        console.warn("[GuardianView] Safety score elements not found!");
        return;
    }

    // Drop safety score to 0 when any alert is triggered
    const previousScore = currentSafetyScore;
    currentSafetyScore = 0;
    console.log(`[GuardianView] Safety score: ${previousScore} → ${currentSafetyScore}`);

    // Pause any existing recovery to reset it
    pauseSafetyScoreRecovery();

    updateSafetyScoreDisplay();
}

function updateSafetyScoreDisplay() {
    const scoreElement = document.getElementById("safetyScore");
    const gaugeFill = document.getElementById("gaugeFill");

    if (!scoreElement || !gaugeFill) return;

    scoreElement.textContent = currentSafetyScore;
    gaugeFill.style.width = currentSafetyScore + "%";

    scoreElement.classList.remove("warning", "danger");
    gaugeFill.classList.remove("warning", "danger");

    if (currentSafetyScore < 50) {
        scoreElement.classList.add("danger");
        gaugeFill.classList.add("danger");
    } else if (currentSafetyScore < 75) {
        scoreElement.classList.add("warning");
        gaugeFill.classList.add("warning");
    }
}

function pauseSafetyScoreRecovery() {
    if (scoreRecoveryInterval) {
        clearInterval(scoreRecoveryInterval);
        scoreRecoveryInterval = null;
    }
}

function resumeSafetyScoreRecovery() {
    // Only start recovery if score is below 100 and not already running
    if (currentSafetyScore < 100 && !scoreRecoveryInterval) {
        scoreRecoveryInterval = setInterval(() => {
            if (currentSafetyScore < 100) {
                currentSafetyScore = Math.min(100, currentSafetyScore + 20);
                updateSafetyScoreDisplay();
            } else {
                clearInterval(scoreRecoveryInterval);
                scoreRecoveryInterval = null;
            }
        }, 5000); // Recover 20 points every 5 seconds
    }
}

// --- Video Border Pulse (Visual Only) ---
function triggerVideoBorderPulse(severity) {
    const videoContainer = document.getElementById("videoContainer");
    if (!videoContainer) return;

    videoContainer.classList.remove("alert-critical", "alert-high");

    if (severity === "critical") {
        videoContainer.classList.add("alert-critical");
    } else if (severity === "high") {
        videoContainer.classList.add("alert-high");
    }

    setTimeout(() => {
        videoContainer.classList.remove("alert-critical", "alert-high");
    }, 10000);
}

// --- Session Timer (Visual Only) ---
let sessionStartTime = null;
let sessionTimerInterval = null;

function startSessionTimerUI() {
    if (sessionTimerInterval) return;

    sessionStartTime = Date.now();
    const timerElement = document.getElementById("sessionTimer");
    if (!timerElement) return;

    sessionTimerInterval = setInterval(() => {
        const elapsed = Date.now() - sessionStartTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);

        timerElement.textContent =
            String(hours).padStart(2, "0") + ":" +
            String(minutes).padStart(2, "0") + ":" +
            String(seconds).padStart(2, "0");
    }, 1000);
}

function stopSessionTimerUI() {
    if (sessionTimerInterval) {
        clearInterval(sessionTimerInterval);
        sessionTimerInterval = null;
        sessionStartTime = null;
        const timerElement = document.getElementById("sessionTimer");
        if (timerElement) {
            timerElement.textContent = "00:00:00";
        }
    }
}

// Hook into existing setConnected to start/stop timer
const originalSetConnected = setConnected;
setConnected = function(connected) {
    originalSetConnected(connected);
    if (connected) {
        startSessionTimerUI();
    } else {
        stopSessionTimerUI();
    }
};

// --- Collapsible Sidebar Sections (Visual Only) ---
function toggleSidebarSection(header) {
    const content = header.nextElementSibling;
    header.classList.toggle("collapsed");
    content.classList.toggle("collapsed");
}

// --- Profile Badge Update (Visual Only) ---
function updateProfileBadge() {
    const select = document.getElementById("profileSelect");
    const profileIcon = document.querySelector(".profile-icon");
    const profileName = document.querySelector(".profile-name");

    if (!select || !profileIcon || !profileName) return;

    const profiles = {
        workshop: { icon: "🔧", name: "WORKSHOP SAFETY" },
        kitchen: { icon: "🍳", name: "KITCHEN SAFETY" },
        clinical: { icon: "🏥", name: "CLINICAL SAFETY" }
    };

    const selected = profiles[select.value];
    if (selected) {
        profileIcon.textContent = selected.icon;
        profileName.textContent = selected.name;
    }
}

// --- Update Button Labels for New UI Structure (Visual Only) ---
const originalStartCamera = startCamera;
startCamera = async function() {
    await originalStartCamera();
    const btnLabel = btnCamera.querySelector(".btn-label");
    if (btnLabel) {
        btnLabel.textContent = "Stop Camera";
    }
};

const originalStopCamera = stopCamera;
stopCamera = function() {
    originalStopCamera();
    const btnLabel = btnCamera.querySelector(".btn-label");
    if (btnLabel) {
        btnLabel.textContent = "Start Camera";
    }
};

const originalStartMicrophone = startMicrophone;
startMicrophone = async function() {
    await originalStartMicrophone();
    const btnLabel = btnMic.querySelector(".btn-label");
    if (btnLabel) {
        btnLabel.textContent = "Stop Mic";
    }
};

const originalStopMicrophone = stopMicrophone;
stopMicrophone = function() {
    originalStopMicrophone();
    const btnLabel = btnMic.querySelector(".btn-label");
    if (btnLabel) {
        btnLabel.textContent = "Start Mic";
    }
};
