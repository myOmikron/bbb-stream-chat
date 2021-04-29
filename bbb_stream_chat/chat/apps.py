from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'chat'

    def ready(self):
        super().ready()
        from chat.models import Chat
        Chat.objects.register_signals()
