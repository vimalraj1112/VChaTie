import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message, Profile


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.mark_messages_read()

        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'read_receipt', 'reader': self.user.username}
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        msg_id = await self.save_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'message_id': msg_id,
            }
        )

    async def chat_message(self, event):
        if event['sender'] != self.user.username:
            await self.mark_messages_read()
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'read_receipt', 'reader': self.user.username}
            )

        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'message_id': event['message_id'],
        }))

    async def read_receipt(self, event):
        if event['reader'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'reader': event['reader'],
            }))

    @database_sync_to_async
    def save_message(self, message):
        conversation = Conversation.objects.get(id=self.room_name)
        msg = Message.objects.create(conversation=conversation, sender=self.user, text=message)
        return msg.id

    @database_sync_to_async
    def mark_messages_read(self):
        conversation = Conversation.objects.get(id=self.room_name)
        conversation.message.exclude(sender=self.user).update(is_read=True)


class PresenceConsumer(AsyncWebsocketConsumer):
    """A lightweight connection that stays open on EVERY page (inbox, room, etc.)
    purely to track whether a user is actively using the app right now."""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.accept()
        await self.set_online(True)

    async def disconnect(self, close_code):
        await self.set_online(False)

    @database_sync_to_async
    def set_online(self, status):
        profile, created = Profile.objects.get_or_create(user=self.user)
        profile.is_online = status
        profile.save()