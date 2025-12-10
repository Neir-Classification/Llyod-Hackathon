# Policy Assistant - React Version

Audio-reactive voice assistant with beautiful iridescent orb visualization.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the Python backend (in a separate terminal):**
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the React dev server:**
   ```bash
   npm run dev
   ```

4. **Open the app:**
   Navigate to `http://localhost:3000`

## Features

- ✨ **Audio-reactive iridescent orb** using WebGL shaders
- 🎤 **Voice input** with real-time audio visualization
- 🤖 **AI-powered responses** via RAG pipeline
- 💬 **Text chat** fallback option
- 🎨 **Apple-inspired design** with smooth animations
- 🌊 **Fluid morphing effects** based on voice frequency

## Tech Stack

- **Frontend:** React + TypeScript + Vite
- **Styling:** Tailwind CSS
- **Graphics:** OGL (WebGL library)
- **Backend:** FastAPI (Python) - see main.py

## How It Works

The orb reacts to your voice in real-time:
- **Volume** controls the scale and glow intensity
- **Frequency ranges** create organic blob shapes
- **Iridescent shader** creates a mesmerizing visual effect
- Audio analysis smooths the animation for fluid transitions
