from rest_framework import generics, permissions,status
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.all()


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        return Message.objects.filter(conversation_id=conversation_id)
    
class LoginAPIView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })    

class SendMessageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.user not in conversation.participants.all():
            return Response({'error': 'You are not a participant of this conversation'}, status=status.HTTP_403_FORBIDDEN)

        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'Message text cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            text=text
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class CreateConversationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_ids = request.data.get('user_ids', [])
        group_name = request.data.get('group_name', '').strip()

        if not user_ids:
            return Response({'error': 'user_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(user_ids) == 1 and not group_name:
            other_user_id = user_ids[0]
            existing = Conversation.objects.filter(
                is_group=False,
                participants=request.user
            ).filter(
                participants__id=other_user_id
            ).first()

            if existing:
                serializer = ConversationSerializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

            conversation = Conversation.objects.create(is_group=False)
            conversation.participants.add(request.user, other_user_id)
        else:
            conversation = Conversation.objects.create(
                is_group=True,
                group_name=group_name or "Unnamed Group"
            )
            conversation.participants.add(request.user)
            for uid in user_ids:
                conversation.participants.add(uid)

        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)    

from django.contrib.auth.models import User


class RegisterAPIView(APIView):
    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if len(password) < 6:
            return Response({'error': 'Password must be at least 6 characters'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        }, status=status.HTTP_201_CREATED)    