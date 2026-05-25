#!/bin/bash
# Script to generate placeholder background assets using ffmpeg

echo "Generating placeholder visual loop..."
ffmpeg -f lavfi -i testsrc2=size=1080x1920:rate=24:duration=10 -c:v libx264 -pix_fmt yuv420p -y assets/backgrounds/visuals/placeholder_visual.mp4

echo "Generating placeholder audio loop..."
ffmpeg -f lavfi -i anoisesrc=d=10:c=pink:r=44100 -c:a pcm_s16le -y assets/backgrounds/audio/placeholder_audio.wav

echo "Placeholders generated successfully."
