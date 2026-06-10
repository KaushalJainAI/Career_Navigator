from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CreditLedger
from .serializers import CreditLedgerSerializer


class BillingSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = CreditLedger.objects.filter(user=request.user).aggregate(total=Sum('delta'))['total'] or 0
        latest = CreditLedger.objects.filter(user=request.user)[:5]
        return Response({
            'balance': balance,
            'currency': 'credits',
            'latest': CreditLedgerSerializer(latest, many=True).data,
            'stripe_enabled': False,
        })


class CreditLedgerListView(generics.ListAPIView):
    serializer_class = CreditLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CreditLedger.objects.filter(user=self.request.user)


class ManualTopUpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = int(request.data.get('amount', 0) or 0)
        if amount <= 0 or amount > 10000:
            return Response({'detail': 'Amount must be between 1 and 10000 credits.'}, status=status.HTTP_400_BAD_REQUEST)
        row = CreditLedger.objects.create(
            user=request.user,
            delta=amount,
            reason='top_up',
            meta={'source': 'manual_dev_top_up'},
        )
        return Response(CreditLedgerSerializer(row).data, status=status.HTTP_201_CREATED)
