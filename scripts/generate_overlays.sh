#!/bin/bash
# Script to generate stable procedural motion overlays

echo "Generating overlay: smoke..."
ffmpeg -f lavfi -i "nullsrc=s=1080x1920:r=24,geq=lum='(255*exp(-(X-W/2)^2/50000-(Y-H/2)^2/50000))':a=100" -t 5 -c:v libx264 -pix_fmt yuv420p -y assets/overlays/smoke.mp4

echo "Generating overlay: rain..."
ffmpeg -f lavfi -i "nullsrc=s=1080x1920:r=24,noise=c0s=10:c0f=t+n" -t 5 -c:v libx264 -pix_fmt yuv420p -y assets/overlays/rain.mp4

echo "Generating overlay: pulse..."
ffmpeg -f lavfi -i "testsrc2=size=1080x1920:rate=24:duration=5" -vf "colorchannelmixer=aa=0.3" -c:v libx264 -pix_fmt yuv420p -y assets/overlays/pulse.mp4

echo "Overlays generated successfully."
