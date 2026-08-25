import httpx
import shutil
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.config import get_settings, PROJECT_ROOT, Settings
from backend.models import SettingsUpdate
from backend.services.prompt_generator import STYLE_PRESETS

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
async def api_get_settings():
    settings = get_settings()
    return settings.model_dump()

@router.put("/")
async def api_update_settings(updates: SettingsUpdate):
    settings = get_settings()
    
    # Merge updates
    current_data = settings.model_dump()
    update_data = updates.model_dump(exclude_unset=True)
    merged_data = {**current_data, **update_data}
    
    # Save to file
    config_path = PROJECT_ROOT / "config" / "default_settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, "w") as f:
            json.dump(merged_data, f, indent=2)
            
        # Re-initialize the active settings instance
        import backend.config
        backend.config._settings = Settings(**merged_data)
        
        return {"status": "success", "message": "Settings updated successfully", "data": merged_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/styles")
async def api_get_styles():
    return [{"style": k, "description": v} for k, v in STYLE_PRESETS.items()]

@router.get("/status")
async def api_get_system_status():
    """Checks the health and availability of all connected AI engines."""
    settings = get_settings()
    status_report = {
        "ollama": {"available": False, "models": [], "error": None},
        "comfyui": {"available": False, "error": None},
        "piper_tts": {"available": False, "binary": None, "voice_model": False}
    }
    
    # 1. Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_url.rstrip('/')}/api/tags")
            if response.status_code == 200:
                status_report["ollama"]["available"] = True
                models_data = response.json()
                status_report["ollama"]["models"] = [m["name"] for m in models_data.get("models", [])]
    except Exception as e:
        status_report["ollama"]["error"] = str(e)
        
    # 2. Check ComfyUI
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.comfyui_url.rstrip('/')}/system_stats")
            if response.status_code == 200:
                status_report["comfyui"]["available"] = True
    except Exception as e:
        status_report["comfyui"]["error"] = str(e)
        
    # 3. Check Piper TTS
    piper_bin = shutil.which("piper")
    if not piper_bin:
        local_piper = PROJECT_ROOT / "venv" / "bin" / "piper"
        if local_piper.exists():
            piper_bin = str(local_piper)
            
    if piper_bin:
        status_report["piper_tts"]["available"] = True
        status_report["piper_tts"]["binary"] = piper_bin
        
    voice_path = PROJECT_ROOT / "assets" / "voices" / f"{settings.tts_voice}.onnx"
    if voice_path.exists():
        status_report["piper_tts"]["voice_model"] = True
        
    return status_report
