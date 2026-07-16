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
        data = json.loads(text_data)

        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'typing_indicator', 'sender': self.user.username}
            )
            return

        message = data['message']
        reply_to_id = data.get('reply_to')
        msg_id, reply_snippet, reply_sender = await self.save_message(message, reply_to_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'message_id': msg_id,
                'reply_snippet': reply_snippet,
                'reply_sender': reply_sender,
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
            'image_url': event.get('image_url'),
            'video_url': event.get('video_url'),
            'audio_url': event.get('audio_url'),
            'reply_snippet': event.get('reply_snippet'),
            'reply_sender': event.get('reply_sender'),
        }))

    async def read_receipt(self, event):
        if event['reader'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'read_receipt',
                'reader': event['reader'],
            }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        }))

    async def typing_indicator(self, event):
        if event['sender'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender': event['sender'],
            }))

    @database_sync_to_async
    def save_message(self, message, reply_to_id=None):
        conversation = Conversation.objects.get(id=self.room_name)
        reply_msg = None
        reply_snippet = None
        reply_sender = None

        if reply_to_id:
            try:
                reply_msg = Message.objects.get(id=reply_to_id)
                reply_snippet = reply_msg.text[:60] if reply_msg.text else "Media message"
                reply_sender = reply_msg.sender.username
            except Message.DoesNotExist:
                pass

        msg = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            text=message,
            reply_to=reply_msg
        )
        return msg.id, reply_snippet, reply_sender

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