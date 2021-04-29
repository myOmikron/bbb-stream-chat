import hashlib
import json
import logging

from channels.exceptions import InvalidChannelLayerError
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils.html import escape
from rc_protocol import get_checksum
import httpx

from chat.models import Chat, Message
from chat.counter import viewers


class ChatConsumer(AsyncWebsocketConsumer):

    meeting_id: str
    user_name: str

    logger = logging.getLogger(f"{__name__}.ChatConsumer")

    @database_sync_to_async
    def load_session(self):
        "Please don't be lazy" in self.scope["session"]

    async def websocket_connect(self, message):
        # Check for valid session data
        await self.load_session()
        if "checksum" not in self.scope["session"]:
            await self.close(1008)
            return
        if "user_name" not in self.scope["session"]:
            await self.close(1008)
            return

        # Store relevant data
        user_name = self.scope["session"]["user_name"]
        meeting_id = self.scope["url_route"]["kwargs"]["meeting_id"]

        # Check checksum
        tmp_checksum = hashlib.sha512(
            f"{user_name}{meeting_id}{settings.SHARED_SECRET}".encode("utf-8")
        ).hexdigest()
        if self.scope["session"]["checksum"] != tmp_checksum:
            await self.close(1008)
            return

        # Setup channel group
        self.groups.append(meeting_id)
        try:
            for group in self.groups:
                await self.channel_layer.group_add(group, self.channel_name)
        except AttributeError:
            raise InvalidChannelLayerError(
                "BACKEND is unconfigured or doesn't support groups"
            )

        # Accept connection
        await self.accept()

        # Increment the viewer count by 1
        await viewers[meeting_id].increment()

        # Save meeting and user
        # => When these aren't set, this method didn't terminate correctly and the counter wasn't incremented
        self.meeting_id = meeting_id
        self.user_name = user_name

        await self.send(text_data=json.dumps(await self.get_old_message()))

    def __del__(self):
        # Check if consumer has finished connecting
        if hasattr(self, "meeting_id"):
            # Decrement the viewer count by 1
            viewers[self.meeting_id].decrement()

    @database_sync_to_async
    def get_old_message(self):
        return [
            {"type": "chat.message", "user_name": msg.user_name, "message": msg.message}
            for msg in Message.objects.filter(chat__chat_id=self.meeting_id)
        ]

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
        else:
            raise ValueError("No text section for incoming WebSocket frame!")

        if data["type"] == "chat.message":
            data["message"] = escape(data["message"])
            data["user_name"] = self.user_name
            await self.channel_layer.group_send(self.meeting_id, data)

            chat = await Chat.objects.aget(self.meeting_id)
            if chat:
                params = {
                    "chat_id": self.meeting_id,
                    "user_name": self.user_name,
                    "message": data["message"]
                }
                params["checksum"] = get_checksum(params, chat.callback_secret, "sendMessage")

                async with httpx.AsyncClient() as client:
                    await client.post(chat.callback_uri.rstrip("/") + "/sendMessage", json=params)

                await database_sync_to_async(Message.objects.create)(
                    chat=chat, user_name=self.user_name, message=data["message"]
                )
        elif data["type"] == "chat.update":
            await self.send(text_data=json.dumps({
                "type": "chat.update",
                "viewers": viewers[self.meeting_id].value
            }))
        else:
            raise ValueError(f"Incoming WebSocket json object is of unknown type: '{data['type']}'")

    async def chat_message(self, message):
        await self.send(text_data=json.dumps(message))

    async def chat_redirect(self, message):
        await self.send(text_data=json.dumps(message))

    async def chat_reload(self, message):
        await self.send(text_data=json.dumps(message))
