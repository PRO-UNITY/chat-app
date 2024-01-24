from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authen.renderers import UserRenderers
from django.contrib.auth.models import User
from chat.models import (
    Conversation,
    Message
)
from chat.serializers import (
    ConversationListSerializer,
    ConversationSerializer, MessageSerializer, MessageListSerializer
)


class StartConversationView(APIView):
    render_classes = [UserRenderers]
    perrmisson_class = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Invalid Token'}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data
        username = data['username']
        try:
            participant = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'message': 'You cannot chat with a non existent user'})

        conversation = Conversation.objects.filter(Q(initiator=request.user, receiver=participant) |
                                                   Q(initiator=participant, receiver=request.user))
        if conversation.exists():
            return Response({"message": "Conversation already exists"}, status=status.HTTP_200_OK)
        else:
            conversation = Conversation.objects.create(initiator=request.user, receiver=participant)
            return Response(ConversationSerializer(instance=conversation).data, status=status.HTTP_200_OK)


class GetConversationView(APIView):
    render_classes = [UserRenderers]
    filterset_fields = ["text"]

    def get(self, request, convo_id):
        if not request.user.is_authenticated:
            return Response({'error': 'Invalid Token'}, status=status.HTTP_401_UNAUTHORIZED)

        text = request.query_params.get("text", None)
        if text:
            conversation = Message.objects.select_related('conversation_id').filter(
                Q(conversation_id=convo_id), Q(text__icontains=text)
            )
            page = self.paginate_queryset(conversation)
            serializer = MessageListSerializer(conversation, many=True, context={'request': request})

            return Response(serializer.data, status=status.HTTP_200_OK)

        conversation = get_object_or_404(Conversation, id=convo_id)
        messages = conversation.message_set.all()  # Retrieve all messages for the conversation
        # page = self.paginate_queryset(messages)

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


    def put(self, request, convo_id):
        if not request.user.is_authenticated:
            return Response({'error': 'Invalid Token'}, status=status.HTTP_401_UNAUTHORIZED)
        conversation = get_object_or_404(Conversation, id=convo_id)
        serializer = MessageSerializer(data=request.data, context={
            "request": request,
            "conversation": conversation
        })
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversationView(APIView):
    render_classes = [UserRenderers]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Invalid Token'}, status=status.HTTP_401_UNAUTHORIZED)
        conversation_list = Conversation.objects.filter(Q(initiator=request.user) |
                                                        Q(receiver=request.user))
        serializer = ConversationListSerializer(instance=conversation_list, many=True)
        # serializer = super().page(conversation_list, ConversationListSerializer, request)

        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteChatSMSView(APIView):
    render_classes = [UserRenderers]
    permission = [IsAuthenticated]

    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Invalid Token'}, status=status.HTTP_401_UNAUTHORIZED)
        queryset = get_object_or_404(Message, id=pk).delete()
        return Response({'msg': "Message Deleted successfully"}, status=status.HTTP_200_OK)
