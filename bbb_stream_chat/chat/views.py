from asgiref.sync import async_to_sync
from django.http import JsonResponse
from channels.layers import get_channel_layer

from bbb_common_api.views import PostApiPoint, GetApiPoint
from chat.counter import viewers
from chat.models import Chat


channel_layer = get_channel_layer()


class ViewerCounts(GetApiPoint):

    endpoint = "viewerCounts"
    required_parameters = []

    def safe_get(self, request, *args, **kwargs):
        if "meeting_id" in request.GET:
            ids = request.GET.getlist("meeting_id")
        else:
            ids = (chat.meeting_id for chat in Chat.objects.all())

        viewer_counts = {}
        for meeting_id in ids:
            viewer_counts[meeting_id] = viewers[meeting_id].value

        return JsonResponse(
            {"success": True, "message": "Success, see 'content'", "content": viewer_counts}
        )


class StartChat(PostApiPoint):

    endpoint = "startChat"
    required_parameters = ["chat_id"]

    def safe_post(self, request, parameters, *args, **kwargs):
        callback_params = ["callback_uri", "callback_secret", "callback_id"]
        missing = []
        for param in callback_params:
            if param not in parameters:
                missing.append(param)

        if len(missing) == 1:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Parameter {missing[0]} is mandatory when enabling callbacks, but is missing"
                },
                status=403,
                reason=f"Parameter {missing[0]} is mandatory when enabling callbacks, but is missing"
            )
        elif len(missing) == 2:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Parameters {missing[0]} and {missing[1]} "
                               f"are mandatory when enabling callbacks, but are missing"
                },
                status=403,
                reason=f"Parameters {missing[0]} and {missing[1]} "
                       f"are mandatory when enabling callbacks, but are missing"
            )

        chat_id = parameters["chat_id"]
        if Chat.objects.filter(chat_id=chat_id).count() > 0:
            return JsonResponse(
                {"success": False, "message": "Channel's chat has already been started."},
                status=304,
                reason="Channel's chat has already been started."
            )
        else:
            if len(missing) == 0:
                Chat.objects.create(
                    chat_id=chat_id,
                    callback_uri=parameters["callback_uri"],
                    callback_secret=parameters["callback_secret"],
                    callback_id=parameters["callback_id"],
                )
            else:
                Chat.objects.create(
                    chat_id=chat_id,
                )
            return JsonResponse({"success": True, "message": "Added room successfully."})


class EndChat(PostApiPoint):

    endpoint = "endChat"
    required_parameters = ["chat_id"]

    def safe_post(self, request, parameters, *args, **kwargs):
        try:
            Chat.objects.get(parameters["chat_id"]).delete()
            return JsonResponse(
                {"success": True, "message": "Chat has ended successfully"}
            )
        except Chat.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "No chat was found"},
                status=404, reason="No chat was found"
            )


class SendMessage(PostApiPoint):

    endpoint = "sendMessage"
    required_parameters = ["chat_id", "message", "user_name"]

    def safe_post(self, request, parameters, *args, **kwargs):
        try:
            chat = Chat.objects.get(parameters["chat_id"])
        except Chat.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "No chat was found."},
                status=404, reason="No chat was found."
            )

        async_to_sync(channel_layer.group_send)(chat.chat_id, {
            "type": "chat.message",
            "user_name": parameters["user_name"],
            "message": parameters["message"]
        })

        return JsonResponse(
            {"success": True, "message": "Send message successfully."}
        )
