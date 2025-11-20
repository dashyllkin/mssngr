import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Conversation, Message
import datetime


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Загружаем историю сообщений при подключении
        await self.send_message_history()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = text_data_json['username']
        user_id = text_data_json['user_id']

        # Сохраняем сообщение в базу
        saved_message = await self.save_message(message, user_id)

        # Отправляем сообщение всем в комнате
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'user_id': user_id,
                'timestamp': saved_message.timestamp.isoformat(),
                'message_id': saved_message.id,
            }
        )

    async def chat_message(self, event):
        # Отправляем сообщение WebSocket клиенту
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
        }))

    async def send_message_history(self):
        """Отправляем историю сообщений при подключении"""
        messages = await self.get_conversation_messages()

        if not messages:
            # Если сообщений нет, отправляем пустой ответ
            await self.send(text_data=json.dumps({
                'type': 'no_messages'
            }))
            return

        # Сначала отправляем информацию о количестве сообщений
        await self.send(text_data=json.dumps({
            'type': 'history_info',
            'total_messages': len(messages)
        }))

        # Затем отправляем все сообщения
        for message in messages:
            await self.send(text_data=json.dumps({
                'type': 'history_message',
                'message': message['content'],
                'username': message['sender__username'],
                'user_id': message['sender_id'],
                'timestamp': message['timestamp'].isoformat(),
                'message_id': message['id'],
            }))

    @sync_to_async
    def save_message(self, message, user_id):
        user = User.objects.get(id=user_id)
        conversation = Conversation.objects.get(id=self.conversation_id)
        return Message.objects.create(
            conversation=conversation,
            sender=user,
            content=message
        )

    @sync_to_async
    def get_conversation_messages(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            messages = conversation.messages.select_related('sender').order_by('timestamp')
            return list(messages.values('id', 'content', 'sender_id', 'sender__username', 'timestamp'))
        except Conversation.DoesNotExist:
            return []