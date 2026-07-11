from rest_framework import serializers
from .models import Conversation,Message,Profile
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):

    class Meta():
        model=User
        fields=['id','username']

class MessageSerializer(serializers.ModelSerializer):
    sender=UserSerializer(read_only=True) 

    class Meta():
        model=Message
        fields=['id','conversation','sender','text','image','timestamp','is_read']     

class ConversationSerializer(serializers.ModelSerializer):
    participants=UserSerializer(many=True,read_only=True)

    class Meta():
        model=Conversation
        fields=['id','participants','is_group','group_name','created_at']         