# Vuwee-Gen — AI Script-to-Video Pipeline Manager

A modern, high-aesthetic web control panel and execution manager for the multi-model **Kaggle (2x T4) Script-to-Video Pipeline**.

---

## 🚀 Features

- **Multi-Model Pipeline Control**: Configure parameters for **Wan 2.1 (1.3B + CausVid LoRA)**, **LTX-Video**, **CogVideoX**, and **AnimateDiff**.
- **Visual Shot Types Supported**:
  - `wan`: AI video clip generation
  - `stock`: Pixabay / Pexels stock video search and download
  - `kenburns`: SDXL image generation with dynamic pan/zoom
  - `card`: Rich generated title/text cards
  - `screen`: Playwright automated web screen recording
- **Audio & Speech**: Kokoro TTS / edge-tts narration, faster-whisper timed captions burned via FFmpeg.
- **LLM Script Generator**: Generate multi-shot video plans directly via **OpenRouter**, **Google Gemini**, **Anthropic Claude**, or **Ollama**.
- **Interactive Shot Editor**: Add, edit, reorder, preview, and delete shots with real-time JSON sync.
- **Kaggle Kernel Runner**: Automated kernel push, run trigger, status polling, time-budget safety guards, and output artifact downloader.

---

## 🛠️ Project Structure

```text
vuwee-gen/
├── server/               # Express backend API for Kaggle & LLM proxying
│   ├── index.js          # API endpoints (Kaggle CLI wrapper, LLM generation, downloads)
│   └── package.json      # Server module config
├── src/                  # React + Vite frontend
│   ├── components/       # CredentialsSection, ConfigSection, ScriptSection, RunSection
│   ├── config.js         # Pipeline schema, defaults, presets, and constants
│   ├── api.js            # API client wrapper
│   ├── App.jsx           # Master UI container & state management
│   ├── index.css         # Dark-mode glassmorphic styling system
│   └── main.jsx          # React DOM entry point
├── downloads/            # Local directory for Kaggle video outputs
├── package.json          # Root scripts & dependencies
└── vite.config.js        # Vite config with API proxy to port 3001
```

---

## 🏁 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Application
To run both the Express backend and the Vite dev server simultaneously:
```bash
npm run dev:all
```

Or run them individually in separate terminals:
```bash
# Terminal 1: Backend API (port 3001)
npm run dev:server

# Terminal 2: Frontend (port 5173)
npm run dev
```

### 3. Open in Browser
Visit [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🔑 Configuration

1. **Credentials**:
   - Provide your **Kaggle Username** and **Kaggle API Key** (`kaggle.json`).
   - Add your API keys for OpenRouter, Gemini, Claude, Pixabay, or Pexels as needed.
2. **Pipeline Settings**:
   - Choose your video orientation (9:16 Shorts vs. 16:9 Landscape).
   - Set target duration, frame counts, and time budget guards.
3. **Generate or Write Script**:
   - Generate automated shots using your configured LLM provider, or paste custom shot JSON.
4. **Push & Monitor**:
   - Push the job to Kaggle, track progress, and download the final rendered `.mp4` video.
