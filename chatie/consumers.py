import json
import logging
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message, Profile

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']
        self.is_authorized = False

        logger.warning(
            'ChatConsumer.connect room=%s user=%s authenticated=%s scheme=%s',
            self.room_name, getattr(self.user, 'username', None),
            self.user.is_authenticated, self.scope.get('scheme'),
        )

        # Accept immediately, before any DB/Redis work, so the 101 handshake
        # reaches the browser. If the DB call below then hangs or errors, the
        # browser sees an open socket and a visible system_error instead of a
        # silent 1006 — this isolates proxy-vs-backend failures.
        await self.accept()

        if not self.user.is_authenticated:
            await self._send_system_error('Not authenticated')
            await self.close(code=4001)
            return

        try:
            participant = await self._is_participant()
        except Exception as exc:
            logger.exception('ChatConsumer: participant check failed')
            await self._send_system_error(f'DB check failed: {exc}')
            await self.close(code=1011)
            return

        if not participant:
            await self._send_system_error('You are not a participant in this chat')
            await self.close(code=4003)
            return

        self.is_authorized = True

        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        except Exception as exc:
            logger.exception('ChatConsumer: Redis group_add failed')
            await self._send_system_error(f'Redis group_add failed: {exc}')
            await self.close(code=1011)
            return

        try:
            updated = await self.mark_messages_read()
            if updated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'read_receipt', 'reader': self.user.username}
                )
        except Exception:
            logger.exception('ChatConsumer: mark_messages_read failed')

    async def _send_system_error(self, message):
        try:
            await self.send(text_data=json.dumps({
                'type': 'system_error',
                'message': message,
            }))
        except Exception:
            pass

    async def disconnect(self, close_code):
        if hasattr(self, 'channel_layer') and hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            except Exception:
                logger.exception('ChatConsumer: Redis group_discard failed')

    async def receive(self, text_data):
        if not getattr(self, 'is_authorized', False):
            await self.close(code=4003)
            return

        data = json.loads(text_data)

        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'typing_indicator', 'sender': self.user.username}
            )
            return

        message = (data.get('message') or '').strip()
        if not message:
            return

        reply_to_id = data.get('reply_to')
        temp_id = data.get('temp_id')
        msg_id, reply_snippet, reply_sender = await self.save_message(message, reply_to_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'message_id': msg_id,
                'temp_id': temp_id,
                'reply_snippet': reply_snippet,
                'reply_sender': reply_sender,
            }
        )

    async def chat_message(self, event):
        # Deliver message immediately to browser WebSocket without waiting for DB operations
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'message_id': event['message_id'],
            'temp_id': event.get('temp_id'),
            'image_url': event.get('image_url'),
            'video_url': event.get('video_url'),
            'audio_url': event.get('audio_url'),
            'reply_snippet': event.get('reply_snippet'),
            'reply_sender': event.get('reply_sender'),
            'call_type': event.get('call_type'),
            'call_duration': event.get('call_duration'),
        }))

        # Mark read and notify sender in background after delivery
        if event['sender'] != self.user.username:
            try:
                updated = await self.mark_messages_read()
                if updated:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'read_receipt', 'reader': self.user.username}
                    )
            except Exception:
                logger.exception('ChatConsumer: mark_messages_read in chat_message failed')

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
    def _is_participant(self):
        return Conversation.objects.filter(
            id=self.room_name, participants=self.user
        ).exists()

    @database_sync_to_async
    def save_message(self, message, reply_to_id=None):
        reply_msg = None
        reply_snippet = None
        reply_sender = None

        if reply_to_id:
            try:
                reply_msg = Message.objects.select_related('sender').get(id=reply_to_id)
                reply_snippet = reply_msg.text[:60] if reply_msg.text else "Media message"
                reply_sender = reply_msg.sender.username
            except Message.DoesNotExist:
                pass

        msg = Message.objects.create(
            conversation_id=self.room_name,
            sender=self.user,
            text=message,
            reply_to=reply_msg
        )
        return msg.id, reply_snippet, reply_sender

    @database_sync_to_async
    def mark_messages_read(self):
        return Message.objects.filter(
            conversation_id=self.room_name,
            is_read=False
        ).exclude(sender=self.user).update(is_read=True)


class PresenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']

        logger.warning(
            'PresenceConsumer.connect user=%s authenticated=%s scheme=%s',
            getattr(self.user, 'username', None),
            self.user.is_authenticated, self.scope.get('scheme'),
        )

        # Accept first so a DB stall below surfaces as a visible error
        # instead of blocking the handshake.
        await self.accept()

        if not self.user.is_authenticated:
            await self._send_system_error('Not authenticated')
            await self.close(code=4001)
            return

        try:
            await self.set_online(True)
        except Exception as exc:
            logger.exception('PresenceConsumer: set_online(True) failed')
            await self._send_system_error(f'DB set_online failed: {exc}')

    async def disconnect(self, close_code):
        try:
            await self.set_online(False)
        except Exception:
            logger.exception('PresenceConsumer: set_online(False) failed')

    async def _send_system_error(self, message):
        try:
            await self.send(text_data=json.dumps({
                'type': 'system_error',
                'message': message,
            }))
        except Exception:
            pass

    @database_sync_to_async
    def set_online(self, status):
        if status:
            Profile.objects.filter(user=self.user).update(is_online=True)
        else:
            Profile.objects.filter(user=self.user).update(is_online=False, last_seen=timezone.now())

class CallConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.call_group_name = f'call_{self.room_name}'
        self.user = self.scope['user']

        logger.warning(
            'CallConsumer.connect room=%s user=%s authenticated=%s scheme=%s',
            self.room_name, getattr(self.user, 'username', None),
            self.user.is_authenticated, self.scope.get('scheme'),
        )

        # Accept first so a Redis stall below surfaces visibly instead of
        # blocking the handshake.
        await self.accept()

        if not self.user.is_authenticated:
            await self._send_system_error('Not authenticated')
            await self.close(code=4001)
            return

        try:
            await self.channel_layer.group_add(self.call_group_name, self.channel_name)
        except Exception as exc:
            logger.exception('CallConsumer: Redis group_add failed')
            await self._send_system_error(f'Redis group_add failed: {exc}')
            await self.close(code=1011)
            return

    async def disconnect(self, close_code):
        if hasattr(self, 'channel_layer') and hasattr(self, 'call_group_name'):
            try:
                await self.channel_layer.group_discard(self.call_group_name, self.channel_name)
            except Exception:
                logger.exception('CallConsumer: Redis group_discard failed')

    async def _send_system_error(self, message):
        try:
            await self.send(text_data=json.dumps({
                'type': 'system_error',
                'message': message,
            }))
        except Exception:
            pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.call_group_name,
            {
                'type': 'call_signal',
                'signal_type': data.get('type'),
                'payload': data.get('payload'),
                'call_kind': data.get('call_kind'),
                'sender': self.user.username,
            }
        )

    async def call_signal(self, event):
        if event['sender'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': event['signal_type'],
                'payload': event.get('payload'),
                'call_kind': event.get('call_kind'),
                'sender': event['sender'],
            }))      