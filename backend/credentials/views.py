from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Credential
from .serializers import CredentialSerializer


class CredentialListCreateView(generics.ListCreateAPIView):
    serializer_class = CredentialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Credential.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CredentialDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CredentialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Credential.objects.filter(user=self.request.user)
