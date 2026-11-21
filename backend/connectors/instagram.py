import os
import json
import logging
import asyncio
import random
from typing import Optional, Callable, Awaitable, Dict, Any
from datetime import datetime, timezone

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    TwoFactorRequired,
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
)

from backend.database import SessionLocal
from backend.models.platform import Platform, PlatformType
from backend.models.message import Message, MessageDirection, MessageMood, MessageUrgency
from backend.models.contact import Contact, RelationshipType
from backend.utils.notifications import encrypt_json, decrypt_json

logger = logging.getLogger(__name__)

MessageCallback = Callable[[int, dict, dict], Awaitable[None]]


class InstagramConnector:
    """Per-user Instagram connector supporting sessionid or username/password authentication."""

    def __init__(
        self,
        user_id: int,
        platform_id: int,
        credentials: dict,
        on_new_message: Optional[MessageCallback] = None,
    ):
        self.user_id = user_id
        self.platform_id = platform_id
        self.credentials = credentials
        self.on_new_message = on_new_message

        self.client: Optional[Client] = None
        self._running = False
        self._polling_task: Optional[asyncio.Task] = None
        self.ready_event = asyncio.Event()
        self.error: Optional[str] = None
        self.ig_user_id: Optional[str] = None
        self.ig_username: Optional[str] = None

    async def connect_and_start(self) -> bool:
        """Authenticate with Instagram and start background DM monitoring."""
        try:
            cl = Client()
            cl.delay_range = [1, 3]

            sessionid = self.credentials.get("sessionid", "").strip()
            username = self.credentials.get("username", "").strip()
            password = self.credentials.get("password", "").strip()
            verification_code = self.credentials.get("verification_code", "").strip()
            settings = self.credentials.get("settings")

            # Try saved settings first if available
            logged_in = False
            if settings and isinstance(settings, dict):
                try:
                    logger.info(f"Attempting login using saved settings for user {self.user_id}...")
                    cl.set_settings(settings)
                    await asyncio.to_thread(cl.get_timeline_feed)
                    logged_in = True
                except Exception as e:
                    logger.warning(f"Saved settings expired or invalid for user {self.user_id}: {e}")

            # If not logged in and sessionid provided
            if not logged_in and sessionid:
                logger.info(f"Authenticating via sessionid for user {self.user_id}...")
                await asyncio.to_thread(cl.login_by_sessionid, sessionid)
                logged_in = True

            # If not logged in and username/password provided
            if not logged_in and username and password:
                logger.info(f"Authenticating via username/password for user {self.user_id}...")
                if verification_code:
                    await asyncio.to_thread(cl.login, username, password, verification_code=verification_code)
                else:
                    await asyncio.to_thread(cl.login, username, password)
                logged_in = True

            if not logged_in:
                raise ValueError("No valid credentials (sessionid or username/password) provided.")

            # Retrieve authenticated user info
            user_info = await asyncio.to_thread(cl.account_info)
            self.ig_user_id = str(user_info.pk)
            self.ig_username = str(user_info.username)
            self.client = cl
            self._running = True
            self.error = None
            self.ready_event.set()

            # Save dumped settings back to credentials to speed up subsequent reconnects
            try:
                dumped = cl.dump_settings()
                self._update_saved_settings(dumped)
            except Exception as e:
                logger.warning(f"Could not dump settings for user {self.user_id}: {e}")

            await self._mark_platform_connected()

            # Start DM poller
            self._polling_task = asyncio.create_task(self._poll_direct_messages())
            logger.info(f"Instagram connected successfully as @{self.ig_username} (ID: {self.ig_user_id})")
            return True

        except TwoFactorRequired:
            self.error = "Two-Factor Authentication is required. Please provide your 2FA verification code or use a sessionid cookie."
            logger.error(f"Instagram 2FA required for user {self.user_id}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
            return False
        except ChallengeRequired:
            self.error = "Instagram Challenge/Checkpoint required. Please log into Instagram in your browser to approve, or connect via sessionid cookie."
            logger.error(f"Instagram challenge required for user {self.user_id}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
            return False
        except BadPassword:
            self.error = "Invalid Instagram username or password."
            logger.error(f"Instagram BadPassword for user {self.user_id}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
            return False
        except PleaseWaitFewMinutes:
            self.error = "Instagram rate limit: Please wait a few minutes before trying to log in again."
            logger.error(f"Instagram rate limit for user {self.user_id}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
            return False
        except Exception as e:
            self.error = f"Instagram connection error: {str(e)}"
            logger.error(f"Instagram error for user {self.user_id}: {e}")
            await self._mark_platform_error(self.error)
            self.ready_event.set()
            return False

    def _update_saved_settings(self, dumped_settings: dict):
        """Persist session settings into encrypted platform credentials."""
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if platform:
                creds = decrypt_json(platform.credentials)
                creds["settings"] = dumped_settings
                if self.ig_username:
                    creds["ig_username"] = self.ig_username
                if self.ig_user_id:
                    creds["ig_user_id"] = self.ig_user_id
                platform.credentials = encrypt_json(creds)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to update saved settings in DB: {e}")
        finally:
            db.close()

    async def _mark_platform_connected(self):
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if platform:
                from sqlalchemy.sql import func
                platform.is_connected = True
                platform.connected_at = func.now()
                platform.error_message = None
                db.commit()
        finally:
            db.close()

    async def _mark_platform_error(self, error_msg: str):
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if platform:
                platform.is_connected = False
                platform.error_message = error_msg
                db.commit()
        finally:
            db.close()

    async def _poll_direct_messages(self):
        """Periodically poll Instagram DM inbox for new messages."""
        logger.info(f"Started Instagram DM polling for user {self.user_id}...")
        while self._running:
            try:
                # Poll inbox with polite delay and jitter (20-30s)
                poll_delay = random.uniform(20.0, 30.0)
                await asyncio.sleep(poll_delay)

                if not self._running or not self.client:
                    break

                # Fetch recent direct threads
                threads = await asyncio.to_thread(self.client.direct_threads, amount=10)
                if not threads:
                    continue

                for thread in threads:
                    await self._process_thread(thread)

            except asyncio.CancelledError:
                break
            except LoginRequired:
                logger.error(f"Instagram session expired for user {self.user_id}")
                await self._mark_platform_error("Instagram session expired. Please reconnect.")
                break
            except Exception as e:
                logger.warning(f"Error during Instagram DM polling for user {self.user_id}: {e}")
                await asyncio.sleep(15.0)

    async def _process_thread(self, thread):
        """Process incoming/outgoing messages in an Instagram DM thread."""
        if not thread.messages:
            return

        # Determine thread interlocutor (the contact)
        other_users = [u for u in thread.users if str(u.pk) != str(self.ig_user_id)]
        if not other_users:
            return
        contact_user = other_users[0]
        thread_id = str(thread.id)

        # Sync or get contact in DB
        db = SessionLocal()
        try:
            contact = db.query(Contact).filter(
                Contact.user_id == self.user_id,
                Contact.platform == "instagram",
                Contact.platform_user_id == str(contact_user.pk),
            ).first()

            avatar_url = str(contact_user.profile_pic_url) if contact_user.profile_pic_url else None
            display_name = contact_user.full_name or contact_user.username

            if not contact:
                contact = Contact(
                    user_id=self.user_id,
                    platform="instagram",
                    platform_user_id=str(contact_user.pk),
                    username=contact_user.username,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    relationship_type=RelationshipType.FRIEND,
                )
                db.add(contact)
                db.flush()
            else:
                contact.username = contact_user.username
                contact.display_name = display_name
                if avatar_url:
                    contact.avatar_url = avatar_url

            # Process latest messages (examine top 5)
            for msg in thread.messages[:5]:
                # Only handle standard text messages
                if not msg.text:
                    continue

                msg_id = str(msg.id)
                existing = db.query(Message).filter(
                    Message.user_id == self.user_id,
                    Message.platform == "instagram",
                    Message.platform_message_id == msg_id,
                ).first()

                if existing:
                    continue

                is_from_me = str(msg.user_id) == str(self.ig_user_id)
                direction = MessageDirection.OUTGOING if is_from_me else MessageDirection.INCOMING

                from sqlalchemy.sql import func
                contact.last_interaction = func.now()
                contact.message_count += 1

                new_msg = Message(
                    user_id=self.user_id,
                    platform="instagram",
                    platform_message_id=msg_id,
                    contact_id=contact.id,
                    content=msg.text,
                    direction=direction,
                    timestamp=msg.timestamp if msg.timestamp else func.now(),
                    is_read=is_from_me,
                )
                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                # Emit Socket.IO real-time notification
                if self.on_new_message:
                    msg_payload = {
                        "id": new_msg.id,
                        "platform": "instagram",
                        "platform_message_id": msg_id,
                        "contact_id": contact.id,
                        "content": new_msg.content,
                        "direction": direction.value,
                        "timestamp": new_msg.timestamp.isoformat() if new_msg.timestamp else None,
                        "is_read": new_msg.is_read,
                    }
                    contact_payload = {
                        "id": contact.id,
                        "platform": "instagram",
                        "platform_user_id": contact.platform_user_id,
                        "username": contact.username,
                        "display_name": contact.display_name,
                        "avatar_url": contact.avatar_url,
                        "unread_count": 0 if is_from_me else 1,
                        "last_message_preview": new_msg.content,
                        "last_message_time": new_msg.timestamp.isoformat() if new_msg.timestamp else None,
                    }
                    await self.on_new_message(self.user_id, msg_payload, contact_payload)

                # If incoming message and busy mode is active, handle auto-reply
                if not is_from_me:
                    await self._handle_auto_reply(contact, thread_id, new_msg.content)

        except Exception as e:
            logger.error(f"Error processing Instagram thread {thread_id} for user {self.user_id}: {e}")
            db.rollback()
        finally:
            db.close()

    async def _handle_auto_reply(self, contact: Contact, thread_id: str, incoming_text: str):
        """Check settings and send automated reply if busy mode is active."""
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == self.platform_id).first()
            if not platform:
                return

            settings = json.loads(platform.settings) if platform.settings else {}
            if not settings.get("auto_reply_enabled", True) or not settings.get("busy_mode", True):
                return

            reply_text = settings.get(
                "custom_busy_message",
                "Hey! I'm currently busy and away right now. I've received your DM on Instagram and will reply as soon as I'm back!"
            )

            # Human typing delay simulation (3-5 seconds)
            await asyncio.sleep(random.uniform(3.0, 5.0))

            if not self._running or not self.client:
                return

            # Send reply via instagrapi
            sent_msg = await asyncio.to_thread(self.client.direct_answer, thread_id, reply_text)
            sent_id = str(sent_msg.id) if (sent_msg and hasattr(sent_msg, 'id')) else f"reply_{int(datetime.now(timezone.utc).timestamp())}"

            from sqlalchemy.sql import func
            out_msg = Message(
                user_id=self.user_id,
                platform="instagram",
                platform_message_id=sent_id,
                contact_id=contact.id,
                content=reply_text,
                direction=MessageDirection.OUTGOING,
                is_read=True,
                timestamp=func.now(),
            )
            db.add(out_msg)
            contact.last_interaction = func.now()
            db.commit()
            db.refresh(out_msg)

            if self.on_new_message:
                await self.on_new_message(
                    self.user_id,
                    {
                        "id": out_msg.id,
                        "platform": "instagram",
                        "platform_message_id": sent_id,
                        "contact_id": contact.id,
                        "content": reply_text,
                        "direction": MessageDirection.OUTGOING.value,
                        "timestamp": out_msg.timestamp.isoformat() if out_msg.timestamp else None,
                        "is_read": True,
                    },
                    {
                        "id": contact.id,
                        "platform": "instagram",
                        "platform_user_id": contact.platform_user_id,
                        "username": contact.username,
                        "display_name": contact.display_name,
                        "avatar_url": contact.avatar_url,
                        "unread_count": 0,
                        "last_message_preview": reply_text,
                        "last_message_time": out_msg.timestamp.isoformat() if out_msg.timestamp else None,
                    }
                )
            logger.info(f"Sent Instagram auto-reply to @{contact.username} in thread {thread_id}")

        except Exception as e:
            logger.error(f"Failed to send Instagram auto-reply in thread {thread_id}: {e}")
        finally:
            db.close()

    async def send_message(self, thread_id_or_user_pk: str, text: str) -> bool:
        """Send a direct message to a thread or user."""
        if not self._running or not self.client:
            logger.warning(f"Instagram client not running for user {self.user_id}")
            return False

        try:
            # If target looks like a thread ID (contains underscore or is long string)
            if "_" in thread_id_or_user_pk or len(thread_id_or_user_pk) > 15:
                await asyncio.to_thread(self.client.direct_send, text, thread_ids=[thread_id_or_user_pk])
            else:
                user_pk = int(thread_id_or_user_pk)
                await asyncio.to_thread(self.client.direct_send, text, user_ids=[user_pk])
            return True
        except Exception as e:
            logger.error(f"Failed to send Instagram DM: {e}")
            return False

    async def stop(self):
        """Stop polling and disconnect client."""
        self._running = False
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        self.client = None
        logger.info(f"Instagram connector stopped for user {self.user_id}")
