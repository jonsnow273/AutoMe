import os
import json
import logging
import asyncio
from typing import Optional, Callable, Awaitable
from datetime import datetime, timezone
import discord

from backend.database import SessionLocal
from backend.models.platform import Platform, PlatformType
from backend.models.message import Message, MessageDirection, MessageMood, MessageUrgency
from backend.models.contact import Contact, RelationshipType
from backend.utils.notifications import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

MessageCallback = Callable[[int, dict, dict], Awaitable[None]]


class DiscordBot:
    """Per-user Discord client supporting User accounts (Alt account) and DMs."""

    def __init__(
        self,
        user_id: int,
        platform_id: int,
        bot_token: str,
        on_new_message: Optional[MessageCallback] = None,
    ):
        self.user_id = user_id
        self.platform_id = platform_id
        self.bot_token = bot_token.strip().strip('"').strip("'")
        self.client: Optional[discord.Client] = None
        self._running = False
        self._on_new_message = on_new_message
        self.ready_event = asyncio.Event()
        self.error: Optional[str] = None

    async def start(self):
        """Start the Discord client with user token."""
        if self._running:
            logger.warning(f"Client for user {self.user_id} already running")
            return

        self.client = discord.Client()
        self._setup_events()
        self._running = True

        try:
            logger.info(f"Connecting Discord client for user {self.user_id}...")
            await self.client.start(self.bot_token)
        except discord.LoginFailure:
            self.error = "Invalid Discord authorization token. Please check your token and try again."
            logger.error(f"Invalid Discord token for user {self.user_id}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
        except Exception as e:
            self.error = str(e)
            logger.error(f"Discord client error for user {self.user_id}: {e}")
            await self._mark_platform_error(str(e))
            self.ready_event.set()
        finally:
            self._running = False
            self.ready_event.set()

    def _setup_events(self):
        @self.client.event
        async def on_ready():
            logger.info(f"Discord connected successfully as user {self.client.user} (ID: {self.client.user.id})")
            self.error = None
            self.ready_event.set()
            await self._mark_platform_connected()

            # Automatically sync existing DM channels into AutoMe
            asyncio.create_task(self._sync_existing_dms())

        @self.client.event
        async def on_message(message: discord.Message):
            # Only process private DM channels
            if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
                return

            # If sent by the logged-in user itself
            if message.author.id == self.client.user.id:
                await self._handle_outgoing_dm(message)
                return

            # Incoming DM from someone else
            await self._handle_incoming_dm(message)

        @self.client.event
        async def on_disconnect():
            logger.warning(f"Discord client disconnected for user {self.user_id}")

    async def _sync_existing_dms(self):
        """Sync open DM channels and recent chat history into the database."""
        await asyncio.sleep(1.0)
        logger.info(f"Starting initial DM sync for user {self.user_id}...")
        db = SessionLocal()
        try:
            for channel in self.client.private_channels:
                if isinstance(channel, discord.DMChannel):
                    recipient = channel.recipient
                    if not recipient or recipient.id == self.client.user.id:
                        continue

                    contact = db.query(Contact).filter(
                        Contact.user_id == self.user_id,
                        Contact.platform == "discord",
                        Contact.platform_user_id == str(recipient.id)
                    ).first()

                    if not contact:
                        contact = Contact(
                            user_id=self.user_id,
                            platform="discord",
                            platform_user_id=str(recipient.id),
                            username=recipient.name,
                            display_name=recipient.display_name,
                            avatar_url=str(recipient.avatar.url) if recipient.avatar else None,
                            relationship_type=RelationshipType.FRIEND,
                            message_count=0,
                        )
                        db.add(contact)
                        db.flush()

                    # Fetch recent message history (up to 20 messages)
                    try:
                        async for msg in channel.history(limit=20):
                            exists = db.query(Message).filter(
                                Message.platform_message_id == str(msg.id)
                            ).first()
                            if not exists and (msg.content or msg.attachments):
                                is_self = (msg.author.id == self.client.user.id)
                                content = msg.content if msg.content else "[Attachment / Image]"
                                db_msg = Message(
                                    user_id=self.user_id,
                                    platform="discord",
                                    platform_message_id=str(msg.id),
                                    contact_id=contact.id,
                                    content=content,
                                    direction=MessageDirection.OUTGOING if is_self else MessageDirection.INCOMING,
                                    timestamp=msg.created_at,
                                    is_read=True,
                                    mood=MessageMood.POSITIVE if is_self else MessageMood.NEUTRAL,
                                    urgency=MessageUrgency.LOW,
                                )
                                db.add(db_msg)
                                contact.message_count += 1
                                contact.last_interaction = msg.created_at
                        db.commit()
                    except Exception as err:
                        logger.error(f"Error fetching channel history for {recipient.name}: {err}")
                        db.rollback()

            logger.info(f"Completed initial DM sync for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to sync DMs for user {self.user_id}: {e}")
        finally:
            db.close()

    async def _handle_outgoing_dm(self, message: discord.Message):
        """Save outgoing messages sent from this account (via Discord client or web UI)."""
        db = SessionLocal()
        try:
            recipient = getattr(message.channel, "recipient", None)
            if not recipient:
                return

            contact = db.query(Contact).filter(
                Contact.user_id == self.user_id,
                Contact.platform == "discord",
                Contact.platform_user_id == str(recipient.id)
            ).first()

            if not contact:
                contact = Contact(
                    user_id=self.user_id,
                    platform="discord",
                    platform_user_id=str(recipient.id),
                    username=recipient.name,
                    display_name=recipient.display_name,
                    avatar_url=str(recipient.avatar.url) if recipient.avatar else None,
                )
                db.add(contact)
                db.flush()

            exists = db.query(Message).filter(Message.platform_message_id == str(message.id)).first()
            if exists:
                return

            contact.last_interaction = message.created_at
            contact.message_count += 1

            content = message.content if message.content else "[Attachment / Image]"
            db_message = Message(
                user_id=self.user_id,
                platform="discord",
                platform_message_id=str(message.id),
                contact_id=contact.id,
                content=content,
                direction=MessageDirection.OUTGOING,
                timestamp=message.created_at,
                is_read=True,
            )
            db.add(db_message)
            db.commit()
            db.refresh(db_message)

            if self._on_new_message:
                await self._notify_socket(db_message, contact)

        except Exception as e:
            logger.error(f"Error saving outgoing DM: {e}")
            db.rollback()
        finally:
            db.close()

    async def _handle_incoming_dm(self, message: discord.Message):
        """Process incoming DM, emit socket update, and trigger auto-reply if busy."""
        db = SessionLocal()
        try:
            # Find or create contact
            contact = db.query(Contact).filter(
                Contact.user_id == self.user_id,
                Contact.platform == "discord",
                Contact.platform_user_id == str(message.author.id)
            ).first()

            if not contact:
                contact = Contact(
                    user_id=self.user_id,
                    platform="discord",
                    platform_user_id=str(message.author.id),
                    username=message.author.name,
                    display_name=message.author.display_name,
                    avatar_url=str(message.author.avatar.url) if message.author.avatar else None,
                    relationship_type=RelationshipType.FRIEND,
                )
                db.add(contact)
                db.flush()

            contact.last_interaction = message.created_at
            contact.message_count += 1

            content = message.content if message.content else "[Attachment / Image]"
            db_message = Message(
                user_id=self.user_id,
                platform="discord",
                platform_message_id=str(message.id),
                contact_id=contact.id,
                content=content,
                direction=MessageDirection.INCOMING,
                timestamp=message.created_at,
                is_read=False,
                mood=MessageMood.NEUTRAL,
                urgency=MessageUrgency.LOW,
            )
            db.add(db_message)
            db.commit()
            db.refresh(db_message)

            # Real-time WebSocket emission to frontend
            if self._on_new_message:
                await self._notify_socket(db_message, contact)

            # Check if busy mode / auto reply is enabled
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            settings = json.loads(platform.settings) if (platform and platform.settings) else {}
            auto_reply_enabled = settings.get("auto_reply_enabled", True)
            busy_mode = settings.get("busy_mode", True)

            if auto_reply_enabled and busy_mode:
                busy_text = settings.get(
                    "custom_busy_message",
                    "Hey! I'm currently busy right now. I've received your message and will get back to you as soon as I can!"
                )
                # Run auto-reply in background with human-like delay
                asyncio.create_task(self._send_auto_reply(message.channel, busy_text, contact.id))

        except Exception as e:
            logger.error(f"Error handling incoming DM: {e}")
            db.rollback()
        finally:
            db.close()

    async def _send_auto_reply(self, channel, reply_text: str, contact_id: int):
        """Simulate typing and send auto-reply directly from user's account."""
        try:
            await asyncio.sleep(2.0)
            async with channel.typing():
                await asyncio.sleep(2.0)
            sent_msg = await channel.send(reply_text)
            logger.info(f"Auto-reply sent in channel: {reply_text}")

            # Save outgoing auto-reply to DB
            db = SessionLocal()
            try:
                contact = db.query(Contact).filter(Contact.id == contact_id).first()
                if contact:
                    contact.last_interaction = sent_msg.created_at
                auto_msg = Message(
                    user_id=self.user_id,
                    platform="discord",
                    platform_message_id=str(sent_msg.id),
                    contact_id=contact_id,
                    content=reply_text,
                    direction=MessageDirection.OUTGOING,
                    timestamp=sent_msg.created_at,
                    is_read=True,
                )
                db.add(auto_msg)
                db.commit()
                db.refresh(auto_msg)

                if self._on_new_message and contact:
                    await self._notify_socket(auto_msg, contact)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to send auto-reply: {e}")

    async def _notify_socket(self, message: Message, contact: Contact):
        message_data = {
            "id": message.id,
            "platform": "discord",
            "platform_message_id": message.platform_message_id,
            "contact_id": contact.id,
            "content": message.content,
            "direction": message.direction.value,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "is_read": message.is_read,
            "mood": message.mood.value if message.mood else None,
            "urgency": message.urgency.value if message.urgency else None,
            "suggested_reply": message.suggested_reply,
        }
        contact_data = {
            "id": contact.id,
            "platform": "discord",
            "platform_user_id": contact.platform_user_id,
            "username": contact.username,
            "display_name": contact.display_name,
            "avatar_url": contact.avatar_url,
            "unread_count": 1 if message.direction == MessageDirection.INCOMING else 0,
            "last_message_preview": message.content,
            "last_message_time": message.timestamp.isoformat() if message.timestamp else None,
        }
        await self._on_new_message(self.user_id, message_data, contact_data)

    async def _mark_platform_connected(self):
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if platform:
                platform.is_connected = True
                platform.error_message = None
                from sqlalchemy.sql import func
                platform.connected_at = func.now()
                db.commit()
        finally:
            db.close()

    async def _mark_platform_error(self, error: str):
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if platform:
                platform.is_connected = False
                platform.error_message = error
                db.commit()
        finally:
            db.close()

    async def stop(self):
        """Stop the Discord client."""
        if self.client and self._running:
            await self.client.close()
            self._running = False
            logger.info(f"Discord client stopped for user {self.user_id}")

    async def send_message(self, platform_user_id: str, content: str) -> bool:
        """Send a DM directly to a user from this account."""
        if not self.client or not self._running:
            return False

        try:
            user = await self.client.fetch_user(int(platform_user_id))
            if user:
                await user.send(content)
                return True
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
        return False


async def run_discord_bot(user_id: int, platform_id: int, bot_token: str):
    """Entry point for running a single user's Discord client."""
    bot = DiscordBot(user_id, platform_id, bot_token)
    await bot.start()
