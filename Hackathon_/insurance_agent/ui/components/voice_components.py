"""
Voice-enabled UI components for web interface.
"""
import base64
import json
from typing import Optional, Callable
import asyncio

VOICE_RECORDER_HTML = """
<div id="voice-recorder" style="padding: 20px; text-align: center;">
    <button id="record-btn" onclick="toggleRecording()" style="
        padding: 20px 40px;
        font-size: 18px;
        border-radius: 50px;
        border: none;
        cursor: pointer;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    ">
        🎤 Hold to Speak
    </button>
    
    <div id="status" style="margin-top: 15px; color: #666; font-size: 14px;">
        Click and hold to record your question
    </div>
    
    <div id="waveform" style="
        height: 50px;
        margin: 15px auto;
        max-width: 300px;
        display: none;
    ">
        <canvas id="waveform-canvas" width="300" height="50"></canvas>
    </div>
</div>

<script>
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;
let analyser = null;

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Set up audio context for visualization
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        
        // Set up media recorder
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendAudioToServer(audioBlob);
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        // Update UI
        document.getElementById('record-btn').textContent = '🔴 Recording...';
        document.getElementById('record-btn').style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        document.getElementById('status').textContent = 'Release to send';
        document.getElementById('waveform').style.display = 'block';
        
        // Start visualization
        visualize();
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        document.getElementById('status').textContent = 'Error: ' + error.message;
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    isRecording = false;
    
    // Update UI
    document.getElementById('record-btn').textContent = '🎤 Hold to Speak';
    document.getElementById('record-btn').style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    document.getElementById('status').textContent = 'Processing...';
    document.getElementById('waveform').style.display = 'none';
}

function visualize() {
    if (!isRecording) return;
    
    const canvas = document.getElementById('waveform-canvas');
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        if (!isRecording) return;
        
        requestAnimationFrame(draw);
        
        analyser.getByteTimeDomainData(dataArray);
        
        ctx.fillStyle = '#f3f4f6';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#667eea';
        ctx.beginPath();
        
        const sliceWidth = canvas.width / bufferLength;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * canvas.height / 2;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }
    
    draw();
}

async function sendAudioToServer(audioBlob) {
    // Convert to base64
    const reader = new FileReader();
    reader.onloadend = async () => {
        const base64Audio = reader.result.split(',')[1];
        
        // Send to parent Streamlit
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({
                type: 'audio_data',
                audio: base64Audio
            }, '*');
        }
        
        document.getElementById('status').textContent = 'Click and hold to record your question';
    };
    reader.readAsDataURL(audioBlob);
}
</script>
"""


AUDIO_PLAYER_HTML = """
<div id="audio-player" style="padding: 10px;">
    <audio id="response-audio" controls style="width: 100%; display: none;">
        Your browser does not support the audio element.
    </audio>
</div>

<script>
function playAudio(base64Audio) {
    const audio = document.getElementById('response-audio');
    audio.src = 'data:audio/mp3;base64,' + base64Audio;
    audio.style.display = 'block';
    audio.play();
}

// Listen for audio from parent
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'play_audio') {
        playAudio(event.data.audio);
    }
});
</script>
"""


THOUGHT_VISUALIZATION_HTML = """
<div id="thought-viz" style="font-family: monospace; font-size: 13px;">
    <style>
        .thought-item {
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 6px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .thought-type { font-weight: bold; margin-right: 8px; }
        
        .thought { background: #fef3c7; border-left: 3px solid #f59e0b; }
        .action { background: #fee2e2; border-left: 3px solid #ef4444; }
        .observation { background: #dcfce7; border-left: 3px solid #22c55e; }
        .response { background: #dbeafe; border-left: 3px solid #3b82f6; }
    </style>
    
    <div id="thoughts-container"></div>
</div>

<script>
function addThought(type, content) {
    const container = document.getElementById('thoughts-container');
    const item = document.createElement('div');
    item.className = 'thought-item ' + type;
    
    const icons = {
        'thought': '💭',
        'action': '🔧',
        'observation': '👁️',
        'response': '💬'
    };
    
    item.innerHTML = `
        <span class="thought-type">${icons[type] || '📝'} ${type.toUpperCase()}</span>
        <span>${content}</span>
    `;
    
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

function clearThoughts() {
    document.getElementById('thoughts-container').innerHTML = '';
}

// Listen for thoughts from parent
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'add_thought') {
        addThought(event.data.thoughtType, event.data.content);
    } else if (event.data && event.data.type === 'clear_thoughts') {
        clearThoughts();
    }
});
</script>
"""


def get_voice_recorder_component() -> str:
    """Get the voice recorder HTML component."""
    return VOICE_RECORDER_HTML


def get_audio_player_component() -> str:
    """Get the audio player HTML component."""
    return AUDIO_PLAYER_HTML


def get_thought_visualization_component() -> str:
    """Get the thought visualization HTML component."""
    return THOUGHT_VISUALIZATION_HTML


def create_streamlit_voice_component():
    """
    Create a Streamlit component for voice interaction.
    Use with st.components.v1.html()
    """
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body>
        {VOICE_RECORDER_HTML}
        {AUDIO_PLAYER_HTML}
    </body>
    </html>
    """
    return full_html
