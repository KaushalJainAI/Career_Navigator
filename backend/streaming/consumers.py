import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    """Per-user notifications WebSocket. Other services broadcast to
    `user_<id>` to push job alerts, application updates, etc."""

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close(code=4401)
            return
        self.group = f'user_{self.scope["user"].id}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send_json(event.get('payload', {}))


class InterviewConsumer(AsyncJsonWebsocketConsumer):
    """Per-interview-session live channel for the grilling agent."""

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close(code=4401)
            return
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group = f'interview_{self.session_id}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def turn_event(self, event):
        await self.send_json(event.get('payload', {}))
