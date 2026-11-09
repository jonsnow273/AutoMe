import asyncio
import logging
from typing import Dict, Optional
from backend.database import SessionLocal
from backend.models.platform import Platform, PlatformType
from backend.utils.notifications import decrypt_json
from backend.connectors.discord_bot import DiscordBot
from backend.events import emit_new_message, emit_contact_update

logger = logging.getLogger(__name__)

# Track running bot instances in memory: {user_id: DiscordBot}
_active_discord_bots: Dict[int, DiscordBot] = {}
_active_discord_tasks: Dict[int, asyncio.Task] = {}


async def _on_new_message_callback(user_id: int, message_data: dict, contact_data: dict):
    """Callback to emit Socket.IO events for new messages."""
    await emit_new_message(user_id, message_data, contact_data)
    await emit_contact_update(user_id, contact_data)


async def start_discord_bot(user_id: int, platform_id: int) -> bool:
    """Start an in-process Discord bot for a user and wait for verification."""
    db = SessionLocal()
    try:
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        if not platform or platform.platform_type != PlatformType.DISCORD:
            logger.error(f"Platform {platform_id} not found or not Discord")
            return False

        # Decrypt bot token
        creds = decrypt_json(platform.credentials)
        bot_token = creds.get("bot_token")
        if not bot_token:
            logger.error(f"No bot_token in credentials for platform {platform_id}")
            return False

        # Stop existing bot if already running
        if user_id in _active_discord_bots:
            await stop_discord_bot(user_id)

        # Create new bot instance with callback for real-time events
        bot = DiscordBot(
            user_id=user_id,
            platform_id=platform_id,
            bot_token=bot_token,
            on_new_message=_on_new_message_callback,
        )
        _active_discord_bots[user_id] = bot

        # Run bot on the asyncio event loop as background task
        task = asyncio.create_task(bot.start())
        _active_discord_tasks[user_id] = task

        # Wait up to 3.5 seconds for bot to connect or fail
        try:
            await asyncio.wait_for(bot.ready_event.wait(), timeout=3.5)
        except asyncio.TimeoutError:
            pass

        # Check if error occurred
        if bot.error:
            logger.error(f"Discord bot startup error for user {user_id}: {bot.error}")
            platform.is_connected = False
            platform.error_message = bot.error
            db.commit()
            return False

        # If connected successfully or still initializing without error
        platform.is_connected = True
        platform.error_message = None
        from sqlalchemy.sql import func
        platform.connected_at = func.now()
        db.commit()

        logger.info(f"Started Discord bot for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to start Discord bot for user {user_id}: {e}")
        return False
    finally:
        db.close()


async def stop_discord_bot(user_id: int, platform_type: str = "discord") -> bool:
    """Stop a user's Discord bot."""
    bot = _active_discord_bots.get(user_id)
    if bot:
        try:
            await bot.stop()
        except Exception as e:
            logger.error(f"Error stopping Discord bot for user {user_id}: {e}")
        finally:
            _active_discord_bots.pop(user_id, None)

    task = _active_discord_tasks.pop(user_id, None)
    if task and not task.done():
        task.cancel()

    # Update platform status in DB
    db = SessionLocal()
    try:
        platform = db.query(Platform).filter(
            Platform.user_id == user_id,
            Platform.platform_type == PlatformType.DISCORD
        ).first()
        if platform:
            platform.is_connected = False
            db.commit()
    finally:
        db.close()

    logger.info(f"Stopped Discord bot for user {user_id}")
    return True


async def get_bot_status(user_id: int, platform_type: str = "discord") -> dict:
    """Get status of a user's bot."""
    bot = _active_discord_bots.get(user_id)
    if bot and bot._running:
        is_ready = bot.client.is_ready() if bot.client else False
        return {
            "running": True,
            "connected": is_ready,
            "username": str(bot.client.user) if (bot.client and bot.client.user) else None,
        }
    return {"running": False, "connected": False, "username": None}


async def send_discord_dm(user_id: int, platform_user_id: str, content: str) -> bool:
    """Send a Discord DM to a user via their connected bot."""
    bot = _active_discord_bots.get(user_id)
    if not bot or not bot._running:
        logger.warning(f"No active Discord bot for user {user_id} to send message")
        return False

    return await bot.send_message(platform_user_id, content)


async def restart_discord_bot(user_id: int, platform_id: int) -> bool:
    """Restart a user's Discord bot."""
    await stop_discord_bot(user_id, "discord")
    await asyncio.sleep(1)
    return await start_discord_bot(user_id, platform_id)


async def auto_start_all_bots():
    """Auto-start Discord bots for all platforms that have credentials saved."""
    db = SessionLocal()
    try:
        platforms = db.query(Platform).filter(
            Platform.platform_type == PlatformType.DISCORD
        ).all()
        for p in platforms:
            if p.credentials:
                logger.info(f"Auto-starting Discord bot on startup for user {p.user_id}...")
                await start_discord_bot(p.user_id, p.id)
    except Exception as e:
        logger.error(f"Error in auto_start_all_bots: {e}")
    finally:
        db.close()


async def stop_all_bots():
    """Stop all running bots on shutdown."""
    user_ids = list(_active_discord_bots.keys())
    for uid in user_ids:
        try:
            await stop_discord_bot(uid)
        except Exception as e:
            logger.error(f"Error stopping bot for user {uid}: {e}")


async def monitor_bots():
    """Check health of running bots."""
    pass
