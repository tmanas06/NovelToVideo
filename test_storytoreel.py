import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

async def test_all():
    print("====================================")
    print("  StoryToReel AI - Import Tester    ")
    print("====================================")
    
    try:
        from backend.config import get_settings
        settings = get_settings()
        print("✅ Settings Loaded successfully:")
        print(f"   Ollama: {settings.ollama_url} (model: {settings.ollama_model})")
        print(f"   ComfyUI: {settings.comfyui_url}")
        print(f"   TTS: {settings.tts_voice}")
    except Exception as e:
        print(f"❌ Settings load failed: {e}")
        return

    try:
        from backend.database.db import db_manager, list_projects
        await db_manager.init_db()
        projects = await list_projects()
        print(f"✅ DB initialized successfully. Found {len(projects)} existing projects.")
    except Exception as e:
        print(f"❌ DB initialization failed: {e}")
        return

    try:
        from backend.services.story_splitter import split_story
        print("🧪 Testing story splitting via Ollama...")
        scenes = await split_story("A boy enters a dark cave and finds a glowing sword.", num_scenes=2)
        print(f"✅ Story splitting works! Extracted {len(scenes)} scenes:")
        for s in scenes:
            print(f"   Scene {s['scene_number']}: Description: {s['description'][:50]}... | Narration: {s['narration_text']}")
    except Exception as e:
        print(f"❌ Story splitting failed: {e}")

    try:
        from backend.services.narration_generator import generate_narration
        print("🧪 Testing TTS generation...")
        out_wav = Path(__file__).parent / "temp" / "test_voice.wav"
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        res = await generate_narration("This is an offline system check.", out_wav)
        print(f"✅ TTS Generation works! File size: {out_wav.stat().st_size} bytes | Duration: {res['duration']}s")
        if out_wav.exists():
            out_wav.unlink()
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")

    try:
        from backend.services.subtitle_generator import generate_ass
        print("🧪 Testing Subtitle generation...")
        test_scenes = [
            {"scene_number": 1, "description": "test", "narration_text": "First test scene narration.", "duration": 3.5},
            {"scene_number": 2, "description": "test2", "narration_text": "Second test scene.", "duration": 2.5}
        ]
        out_ass = Path(__file__).parent / "temp" / "test_subs.ass"
        generate_ass(test_scenes, out_ass)
        print(f"✅ Subtitle ASS generation works! File size: {out_ass.stat().st_size} bytes")
        if out_ass.exists():
            out_ass.unlink()
    except Exception as e:
        print(f"❌ Subtitle generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_all())
