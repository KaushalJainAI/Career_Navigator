from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import StructuredProfile
from .serializers import StructuredProfileSerializer


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = StructuredProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = StructuredProfile.objects.get_or_create(user=self.request.user)
        return profile
