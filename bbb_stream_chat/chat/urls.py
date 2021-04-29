from django.urls import path

from chat.views import *


urlpatterns = [
    path("viewerCounts", ViewerCounts.as_view()),
    path("startChat", StartChat.as_view()),
    path("sendMessage", SendMessage.as_view()),
    path("endChat", EndChat.as_view()),
]
