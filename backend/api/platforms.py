from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.platform import Platform, PlatformType
from backend.models.message import Message
from backend.models.contact import Contact
from backend.connectors.session_manager import (
    start_discord_bot,
    stop_discord_bot,
    get_bot_status,
)
from backend.utils.notifications import encrypt_json, decrypt_json

router = APIRouter(prefix="/platforms", tags=["Platforms"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class PlatformConnectDiscord(BaseModel):
    bot_token: str
    settings: Optional[dict] = None


class PlatformResponse(BaseModel):
    id: int
    platform_type: str
    is_connected: bool
    connected_at: Optional[str]
    settings: Optional[dict]
    error_message: Optional[str]
    last_sync: Optional[str]

    class Config:
        from_attributes = True


class PlatformStatusResponse(BaseModel):
    platform: PlatformResponse
    bot_status: dict


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[PlatformResponse])
async def list_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all connected platforms for the current user with real bot status."""
    platforms = db.query(Platform).filter(Platform.user_id == current_user.id).all()
    result = []
    for p in platforms:
        # Check actual bot status
        bot_status = await get_bot_status(current_user.id, p.platform_type.value)
        is_actually_connected = bot_status.get("connected", False)

        # If bot process died or server restarted, attempt auto-reconnecting if credentials exist
        if not is_actually_connected and p.credentials and p.platform_type == PlatformType.DISCORD:
            # If it wasn't a deliberate user error, try starting it
            if not p.error_message or p.error_message == "Bot process stopped":
                logger.info(f"Auto-resuming bot for user {current_user.id} on status check...")
                started = await start_discord_bot(current_user.id, p.id)
                if started:
                    bot_status = await get_bot_status(current_user.id, p.platform_type.value)
                    is_actually_connected = bot_status.get("connected", False)

        # Update DB if status changed
        if p.is_connected != is_actually_connected:
            p.is_connected = is_actually_connected
            if not is_actually_connected and not p.error_message:
                p.error_message = "Bot process stopped"
            db.commit()

        settings = json.loads(p.settings) if p.settings else {}
        result.append(PlatformResponse(
            id=p.id,
            platform_type=p.platform_type.value,
            is_connected=is_actually_connected,
            connected_at=p.connected_at.isoformat() if p.connected_at else None,
            settings=settings,
            error_message=p.error_message,
            last_sync=p.last_sync.isoformat() if p.last_sync else None,
        ))
    return result


@router.post("/discord/reconnect", response_model=PlatformResponse)
async def reconnect_discord(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reconnect Discord bot using saved credentials."""
    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.DISCORD
    ).first()

    if not platform or not platform.credentials:
        raise HTTPException(status_code=404, detail="No saved Discord credentials found. Please click Connect to enter your Bot Token.")

    platform.error_message = None
    db.commit()

    success = await start_discord_bot(current_user.id, platform.id)
    db.refresh(platform)

    if not success or not platform.is_connected:
        err = platform.error_message or "Failed to connect to Discord"
        raise HTTPException(status_code=400, detail=f"Discord connection failed: {err}")

    return PlatformResponse(
        id=platform.id,
        platform_type=platform.platform_type.value,
        is_connected=True,
        connected_at=platform.connected_at.isoformat() if platform.connected_at else None,
        settings=json.loads(platform.settings) if platform.settings else {},
        error_message=None,
        last_sync=platform.last_sync.isoformat() if platform.last_sync else None,
    )


