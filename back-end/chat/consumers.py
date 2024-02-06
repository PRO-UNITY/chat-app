import base64
import json
import secrets
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer
from django.core.files.base import ContentFile
from chat.models import Message, Conversation
from chat.serializers import MessageSerializer, MessageListSerializer
from django.core.exceptions import ObjectDoesNotExist
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(WebsocketConsumer):
    def connect(self):

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        # Join room group
        async_to_sync(self.channel_layer.group_add)(

            self.room_group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Leave room group

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            message.is_read = True
            message.save()
        except ObjectDoesNotExist:
            print(f"Message with ID {message_id} does not exist.")


    # Receive message from WebSocket
    def receive(self, text_data=None, bytes_data=None):
        # parse the json data into dictionary object
        text_data_json = json.loads(text_data)

        # unpack the dictionary into the necessary parts
        message, attachment = (
            text_data_json["message"],
            text_data_json.get("attachment"),
        )


        try:
            conversation = Conversation.objects.get(id=int(self.room_name))
        except ObjectDoesNotExist:
            # Handle the case where the conversation does not exist
            print(f"Conversation with ID {self.room_name} does not exist.")
            return
        # conversation = Conversation.objects.get(id=int(self.room_name))
        sender = self.scope["user"]
        receiver = conversation.receiver 
        # Attachment
        if attachment:
            file_str, file_ext = attachment["data"], attachment["format"]

            file_data = ContentFile(
                base64.b64decode(file_str), name=f"{secrets.token_hex(8)}.{file_ext}"
            )
            _message = Message.objects.create(
                sender=sender,
                attachment=file_data,
                text=message,
                conversation_id=conversation,
            )
        else:
            _message = Message.objects.create(
                sender=sender,
                text=message,
                conversation_id=conversation,
            )
        # Send message to room group

        chat_type = {"type": "chat_message"}
        message_serializer = (dict(MessageSerializer(instance=_message).data))
        return_dict = {**chat_type, **message_serializer}
        if _message.attachment:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": sender.email,
                    "attachment": _message.attachment.url,
                    "time": str(_message.timestamp),
                },
            )
        else:
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                return_dict,
            )

    # Receive message from room group
    def chat_message(self, event):
        dict_to_be_sent = event.copy()
        dict_to_be_sent.pop("type")

        # Send message to WebSocket
        self.send(
            text_data=json.dumps(
                dict_to_be_sent
            )
        )



# class ChatMessage(WebsocketConsumer):
#     def connect(self):
#         self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
#         self.room_group_name = f"chat_{self.room_name}"

#         async_to_sync(self.channel_layer.group_add)(
#             self.room_group_name, self.channel_name
#         )
#         self.accept()
#         self.get_and_send_messages()

#     def disconnect(self, close_code):
#         async_to_sync(self.channel_layer.group_discard)(
#             self.room_group_name, self.channel_name
#         )
    
#     @database_sync_to_async
#     def get_messages_for_room(self, room_id):

#         try:
#             conversation = Conversation.objects.select_related('initiator', 'receiver').get(id=int(room_id))
#             messages = conversation.message_set.all()  # Retrieve messages related to the conversation

#             messages_data = [{
#                 "id": msg.id,
#                 "sender": msg.sender,
#                 "text": msg.text,
#                 "conversation_id": msg.conversation_id.id,
#                 "is_read": msg.is_read,
#                 "timestamp": msg.timestamp,
#                 "sender_type": msg.sender_type,  # Include sender type
#                 "initiator": conversation.initiator,  # Include initiator
#                 "receiver": conversation.receiver  # Include receiver
#             } for msg in messages]
#             print(messages_data)
#             return messages_data, conversation.initiator, conversation.receiver
#         except Conversation.DoesNotExist:
#             print(f"Conversation with ID {room_id} does not exist.")
#             return [], None, None

#     async def get_and_send_messages(self):
#         room_messages, initiator, receiver = await self.get_messages_for_room(self.room_name)
#         await self.send(text_data=json.dumps({
#             "type": "room_messages",
#             "messages": room_messages,
#             "initiator": initiator,
#             "receiver": receiver
#         }))
    
#     def chat_message(self, event):
#         dict_to_be_sent = event.copy()
#         dict_to_be_sent.pop("type")

#         self.send(
#             text_data=json.dumps(
#                 dict_to_be_sent
#             )
#         )

#     def get_sender_type(self, msg):
#         user = msg.sender
#         print(user)
#         if user:
#             conversation = msg.conversation_id
#             if conversation.initiator == user:
#                 return 'initiator'
#             elif conversation.receiver == user:
#                 return 'receiver'
#         return 'unknown'
        


class ChatMessage(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    # async def receive(self, text_data=None):
    #     # text_data_json = json.loads(text_data)
    #     sender = self.scope["user"]
    #     print(sender.id)
    #     queryset = Notification.objects.filter(
    #         sender=sender.id
    #     ).filter(
    #         is_seen=False
    #     )
    #     print(queryset)
    #     chat_type = {"type": "notification_message"}
    #     message_serializer = {}
    #     # message_serializer = (dict(NotificationSerializer(instance=_queryset).data))
    #     # print(message_serializer)
    #     return_dict = {**chat_type, **message_serializer}
    #     print(return_dict)
    #     # Send message to room group
    #     await self.channel_layer.group_send(
    #         self.room_group_name, return_dict
    #     )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", }
        )

    # Receive message from room group
    # async def notification_message(self, event):
    #     dict_NOTIFICATION = event.copy()
    #     dict_NOTIFICATION.pop("type")
    #     print(dict_NOTIFICATION)
    #     # Send message to WebSocket
    #     self.send(text_data=json.dumps(dict_NOTIFICATION))

    async def chat_message(self, event):
        message = event
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))