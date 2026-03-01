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
    
    frameInterval = setInterval(() => {
        if (!isCameraOn || !isConnected || !websocket) return;
        
        ctx.drawImage(videoPreview, 0, 0, 640, 480);
        canvas.toBlob((blob) => {
            if (!blob) return;
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(",")[1];
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({ type: "image", data: base64 }));
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
        
        // Use ScriptProcessor as fallback (AudioWorklet requires HTTPS)
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
            if (!isConnected || !websocket) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
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
    
    // ✅ ADD THIS: Periodic ping to keep agent analyzing the camera feed
    window._pingInterval = setInterval(() => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({ type: "text", text: "." }));
        }
    }, 1000);
    
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
    clearInterval(window._pingInterval); // ✅ ADD THIS
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
            playAudioChunk(msg.data);
            break;
            
        case "text":
            addAgentMessage(msg.data);
            break;
            
        case "output_transcription":
            addAgentMessage(msg.data);
            break;
            
        case "input_transcription":
            addUserMessage(msg.data);
            break;
            
        case "turn_complete":
            // Turn is done, agent finished speaking
            break;
            
        case "interrupted":
            clearPlaybackQueue();
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

function addAgentMessage(text) {
    // Accumulate streaming text into current message
    if (!currentAgentMessage) {
        currentAgentMessage = document.createElement("div");
        currentAgentMessage.className = "agent-message";
        transcriptLog.appendChild(currentAgentMessage);
    }
    currentAgentMessage.textContent += text;
    transcriptLog.scrollTop = transcriptLog.scrollHeight;
    
    // Detect severity keywords for alert banner
    const lower = text.toLowerCase();
    if (lower.includes("danger") || lower.includes("stop") || lower.includes("warning") || lower.includes("critical")) {
        showAlert(text, "critical");
    } else if (lower.includes("caution") || lower.includes("careful") || lower.includes("hazard")) {
        showAlert(text, "high");
    }
    
    // Reset after a pause
    clearTimeout(currentAgentMessage._resetTimer);
    currentAgentMessage._resetTimer = setTimeout(() => {
        currentAgentMessage = null;
    }, 2000);
}

function showAlert(text, severity) {
    alertBanner.style.display = "flex";
    alertBanner.className = "alert-banner " + severity;
    alertText.textContent = text.substring(0, 120);
    
    // Auto-hide after 8 seconds
    clearTimeout(alertBanner._hideTimer);
    alertBanner._hideTimer = setTimeout(() => {
        alertBanner.style.display = "none";
    }, 8000);
    
    // Add to incident log
    addIncident(severity, text);
}

function addIncident(severity, description) {
    const noIncidents = incidentLog.querySelector(".no-incidents");
    if (noIncidents) noIncidents.remove();
    
    const time = new Date().toLocaleTimeString();
    const div = document.createElement("div");
    div.className = "incident-item " + severity;
    div.innerHTML = `<strong>${time}</strong> ${description.substring(0, 80)}`;
    incidentLog.prepend(div);
}
