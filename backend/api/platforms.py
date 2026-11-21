from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import os
import httpx
import logging

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.platform import Platform, PlatformType
from backend.models.message import Message, MessageDirection
from backend.models.contact import Contact, RelationshipType
from backend.connectors.session_manager import (
    start_discord_bot,
    stop_discord_bot,
    start_instagram_connector,
    stop_instagram_connector,
    get_bot_status,
)
from backend.utils.notifications import encrypt_json, decrypt_json

logger = logging.getLogger(__name__)
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3001")

router = APIRouter(prefix="/platforms", tags=["Platforms"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class PlatformConnectDiscord(BaseModel):
    bot_token: str
    settings: Optional[dict] = None


class PlatformConnectInstagram(BaseModel):
    sessionid: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    verification_code: Optional[str] = None
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
        if p.platform_type == PlatformType.WHATSAPP:
            is_actually_connected = p.is_connected
            try:
                with httpx.Client(timeout=2.0) as client:
                    wa_res = client.get(f"{WHATSAPP_SERVICE_URL}/session/status/{current_user.id}")
                    if wa_res.status_code == 200:
                        wa_status = wa_res.json()
                        is_actually_connected = (wa_status.get("status") == "ready")
            except Exception:
                is_actually_connected = p.is_connected
            bot_status = {"running": is_actually_connected, "connected": is_actually_connected}
        elif p.platform_type == PlatformType.INSTAGRAM:
            bot_status = await get_bot_status(current_user.id, "instagram")
            is_actually_connected = bot_status.get("connected", False)
            if not is_actually_connected and p.credentials and p.is_connected:
                if not p.error_message or p.error_message == "Bot process stopped":
                    logger.info(f"Auto-resuming Instagram connector for user {current_user.id} on status check...")
                    started = await start_instagram_connector(current_user.id, p.id)
                    if started:
                        bot_status = await get_bot_status(current_user.id, "instagram")
                        is_actually_connected = bot_status.get("connected", False)
        else:
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
        if pt == PlatformType.DISCORD:
            await stop_discord_bot(current_user.id, platform_type)
        elif pt == PlatformType.INSTAGRAM:
            await stop_instagram_connector(current_user.id)
        elif pt == PlatformType.WHATSAPP:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{WHATSAPP_SERVICE_URL}/session/stop", json={"userId": current_user.id})
            except Exception:
                pass
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

    # Stop the bot/connector process
    if platform.platform_type == PlatformType.DISCORD:
        await stop_discord_bot(current_user.id, platform.platform_type.value)
    elif platform.platform_type == PlatformType.INSTAGRAM:
        await stop_instagram_connector(current_user.id)
    elif platform.platform_type == PlatformType.WHATSAPP:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{WHATSAPP_SERVICE_URL}/session/stop", json={"userId": current_user.id})
        except Exception:
            pass

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

    if platform.platform_type == PlatformType.DISCORD:
        success = await restart_discord_bot(current_user.id, platform.id)
    elif platform.platform_type == PlatformType.INSTAGRAM:
        await stop_instagram_connector(current_user.id)
        import asyncio
        await asyncio.sleep(1)
        success = await start_instagram_connector(current_user.id, platform.id)
    else:
        raise HTTPException(status_code=400, detail="Restart not supported for this platform")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to restart connector")

    return {"message": "Connector restart initiated"}


# ─── Instagram Routes ───────────────────────────────────────────────────────

@router.post("/instagram/connect", response_model=PlatformResponse)
async def connect_instagram(
    data: PlatformConnectInstagram,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect an Instagram account via sessionid cookie or username/password."""
    sessionid = (data.sessionid or "").strip()
    username = (data.username or "").strip()
    password = (data.password or "").strip()
    verification_code = (data.verification_code or "").strip()

    if not sessionid and not (username and password):
        raise HTTPException(
            status_code=400,
            detail="Please provide either a sessionid cookie, or both Instagram username and password."
        )

    creds_dict = {}
    if sessionid:
        creds_dict["sessionid"] = sessionid
    if username:
        creds_dict["username"] = username
    if password:
        creds_dict["password"] = password
    if verification_code:
        creds_dict["verification_code"] = verification_code

    encrypted_creds = encrypt_json(creds_dict)

    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.INSTAGRAM,
    ).first()

    default_settings = json.dumps({"auto_reply_enabled": True, "busy_mode": True})

    if not platform:
        platform = Platform(
            user_id=current_user.id,
            platform_type=PlatformType.INSTAGRAM,
            credentials=encrypted_creds,
            settings=default_settings,
            is_connected=False,
            error_message=None,
        )
        db.add(platform)
    else:
        platform.credentials = encrypted_creds
        platform.error_message = None
        if not platform.settings:
            platform.settings = default_settings

    db.commit()
    db.refresh(platform)

    # Start the connector
    started = await start_instagram_connector(current_user.id, platform.id)
    db.refresh(platform)

    if not started:
        raise HTTPException(
            status_code=400,
            detail=platform.error_message or "Failed to authenticate with Instagram."
        )

    bot_status = await get_bot_status(current_user.id, "instagram")
    from backend.events import emit_platform_status
    await emit_platform_status(current_user.id, {
        "platform": "instagram",
        "status": "connected",
        "username": bot_status.get("username"),
    })

    return PlatformResponse(
        id=platform.id,
        platform_type=platform.platform_type.value,
        is_connected=True,
        connected_at=platform.connected_at.isoformat() if platform.connected_at else None,
        settings=json.loads(platform.settings) if platform.settings else {},
        error_message=None,
        last_sync=platform.last_sync.isoformat() if platform.last_sync else None,
    )


@router.post("/instagram/reconnect")
async def reconnect_instagram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reconnect Instagram using stored credentials."""
    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.INSTAGRAM,
    ).first()

    if not platform or not platform.credentials:
        raise HTTPException(status_code=404, detail="No saved Instagram credentials found")

    await stop_instagram_connector(current_user.id)
    import asyncio
    await asyncio.sleep(1)

    started = await start_instagram_connector(current_user.id, platform.id)
    db.refresh(platform)

    if not started:
        raise HTTPException(
            status_code=400,
            detail=platform.error_message or "Failed to reconnect Instagram"
        )

    return {"message": "Instagram reconnected successfully"}


@router.post("/instagram/disconnect")
async def disconnect_instagram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect and remove Instagram platform."""
    await stop_instagram_connector(current_user.id)
    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.INSTAGRAM,
    ).first()
    if platform:
        db.delete(platform)
        db.commit()
    return {"message": "Instagram disconnected successfully"}


# ─── WhatsApp Routes & Webhooks ─────────────────────────────────────────────

class WhatsAppMessageWebhook(BaseModel):
    userId: int
    from_: str = Field(alias="from")
    phone: str
    name: str
    avatarUrl: Optional[str] = None
    messageId: str
    content: str
    timestamp: Optional[int] = None


class WhatsAppReadyWebhook(BaseModel):
    userId: int
    phone: Optional[str] = None
    name: Optional[str] = None


@router.post("/whatsapp/connect")
async def connect_whatsapp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start WhatsApp session and get QR code."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{WHATSAPP_SERVICE_URL}/session/start",
                json={"userId": current_user.id}
            )
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to WhatsApp service: {e}")


@router.get("/whatsapp/status")
async def get_whatsapp_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check WhatsApp session status & QR code."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{WHATSAPP_SERVICE_URL}/session/status/{current_user.id}")
            return res.json()
    except Exception as e:
        return {"userId": current_user.id, "status": "disconnected", "qr": None, "error": str(e)}


@router.post("/whatsapp/disconnect")
async def disconnect_whatsapp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect and destroy WhatsApp session."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{WHATSAPP_SERVICE_URL}/session/stop", json={"userId": current_user.id})
    except Exception:
        pass

    platform = db.query(Platform).filter(
        Platform.user_id == current_user.id,
        Platform.platform_type == PlatformType.WHATSAPP
    ).first()
    if platform:
        db.delete(platform)
        db.commit()

    return {"message": "WhatsApp disconnected"}


@router.post("/whatsapp/webhook/ready")
async def whatsapp_webhook_ready(
    data: WhatsAppReadyWebhook,
    db: Session = Depends(get_db),
):
    """Called by WhatsApp microservice when user scans QR and connects."""
    platform = db.query(Platform).filter(
        Platform.user_id == data.userId,
        Platform.platform_type == PlatformType.WHATSAPP
    ).first()

    from sqlalchemy.sql import func
    creds = encrypt_json({"phone": data.phone, "name": data.name})

    if not platform:
        platform = Platform(
            user_id=data.userId,
            platform_type=PlatformType.WHATSAPP,
            credentials=creds,
            settings=json.dumps({"auto_reply_enabled": True, "busy_mode": True}),
            is_connected=True,
            connected_at=func.now(),
        )
        db.add(platform)
    else:
        platform.credentials = creds
        platform.is_connected = True
        platform.connected_at = func.now()
        platform.error_message = None

    db.commit()

    from backend.events import emit_platform_status
    await emit_platform_status(data.userId, {"platform": "whatsapp", "status": "connected"})
    return {"status": "ok"}


@router.post("/whatsapp/webhook/message")
async def whatsapp_webhook_message(
    data: WhatsAppMessageWebhook,
    db: Session = Depends(get_db),
):
    """Called by WhatsApp microservice on incoming message."""
    contact = db.query(Contact).filter(
        Contact.user_id == data.userId,
        Contact.platform == "whatsapp",
        Contact.platform_user_id == data.phone
    ).first()

    if not contact:
        contact = Contact(
            user_id=data.userId,
            platform="whatsapp",
            platform_user_id=data.phone,
            username=data.phone,
            display_name=data.name or data.phone,
            avatar_url=data.avatarUrl,
            relationship_type=RelationshipType.FRIEND,
        )
        db.add(contact)
        db.flush()

    from sqlalchemy.sql import func
    contact.last_interaction = func.now()
    contact.message_count += 1

    msg = Message(
        user_id=data.userId,
        platform="whatsapp",
        platform_message_id=data.messageId,
        contact_id=contact.id,
        content=data.content,
        direction=MessageDirection.INCOMING,
        is_read=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Emit socket events
    from backend.events import emit_new_message, emit_contact_update
    await emit_new_message(data.userId, {
        "id": msg.id,
        "platform": "whatsapp",
        "platform_message_id": msg.platform_message_id,
        "contact_id": contact.id,
        "content": msg.content,
        "direction": msg.direction.value,
        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        "is_read": msg.is_read,
    }, {
        "id": contact.id,
        "platform": "whatsapp",
        "platform_user_id": contact.platform_user_id,
        "username": contact.username,
        "display_name": contact.display_name,
        "avatar_url": contact.avatar_url,
        "unread_count": 1,
        "last_message_preview": msg.content,
        "last_message_time": msg.timestamp.isoformat() if msg.timestamp else None,
    })
    await emit_contact_update(data.userId, {
        "id": contact.id,
        "platform": "whatsapp",
        "platform_user_id": contact.platform_user_id,
        "username": contact.username,
        "display_name": contact.display_name,
        "avatar_url": contact.avatar_url,
        "unread_count": 1,
        "last_message_preview": msg.content,
        "last_message_time": msg.timestamp.isoformat() if msg.timestamp else None,
    })

    # Check auto reply / busy mode
    platform = db.query(Platform).filter(
        Platform.user_id == data.userId,
        Platform.platform_type == PlatformType.WHATSAPP
    ).first()
    settings = json.loads(platform.settings) if (platform and platform.settings) else {}
    if settings.get("auto_reply_enabled", True) and settings.get("busy_mode", True):
        reply_text = settings.get(
            "custom_busy_message",
            "Hey! I'm currently busy and away from my phone right now. I've received your message on WhatsApp and will get back to you soon!"
        )
        return {"autoReply": True, "replyText": reply_text}

    return {"autoReply": False}