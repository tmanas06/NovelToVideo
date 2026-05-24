# StoryToReel AI

An automated local-first content factory designed for Ubuntu to automatically convert stories, novel chapters, summaries, or custom text into engaging YouTube Shorts and Instagram Reels using offline AI pipelines.

---

## 🎬 Key Features

1. **Automated Story Splitting**: Utilizes local Ollama (`qwen2.5:3b` or `phi4-mini`) to extract key visual storyboard scenes.
2. **Art Preset prompts**: Expands scenes into detailed portrait stable diffusion prompts with predefined styles (Manga, Anime, Realistic, Fantasy, Dark, Cinematic).
3. **Camera Motion Engine**: Uses high-performance FFmpeg zoompan filters to generate Ken Burns camera panning, sliding, and zooming animations over static scene images.
4. **Offline Narration (Piper TTS)**: Lightweight, low-latency American accent voice narration (`en_US-lessac-medium`).
5. **Reels Styled Subtitles**: Burns high-visibility capital, bold, centered subtitles with customized outlines directly into the video.
6. **Background Music Overlay**: Seamlessly loops and ducks background ambient music under narration voice track.
7. **Fast Sequential background worker**: Sequential SQLite-backed worker queue prioritizing low RAM usage (only uses ~700MB) without redis/rabbitmq.
8. **Real-time monitor**: Dashboard SPA rendering percentage indicators, live generated preview cards, and active console log streams via Server-Sent Events (SSE).
9. **Batch Queue**: Supports submitting a bulk list of stories to process overnight or in a sequential pipeline.

---

## 🚀 One-Click Setup Guide

### 1. Prerequisites
Ensure your Ubuntu Linux machine has the following packages installed:
```bash
sudo apt update
sudo apt install -y ffmpeg curl python3 python3-pip python3-venv
```

Ensure Ollama is running and has Qwen downloaded:
```bash
ollama pull qwen2.5:3b
```

### 2. Install Project
Run the setup wizard which will build the virtual environment, install requirements, download the American English voice model (~80MB), download Inter fonts, and prepare ambient music loops:
```bash
cd /home/manas/Desktop/StoryToReel
chmod +x scripts/setup.sh
./scripts/setup.sh
```

---

## 🏁 Starting the Factory

To start the uvicorn development server:
```bash
source venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## ⚙️ Configuration & Hardware Optimizations

Since you are running on integrated Intel Iris Xe graphics (7GB RAM), configurations are optimized by default:
- **Low RAM sequential execution**: Background jobs are scheduled one-by-one sequentially to avoid RAM overflow.
- **Dynamic Image modes**: Local ComfyUI image generation (using Stable Diffusion 1.5) will run fine but is slow on CPUs (2-5 minutes per image). You can toggle **API Mode** or **Pillow Placeholder Mode** (gorgeous dark gradients) in the Settings tab to test/generate fast videos in seconds!
# NovelToVideo
