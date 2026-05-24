#!/bin/bash
set -e

PROJECT_ROOT="/home/manas/Desktop/StoryToReel"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "      StoryToReel AI - Setup Wizard       "
echo "=========================================="

# 1. Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Python virtual environment already exists."
fi

# 2. Activate virtualenv and install dependencies
echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing required Python dependencies..."
pip install -r backend/requirements.txt

# 3. Download public static assets
echo "Triggering asset downloader (fonts, voice models, music)..."
chmod +x scripts/download_assets.sh
./scripts/download_assets.sh

# 4. Check dependencies
echo "Checking local service health..."
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama CLI found."
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama local service is running."
        echo "Models downloaded:"
        curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | head -n 5
    else
        echo "⚠️ Ollama CLI is installed but service is NOT running."
        echo "Start it using: systemctl start ollama OR run 'ollama serve' in another window."
    fi
else
    echo "❌ Ollama is NOT installed. Install it from https://ollama.com/"
fi

if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg installation found."
else
    echo "❌ FFmpeg is NOT installed! Install it using: sudo apt update && sudo apt install -y ffmpeg"
fi

echo "=========================================="
echo "          Setup Completed!                "
echo "=========================================="
echo "To start the StoryToReel AI server:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run server: uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload"
echo "3. Open your browser and navigate to: http://localhost:8000"
echo "=========================================="
