from channels.routing import URLRouter
from channels.sessions import SessionMiddlewareStack
from django.urls import re_path

from chat.consumer import ChatConsumer


websocket = SessionMiddlewareStack(
    URLRouter([
        re_path(r"watch/(?P<meeting_id>.+)", ChatConsumer.as_asgi()),
    ])
)
