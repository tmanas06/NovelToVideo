#!/bin/bash
set -e

PROJECT_ROOT="/home/manas/Desktop/StoryToReel"
FONTS_DIR="$PROJECT_ROOT/assets/fonts"
VOICES_DIR="$PROJECT_ROOT/assets/voices"
MUSIC_DIR="$PROJECT_ROOT/assets/music"

mkdir -p "$FONTS_DIR"
mkdir -p "$VOICES_DIR"
mkdir -p "$MUSIC_DIR"

echo "=== downloading fonts ==="
# Download Google Fonts - Inter Bold
if [ ! -f "$FONTS_DIR/Inter-Bold.ttf" ]; then
    echo "Downloading Inter-Bold.ttf..."
    curl -L -s -o "$FONTS_DIR/Inter-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf" || \
    wget -q -O "$FONTS_DIR/Inter-Bold.ttf" "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf" || \
    echo "⚠️ Failed to download Inter-Bold.ttf. Will use fallback Linux fonts."
else
    echo "Inter-Bold.ttf already exists."
fi

# Download Google Fonts - Inter Regular
if [ ! -f "$FONTS_DIR/Inter-Regular.ttf" ]; then
    echo "Downloading Inter-Regular.ttf..."
    curl -L -s -o "$FONTS_DIR/Inter-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf" || \
    wget -q -O "$FONTS_DIR/Inter-Regular.ttf" "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf" || \
    echo "⚠️ Failed to download Inter-Regular.ttf. Will use fallback Linux fonts."
else
    echo "Inter-Regular.ttf already exists."
fi

echo "=== downloading piper tts voice model ==="
# Piper TTS English Lessac model (ONNX + JSON)
if [ ! -f "$VOICES_DIR/en_US-lessac-medium.onnx" ] || [ $(stat -c%s "$VOICES_DIR/en_US-lessac-medium.onnx") -le 100 ]; then
    echo "Downloading en_US-lessac-medium.onnx voice model (~63MB)..."
    curl -L -o "$VOICES_DIR/en_US-lessac-medium.onnx" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || \
    wget -O "$VOICES_DIR/en_US-lessac-medium.onnx" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || \
    echo "⚠️ Failed to download voice model. Ensure you download it manually and place at assets/voices/en_US-lessac-medium.onnx"
else
    echo "en_US-lessac-medium.onnx already exists."
fi

if [ ! -f "$VOICES_DIR/en_US-lessac-medium.onnx.json" ] || [ $(stat -c%s "$VOICES_DIR/en_US-lessac-medium.onnx.json") -le 100 ]; then
    echo "Downloading en_US-lessac-medium.onnx.json voice config..."
    curl -L -s -o "$VOICES_DIR/en_US-lessac-medium.onnx.json" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || \
    wget -q -O "$VOICES_DIR/en_US-lessac-medium.onnx.json" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || \
    echo "⚠️ Failed to download voice config."
else
    echo "en_US-lessac-medium.onnx.json already exists."
fi

echo "=== downloading ambient background music ==="
# Synthesize a beautiful 30s ambient drone/beat using FFmpeg directly (bulletproof offline generation)
if [ ! -f "$MUSIC_DIR/ambient_loop.mp3" ] || [ $(stat -c%s "$MUSIC_DIR/ambient_loop.mp3") -le 2000 ]; then
    echo "Synthesizing a high-quality ambient loop track via FFmpeg..."
    ffmpeg -y -f lavfi -i "sine=frequency=110:duration=30" -af "apulsator=hz=0.5,lowpass=f=200,volume=0.5" -c:a libmp3lame -q:a 4 "$MUSIC_DIR/ambient_loop.mp3"
else
    echo "ambient_loop.mp3 already exists."
fi

echo "✅ Asset downloader script completed successfully."
