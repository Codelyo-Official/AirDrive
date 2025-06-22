from rest_framework import serializers
from .models import Ticket, TicketReply





class TicketReplySerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TicketReply
        fields = ['id', 'ticket', 'sender', 'message', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at', 'ticket']

class TicketSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = TicketReplySerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'user', 'subject', 'message', 'status', 'created_at', 'replies']
        read_only_fields = ['id', 'user', 'status', 'created_at', 'replies']

class TicketStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['status']




class TicketReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReply
        fields = ['id', 'message', 'created_at', 'author']

class TicketDetailSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'status', 'created_at', 'replies']
