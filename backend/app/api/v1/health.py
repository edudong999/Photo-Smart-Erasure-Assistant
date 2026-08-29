from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "ai_reachable": True,
        "version": "0.1.0",
    }
