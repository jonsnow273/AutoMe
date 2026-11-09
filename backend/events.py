"""Event emitters for real-time updates. Separate module to avoid circular imports."""
import socketio
from backend.auth.jwt_handler import verify_token
from backend.database import SessionLocal
from backend.models.user import User

# Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['http://localhost:5173'],
    logger=True,
    engineio_logger=True,
)

# Mount Socket.IO as ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path='/socket.io')

# Track connected users: {user_id: set(sid)}
connected_users = {}


@sio.event
async def connect(sid, environ, auth):
    """Authenticate user on connection."""
    if not auth or 'token' not in auth:
        await sio.disconnect(sid)
        return False

    token = auth['token']
    payload = verify_token(token)
    if not payload:
        await sio.disconnect(sid)
        return False

    user_id = payload.get('sub')
    if not user_id:
        await sio.disconnect(sid)
        return False

    # Verify user exists
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            await sio.disconnect(sid)
            return False
    finally:
        db.close()

    # Store connection
    if user_id not in connected_users:
        connected_users[user_id] = set()
    connected_users[user_id].add(sid)

    # Join user's room
    await sio.enter_room(sid, f"user_{user_id}")

    print(f"Socket connected: user_id={user_id}, sid={sid}")
    return True


@sio.event
async def disconnect(sid):
    """Clean up on disconnect."""
    for user_id, sids in connected_users.items():
        if sid in sids:
            sids.remove(sid)
            if not sids:
                del connected_users[user_id]
            break
    print(f"Socket disconnected: sid={sid}")


# Helper functions to emit events
async def emit_new_message(user_id: int, message_data: dict, contact_data: dict):
    """Emit new message event to user's room."""
    await sio.emit('new_message', {
        'message': message_data,
        'contact': contact_data,
    }, room=f"user_{user_id}")


async def emit_message_read(user_id: int, message_ids: list):
    """Emit message read event to user's room."""
    await sio.emit('message_read', {
        'message_ids': message_ids,
    }, room=f"user_{user_id}")


async def emit_contact_update(user_id: int, contact_data: dict):
    """Emit contact update event to user's room."""
    await sio.emit('contact_update', contact_data, room=f"user_{user_id}")


async def emit_platform_status(user_id: int, platform_data: dict):
    """Emit platform status change event."""
    await sio.emit('platform_status', platform_data, room=f"user_{user_id}")


# Export for use in other modules
__all__ = [
    'sio',
    'socket_app',
    'emit_new_message',
    'emit_message_read',
    'emit_contact_update',
    'emit_platform_status',
]