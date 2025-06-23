from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ticket, TicketReply
from .serializers import TicketSerializer, TicketReplySerializer, TicketStatusUpdateSerializer,TicketDetailSerializer
from rest_framework.permissions import IsAuthenticated


class TicketRepliesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id)

        # Only allow related user/support/admin
        if request.user != ticket.user and not request.user.is_staff and request.user.user_type != 'support':
            return Response({"detail": "Not authorized."}, status=403)

        replies = TicketReply.objects.filter(ticket=ticket).order_by('created_at')
        serializer = TicketReplySerializer(replies, many=True)
        return Response(serializer.data)

class TicketDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TicketDetailSerializer
    queryset = Ticket.objects.all()

    def get_queryset(self):
        # Users can only see their own tickets or support/admin all tickets
        user = self.request.user
        if user.user_type in ['support', 'admin']:
            return Ticket.objects.all()
        return Ticket.objects.filter(user=user)

class CreateTicketView(generics.CreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MyTicketsView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)

class AllTicketsAdminSupportView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type in ['admin', 'support']:
            return Ticket.objects.all()
        return Ticket.objects.none()

class ReplyToTicketView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, ticket_id):
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=404)

        serializer = TicketReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ticket=ticket, sender=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class UpdateTicketStatusView(generics.UpdateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        ticket = self.get_object()
        if request.user.user_type not in ['admin', 'support']:
            return Response({"error": "Permission denied"}, status=403)
        return self.partial_update(request, *args, **kwargs)
