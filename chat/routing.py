from django.urls import path, re_path


from chat.comsumers import (
    ChatConsumer,
    ChatMessage,

)


websocket_urlpatterns = [
    path('ws/chat/<int:room_name>/', ChatConsumer.as_asgi()),
    path('ws/message/<int:room_name>/', ChatMessage.as_asgi()),

]