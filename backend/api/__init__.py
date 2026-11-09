from backend.api.messages import router as messages_router
from backend.api.contacts import router as contacts_router
from backend.api.platforms import router as platforms_router
from backend.auth.router import router as auth_router
from backend.api.settings import router as settings_router
from backend.api.analytics import router as analytics_router

__all__ = [
    "messages_router",
    "contacts_router",
    "platforms_router",
    "auth_router",
    "settings_router",
    "analytics_router",
]