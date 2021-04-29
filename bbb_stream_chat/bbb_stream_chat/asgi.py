"""
ASGI config for bbb_stream_chat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

from chat.routing import websocket

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bbb_stream_chat.settings')

application = ProtocolTypeRouter({
    "ws": websocket,
    "http": get_asgi_application(),
})
