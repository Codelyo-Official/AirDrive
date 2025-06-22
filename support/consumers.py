import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Ticket, TicketReply
from django.contrib.auth.models import AnonymousUser

class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.room_group_name = f'ticket_{self.ticket_id}'

        # Optionally: check user permissions here and reject if unauthorized
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        data = json.loads(text_data)
        message = data.get('message')

        if message:
            # Save reply to DB
            reply = await self.save_reply(user, self.ticket_id, message)

            # Broadcast message to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ticket_message',
                    'message': message,
                    'author': user.username,
                    'created_at': reply.created_at.isoformat(),
                }
            )

    # Receive message from room group
    async def ticket_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'author': event['author'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def save_reply(self, user, ticket_id, message):
        ticket = Ticket.objects.get(id=ticket_id)
        return TicketReply.objects.create(ticket=ticket, author=user, message=message)
