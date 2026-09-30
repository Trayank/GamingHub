"""
ASGI config for gaming_hub project.

It exposes the ASGI callable as a module-level variable named `application`.
Configured with ProtocolTypeRouter for HTTP and WebSocket routing with AuthMiddlewareStack.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaming_hub.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing code that may import Django models.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import rooms.routing
import games.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            rooms.routing.websocket_urlpatterns + games.routing.websocket_urlpatterns
        )
    ),
})
