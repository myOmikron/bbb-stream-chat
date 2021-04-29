from django.db import models
from channels.db import database_sync_to_async
from django.db.models.signals import post_save, pre_delete


class CachedManager(models.Manager):

    def __init__(self, field_name):
        super().__init__()
        self.field = field_name
        self.cache = {}

    async def aget(self, value, **kwargs):
        if value in self.cache:
            return self.cache[value]
        else:
            return await database_sync_to_async(self.get)(value, **kwargs)

    def get(self, value=None, **kwargs):
        if value in self.cache:
            return self.cache[value]
        elif value is None:
            return super().get(**kwargs)
        else:
            try:
                self.cache[value] = super().get((self.field, value))
            except self.model.DoesNotExist:
                self.cache[value] = None
            return self.cache[value]

    def on_object_save(self, instance, **kwargs):
        value = instance
        for attr in self.field.split("__"):
            value = getattr(value, attr)

        self.cache[value] = instance

    def on_object_delete(self, instance, **kwargs):
        value = instance
        for attr in self.field.split("__"):
            value = getattr(value, attr)

        self.cache[value] = None

    def register_signals(self):
        post_save.connect(self.on_object_save, sender=self.model, dispatch_uid="on_chat_save")
        pre_delete.connect(self.on_object_delete, sender=self.model, dispatch_uid="on_chat_delete")


class Chat(models.Model):

    chat_id = models.CharField(max_length=255, default="", unique=True)
    callback_uri = models.CharField(max_length=255, default="")
    callback_secret = models.CharField(max_length=255, default="")
    callback_id = models.CharField(max_length=255, default="")

    objects = CachedManager("chat_id")

    def __str__(self):
        return self.chat_id


class Message(models.Model):

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    message = models.CharField(max_length=4096, default="")
    user_name = models.CharField(max_length=255, default="")

    def __str__(self):
        return f"Message by {self.user_name}"
