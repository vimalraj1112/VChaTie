from django.urls import path
from . import api_views

urlpatterns = [
    path('register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('conversations/', api_views.ConversationListView.as_view(), name='api_conversations'),
    path('conversations/create/', api_views.CreateConversationAPIView.as_view(), name='api_create_conversation'),
    path('conversations/<int:conversation_id>/messages/', api_views.MessageListView.as_view(), name='api_messages'),
    path('conversations/<int:conversation_id>/messages/send/', api_views.SendMessageAPIView.as_view(), name='api_send_message'),
]