@router.post("/discord/connect", response_model=PlatformResponse)
async def connect_discord(
    data: PlatformConnectDiscord,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect or reconnect a Discord bot for the current user."""
    # Validate token format (basic check)
    if not data.bot_token or len(data.bot_token) < 50:
        raise HTTPException(status_code=400, detail="Invalid bot token")

    # Check if platform record exists
    existing = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.DISCORD
    ).first()

    # Encrypt credentials
    credentials = encrypt_json({"bot_token": data.bot_token})
    settings = json.dumps(data.settings) if data.settings else json.dumps({"auto_reply_enabled": True, "dm_only": True})

    if existing:
        # Update existing record with new token/settings
        existing.credentials = credentials
        existing.settings = settings
        existing.error_message = None
        platform = existing
        db.commit()
        db.refresh(platform)
    else:
        # Create new platform record
        platform = Platform(
            user_id=current_user.id,
            platform_type=PlatformType.DISCORD,
            credentials=credentials,
            settings=settings,
            is_connected=False,
        )
        db.add(platform)
        db.commit()
        db.refresh(platform)

    # Start/restart the bot process
    success = await start_discord_bot(current_user.id, platform.id)
    db.refresh(platform)

    if not success or not platform.is_connected:
        err = platform.error_message or "Failed to connect to Discord"
        if "token" in err.lower():
            detail = "Invalid Discord account token. Please make sure you copied the full authorization token from your browser/client network tab."
        else:
            detail = f"Discord connection failed: {err}"
        raise HTTPException(status_code=400, detail=detail)

    bot_status = await get_bot_status(current_user.id, "discord")

    return PlatformResponse(
        id=platform.id,
        platform_type=platform.platform_type.value,
        is_connected=True,
        connected_at=platform.connected_at.isoformat() if platform.connected_at else None,
        settings=json.loads(platform.settings) if platform.settings else {},
        error_message=None,
        last_sync=platform.last_sync.isoformat() if platform.last_sync else None,
    )


@router.post("/disconnect-type/{platform_type}", status_code=status.HTTP_200_OK)
async def disconnect_platform_by_type(
    platform_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect and remove a platform by name (e.g. 'discord')."""
    try:
        pt = PlatformType(platform_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform type")

    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == pt
    ).first()

    if platform:
        await stop_discord_bot(current_user.id, platform_type)
        db.delete(platform)
        db.commit()

    return {"message": f"{platform_type} disconnected"}


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.post("/{platform_id}/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_platform(
    platform_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect a platform."""
    platform = db.query(Platform).filter(
        Platform.id == platform_id,
        Platform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Stop the bot process
    await stop_discord_bot(current_user.id, platform.platform_type.value)

    # Delete platform record
    db.delete(platform)
    db.commit()

    return {"message": "Disconnected successfully"}


@router.post("/{platform_id}/force-disconnect", status_code=status.HTTP_200_OK)
async def force_disconnect_platform(
    platform_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force disconnect a platform - cleanup even if bot process is stuck."""
    platform = db.query(Platform).filter(
        Platform.id == platform_id,
        Platform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Force stop the bot process
    from backend.connectors.session_manager import _active_discord_bots, _active_discord_tasks
    import asyncio

    bot = _active_discord_bots.get(current_user.id)
    if bot:
        try:
            await bot.stop()
        except Exception:
            pass
        _active_discord_bots.pop(current_user.id, None)

    task = _active_discord_tasks.pop(current_user.id, None)
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except Exception:
            pass

    # Delete platform record
    db.delete(platform)
    db.commit()

    return {"message": "Force disconnected"}


@router.get("/{platform_id}/status", response_model=PlatformStatusResponse)
async def get_platform_status(
    platform_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed status for a platform including bot process health."""
    platform = db.query(Platform).filter(
        Platform.id == platform_id,
        Platform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    bot_status = await get_bot_status(current_user.id, platform.platform_type.value)

    # Update platform record with actual status
    if platform.is_connected != bot_status.get("connected", False):
        platform.is_connected = bot_status.get("connected", False)
        if not platform.is_connected:
            platform.error_message = "Bot process not running"
        db.commit()

    settings = json.loads(platform.settings) if platform.settings else {}
    return PlatformStatusResponse(
        platform=PlatformResponse(
            id=platform.id,
            platform_type=platform.platform_type.value,
            is_connected=bot_status.get("connected", False),
            connected_at=platform.connected_at.isoformat() if platform.connected_at else None,
            settings=settings,
            error_message=platform.error_message,
            last_sync=platform.last_sync.isoformat() if platform.last_sync else None,
        ),
        bot_status=bot_status,
    )


@router.post("/{platform_id}/restart")
async def restart_platform(
    platform_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restart a platform's bot process."""
    from backend.connectors.session_manager import restart_discord_bot

    platform = db.query(Platform).filter(
        Platform.id == platform_id,
        Platform.user_id == current_user.id
    ).first()

    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    if platform.platform_type != PlatformType.DISCORD:
        raise HTTPException(status_code=400, detail="Restart only supported for Discord currently")

    success = await restart_discord_bot(current_user.id, platform.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restart bot")

    return {"message": "Bot restart initiated"}